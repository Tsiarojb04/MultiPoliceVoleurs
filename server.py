# -*- coding: utf-8 -*-
"""
server.py — Serveur du « Jeu du Gendarme et du Voleur » (multijoueur en ligne).

Serveur TCP multi-threads, sans dépendance externe (module `socket` seul).
Il apparie les deux joueurs, valide les coups avec la classe Game et diffuse
l'état de la partie en temps réel. Il peut être :

  * lancé tout seul :  python server.py
  * démarré automatiquement par main.py quand un joueur clique sur
    « Héberger une partie » (c'est le cas normal).

Dans les deux cas, le serveur annonce son adresse sur le réseau local via
discovery.py : le second joueur n'a qu'à cliquer sur « Rejoindre ».

Protocole (une ligne JSON par message, terminée par \\n) :

  Client -> Serveur :
    {"type": "join",   "role": "voleur"|"police"|"any", "name": "..."}
    {"type": "move",   "frm": "te", "to": "E"}
    {"type": "rematch"}
    {"type": "quit"}

  Serveur -> Client :
    {"type": "waiting",   "msg": "..."}
    {"type": "welcome",   "role": "...", "adversaire": "..."}
    {"type": "start",     "state": {...}}
    {"type": "state",     "state": {...}}
    {"type": "error",     "msg": "..."}
    {"type": "info",      "msg": "..."}
    {"type": "game_over", "winner": "...", "state": {...}}
"""

import argparse
import json
import socket
import threading

from discovery import Annonceur, ip_locale, port_libre
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
        self.souhait = None
        self.role = None
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

    def start(self):
        """(Ré)initialise la partie et prévient les deux joueurs."""
        with self.lock:
            self.game = Game()
            self.rematch_votes = set()
            log(f"Partie lancée : {self.voleur.name} (voleur) vs "
                f"{self.police.name} (police)")
            for c, role in ((self.voleur, VOLEUR), (self.police, POLICE)):
                adversaire = self.police if role == VOLEUR else self.voleur
                c.send({"type": "welcome", "role": role,
                        "adversaire": adversaire.name})
                c.send({"type": "start", "state": self.game.to_dict()})

    def broadcast(self, obj):
        for c in (self.voleur, self.police):
            c.send(obj)

    def handle_move(self, client, msg):
        with self.lock:
            if self.game.winner is not None:
                client.send({"type": "error",
                             "msg": "La partie est terminée (rematch pour rejouer)."})
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
                client.send({"type": "error",
                             "msg": "La partie n'est pas encore terminée."})
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
    """Accepte les connexions et apparie les clients par salon de 2.

    `demarrer()` lance l'écoute dans un thread (pratique pour l'hébergement
    intégré à main.py) ; `arreter()` libère les sockets proprement."""

    def __init__(self, host=HOST_PAR_DEFAUT, port=PORT_PAR_DEFAUT,
                 annoncer=True):
        self.host = host
        self.port = port
        self.attente = []
        self.lock = threading.Lock()
        self._srv = None
        self._thread = None
        self._arret = threading.Event()
        self.annonceur = Annonceur(self.port) if annoncer else None

    def demarrer(self):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.port))
        self._srv.listen(8)
        self._srv.settimeout(0.5)
        self._thread = threading.Thread(target=self._boucle_accept, daemon=True)
        self._thread.start()
        if self.annonceur is not None:
            self.annonceur.demarrer()
        log(f"Écoute sur {self.host}:{self.port} — en attente de 2 joueurs...")
        log(f"Adresse à partager avec l'autre joueur : "
            f"{ip_locale()}:{self.port}")
        return self

    def _boucle_accept(self):
        while not self._arret.is_set():
            try:
                conn, addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            client = Client(conn, addr)
            log(f"Nouvelle connexion : {client.name}")
            threading.Thread(target=self.handle_client, args=(client,),
                             daemon=True).start()

    def _apparier(self, nouveau):
        """Apparie `nouveau` avec un client en attente, sinon le met en file."""
        with self.lock:
            if self.attente:
                ancien = self.attente.pop(0)
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
                        log(f"{client.name} attend un adversaire")
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
                    client.send({"type": "error",
                                 "msg": "Message illisible (JSON attendu)."})
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

    def arreter(self):
        """Arrête l'écoute, l'annonce UDP et attend la fin des threads."""
        self._arret.set()
        if self.annonceur is not None:
            self.annonceur.arreter()
        if self._srv is not None:
            try:
                self._srv.close()
            except OSError:
                pass
            self._srv = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def run(self):
        """Lancement console : bloque jusqu'à Ctrl+C."""
        if self.port == 0:
            self.port = port_libre()
        self.demarrer()
        try:
            while self._thread is not None and not self._arret.is_set():
                self._thread.join(timeout=0.5)
        except KeyboardInterrupt:
            log("Arrêt du serveur (Ctrl+C).")
        finally:
            self.arreter()


def main():
    parser = argparse.ArgumentParser(description="Serveur du jeu Gendarme & Voleur")
    parser.add_argument("--host", default=HOST_PAR_DEFAUT)
    parser.add_argument("--port", type=int, default=PORT_PAR_DEFAUT)
    args = parser.parse_args()
    Serveur(args.host, args.port).run()


if __name__ == "__main__":
    main()
