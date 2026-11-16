# -*- coding: utf-8 -*-
"""
server.py — Serveur du « Jeu du Gendarme et du Voleur » (mode en ligne).

Serveur TCP multi-threads, sans dépendance externe (module `socket` seul).
Il apparie les clients par salon de 2 joueurs (un VOLEUR + une POLICE),
valide les coups avec la classe Game (partagée avec le jeu local) et
diffuse l'état de la partie aux deux joueurs en temps réel.

Protocole (une ligne JSON par message, terminée par \\n) :

  Client -> Serveur :
    {"type": "join",   "role": "voleur"|"police"|"any", "name": "..."}
    {"type": "move",   "frm": "te", "to": "E"}   (identifiants des nœuds)
    {"type": "rematch"}
    {"type": "quit"}

  Serveur -> Client :
    {"type": "waiting", "msg": "..."}                en attente d'un adversaire
    {"type": "welcome", "role": "...", "adversaire": "..."} salon complet
    {"type": "start", "state": {...}}               début de partie (état initial)
    {"type": "state",  "state": {...}}              état après chaque coup validé
    {"type": "error",  "msg": "..."}                coup illégal (émis à l'émetteur)
    {"type": "info",   "msg": "..."}                déconnexion, rematch...
    {"type": "game_over", "winner": "...", "state": {...}}

Lancement :
    python server.py                 # écoute sur 0.0.0.0:5555
    python server.py --host 127.0.0.1 --port 9000
"""

import argparse
import json
import socket
import threading

from game import POLICE, VOLEUR, Game, IllegalMove

HOST_PAR_DEFAUT = "0.0.0.0"
PORT_PAR_DEFAUT = 5555

AUTRE_ROLE = {VOLEUR: POLICE, POLICE: VOLEUR}


def log(msg):
    print(f"[serveur] {msg}", flush=True)


class Client:
    """Un client connecté : socket, pseudo, rôle attribué et salon."""

    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.name = f"joueur@{addr[0]}:{addr[1]}"
        self.souhait = None          # rôle demandé au moment du join
        self.role = None              # rôle définitif : "voleur" ou "police"
        self.room = None
        self.send_lock = threading.Lock()

    def send(self, obj):
        """Envoie un message JSON (thread-safe)."""
        try:
            data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            with self.send_lock:
                self.conn.sendall(data)
        except OSError:
            pass

    def recv_line(self):
        """Lit une ligne JSON complète ; renvoie None si déconnexion."""
        buf = b""
        while b"\n" not in buf:
            try:
                chunk = self.conn.recv(4096)
            except OSError:
                return None
            if not chunk:
                return None
            buf += chunk
        line = buf.partition(b"\n")[0]
        try:
            return json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {"type": "bad_message"}


class Room:
    """Salon de 2 joueurs : un voleur, une police, une partie en cours."""

    def __init__(self, voleur, police):
        self.lock = threading.RLock()
        self.game = Game()
        self.voleur = voleur
        self.police = police
        self.rematch_votes = set()

    # ------------------------------------------------------------------ #
    def start(self):
        """(Ré)initialise la partie et prévient les deux joueurs."""
        with self.lock:
            self.game = Game()
            self.rematch_votes = set()
            log(f"Partie lancée : {self.voleur.name} (voleur) vs "
                f"{self.police.name} (police)")
            for c, role in ((self.voleur, VOLEUR), (self.police, POLICE)):
                adversaire = self.police if role == VOLEUR else self.voleur
                c.send({"type": "welcome", "role": role, "adversaire": adversaire.name})
                c.send({"type": "start", "state": self.game.to_dict()})

    def broadcast(self, obj):
        for c in (self.voleur, self.police):
            c.send(obj)

    # ------------------------------------------------------------------ #
    def handle_move(self, client, msg):
        with self.lock:
            if self.game.winner is not None:
                client.send({"type": "error", "msg": "La partie est terminée (rematch pour rejouer)."})
                return
            try:
                self.game.move(client.role, msg.get("frm"), msg.get("to"))
            except IllegalMove as e:
                client.send({"type": "error", "msg": str(e)})
                return
            state = self.game.to_dict()
            if self.game.winner is not None:
                log(f"Partie terminée — vainqueur : {self.game.winner}")
                self.broadcast({"type": "game_over", "winner": self.game.winner,
                                "state": state})
            else:
                self.broadcast({"type": "state", "state": state})

    def handle_rematch(self, client):
        with self.lock:
            if self.game.winner is None:
                client.send({"type": "error", "msg": "La partie n'est pas encore terminée."})
                return
            self.rematch_votes.add(client.role)
            if len(self.rematch_votes) >= 2:
                self.start()
            else:
                self.broadcast({"type": "info",
                               "msg": f"{client.name} veut rejouer (1/2)..."})

    def leave(self, client):
        with self.lock:
            if client is self.voleur:
                self.voleur = None
            elif client is self.police:
                self.police = None
            autre = self.voleur or self.police
            if autre is not None:
                autre.send({"type": "info",
                            "msg": "Votre adversaire s'est déconnecté. "
                                   "Vous pouvez quitter (Échap) ou attendre."})
            log(f"{client.name} quitte son salon.")


class Serveur:
    """Accepte les connexions et apparie les clients par salon de 2."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.attente = []          # liste de Client en attente d'un adversaire
        self.lock = threading.Lock()

    def _apparier(self, nouveau):
        """Apparie `nouveau` avec un client en attente, sinon le met en file.

        Renvoie le salon créé, ou None si le client doit attendre."""
        with self.lock:
            if self.attente:
                ancien = self.attente.pop(0)
                # attribution des rôles : priorité au premier arrivé,
                # les indécis ("any") prennent le rôle restant.
                if ancien.souhait in (VOLEUR, POLICE):
                    role_ancien = ancien.souhait
                elif nouveau.souhait in (VOLEUR, POLICE):
                    role_ancien = AUTRE_ROLE[nouveau.souhait]
                else:
                    role_ancien = VOLEUR
                role_nouveau = AUTRE_ROLE[role_ancien]

                ancien.role, nouveau.role = role_ancien, role_nouveau
                room = Room(ancien if role_ancien == VOLEUR else nouveau,
                            ancien if role_ancien == POLICE else nouveau)
                ancien.room = nouveau.room = room
                return room
            self.attente.append(nouveau)
            return None

    def handle_client(self, client):
        try:
            while True:
                msg = client.recv_line()
                if msg is None:
                    break
                mtype = msg.get("type")

                if mtype == "join":
                    if client.room is not None:
                        continue
                    if "name" in msg:
                        client.name = str(msg["name"])[:30]
                    souhait = msg.get("role") or "any"
                    client.souhait = souhait if souhait in (VOLEUR, POLICE) else None
                    room = self._apparier(client)
                    if room is None:
                        client.send({"type": "waiting",
                                     "msg": "En attente d'un adversaire..."})
                        log(f"{client.name} attend un adversaire "
                            f"(rôle souhaité : {souhait})")
                    else:
                        room.start()

                elif mtype == "move":
                    if client.room is not None:
                        client.room.handle_move(client, msg)

                elif mtype == "rematch":
                    if client.room is not None:
                        client.room.handle_rematch(client)

                elif mtype == "quit":
                    break

                elif mtype == "bad_message":
                    client.send({"type": "error", "msg": "Message illisible (JSON attendu)."})
        finally:
            if client.room is not None:
                client.room.leave(client)
            else:
                with self.lock:
                    if client in self.attente:
                        self.attente.remove(client)
            try:
                client.conn.close()
            except OSError:
                pass
            log(f"Déconnexion de {client.name}")

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(8)
        log(f"Écoute sur {self.host}:{self.port} — en attente de 2 joueurs...")
        log(f"Sur chaque machine :  python client.py --host <ip_serveur> "
            f"--port {self.port}")
        try:
            while True:
                conn, addr = srv.accept()
                client = Client(conn, addr)
                log(f"Nouvelle connexion : {client.name}")
                threading.Thread(target=self.handle_client, args=(client,),
                                 daemon=True).start()
        except KeyboardInterrupt:
            log("Arrêt du serveur (Ctrl+C).")
        finally:
            srv.close()


def main():
    parser = argparse.ArgumentParser(description="Serveur du jeu Gendarme & Voleur")
    parser.add_argument("--host", default=HOST_PAR_DEFAUT)
    parser.add_argument("--port", type=int, default=PORT_PAR_DEFAUT)
    args = parser.parse_args()
    Serveur(args.host, args.port).run()


if __name__ == "__main__":
    main()
