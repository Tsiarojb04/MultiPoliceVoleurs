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
    {"type": "auto",   "enabled": true|false}
    {"type": "niveau", "niveau": "mora"|"antonony"|"sarotra"}
    {"type": "rematch"}
    {"type": "quit"}

  Serveur -> Client :
    {"type": "waiting",   "msg": "..."}
    {"type": "welcome",   "role": "...", "adversaire": "..."}
    {"type": "start",     "state": {...}}
    {"type": "state",     "state": {...}}
    {"type": "auto",      "enabled": ..., "niveau": "...", "msg": "..."}
    {"type": "error",     "msg": "..."}
    {"type": "info",      "msg": "..."}
    {"type": "game_over", "winner": "...", "state": {...}}

Tous les messages de partie (welcome/start/state/game_over/auto) portent
aussi les champs "auto" et "niveau" : le mode spectateur reste synchronisé
même si un client manque une notification.

Mode « Auto-Play (IA vs IA) » : le SERVEUR calcule les coups des deux camps
avec ai.py (un seul calcul, diffusé ensuite aux deux clients). Les coups
manuels sont refusés tant que le mode est actif. La bascule peut avoir lieu
à tout moment, y compris pendant une partie.
"""

import argparse
import json
import os
import socket
import threading

from ai import NIVEAU_DEFAUT, NIVEAUX, choisir_coup, evaluer
from discovery import Annonceur, ip_locale, port_libre
from game import POLICE, VOLEUR, Game, IllegalMove
from locales import texte

HOST_PAR_DEFAUT = "0.0.0.0"
PORT_PAR_DEFAUT = 5555

AUTRE_ROLE = {VOLEUR: POLICE, POLICE: VOLEUR}

# Réglages du mode spectateur (variables d'environnement pratiques pour les
# tests : on peut accélérer le rythme des coups sans toucher au jeu).
DELAI_AUTO = float(os.environ.get("POLICE_VOLEUR_AUTO_DELAI", "0.45"))
TEMPS_IA_AUTO = float(os.environ.get("POLICE_VOLEUR_AUTO_TEMPS", "0.35"))
AUTO_MAX_COUPS = 200       # garde-fou contre une partie IA vs IA interminable


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
        # Préférences de mode spectateur, même avant l'appariement : elles
        # sont appliquées dès que la Room est créée.
        self.auto = False
        self.niveau = NIVEAU_DEFAUT
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
        self.cond = threading.Condition(self.lock)
        self.game = Game()
        self.voleur = voleur
        self.police = police
        self.rematch_votes = set()

        # Mode Auto-Play : n'importe quel joueur peut l'activer/désactiver.
        # Les préférences exprimées dans la salle d'attente sont conservées.
        self.auto = bool(voleur.auto or police.auto)
        self.niveau = (voleur.niveau if voleur.niveau != NIVEAU_DEFAUT
                       else police.niveau)
        self._thread_auto = None
        self._arret_auto = threading.Event()

    # ------------------------------------------------------------------ #
    # Mode spectateur IA (calculé côté SERVEUR uniquement)
    # ------------------------------------------------------------------ #
    def _config(self, msg):
        """Ajoute la configuration du mode à un message diffusé."""
        msg["auto"] = self.auto
        msg["niveau"] = self.niveau
        return msg

    def _demarrer_auto(self):
        if self._thread_auto is None:
            self._thread_auto = threading.Thread(
                target=self._boucle_auto, daemon=True,
                name=f"auto-{id(self)}")
            self._thread_auto.start()

    def _boucle_auto(self):
        """Joue les deux camps les uns après les autres et diffuse CHAQUE
        état aux deux clients. Une seule simulation existe : côté serveur."""
        while not self._arret_auto.is_set():
            with self.cond:
                if (self.game.move_count >= AUTO_MAX_COUPS
                        and self.game.winner is None):
                    # Garde-fou : on départage selon l'évaluation de la
                    # position (voleur si elle lui est favorable).
                    gagnant = VOLEUR if evaluer(self.game) > 0 else POLICE
                    self.game.winner = gagnant
                    log(f"Auto-Play — limite de coups atteinte, "
                        f"vainqueur par évaluation : {gagnant}")
                    self.broadcast({"type": "game_over", "winner": gagnant,
                                    "state": self.game.to_dict()})
                while (not self.auto or self.game.winner is not None
                       or self.game.move_count >= AUTO_MAX_COUPS):
                    if self._arret_auto.is_set():
                        return
                    self.cond.wait(timeout=0.25)
                # On calcule sur un clones hors verrou : la bascule reste
                # réactive même si Sarotra réfléchit longtemps.
                snapshot, role = self.game.clone(), self.game.turn
                niveau = self.niveau
            try:
                coup = choisir_coup(snapshot, role, niveau,
                                    temps_max=TEMPS_IA_AUTO)
            except Exception as e:          # ne jamais tuer le thread IA
                log(f"erreur IA ({role}) : {e}")
                coup = None

            with self.cond:
                # Bascule ou rematch pendant le calcul : on jette le coup.
                if (not self.auto or self.game.winner is not None
                        or self.game.turn != role
                        or self.niveau != niveau
                        or self.game.move_count != snapshot.move_count):
                    self.cond.wait(timeout=0.05)
                    continue

                if coup is None:
                    # Défense : le moteur n'aurait pas dû laisser ce cas.
                    self.game.winner = POLICE if role == VOLEUR else VOLEUR
                else:
                    self.game.move(role, *coup)
                state = self.game.to_dict()
                if self.game.winner is not None:
                    log(f"Auto-Play — partie terminée, vainqueur : "
                        f"{self.game.winner}")
                    self.broadcast({"type": "game_over",
                                    "winner": self.game.winner,
                                    "state": state})
                else:
                    self.broadcast({"type": "state", "state": state})
                self.cond.wait(timeout=DELAI_AUTO)

    def handle_auto(self, client, msg):
        """Active/désactive l'auto-play et/ou change le niveau d'IA."""
        with self.cond:
            if msg.get("niveau") in NIVEAUX:
                self.niveau = msg["niveau"]
                for c in (self.voleur, self.police):
                    if c is not None:
                        c.niveau = self.niveau
            if "enabled" in msg:
                self.auto = bool(msg["enabled"])
                for c in (self.voleur, self.police):
                    if c is not None:
                        c.auto = self.auto
            log(f"Auto-Play {'activé' if self.auto else 'désactivé'} "
                f"— niveau {self.niveau} (par {client.name})")
            self.broadcast(self._config({
                "type": "auto", "enabled": self.auto, "niveau": self.niveau,
                "msg": texte("auto_active" if self.auto else "auto_desactive"),
            }))
            self.cond.notify_all()

    def start(self):
        """(Ré)initialise la partie et prévient les deux joueurs."""
        with self.lock:
            self.game = Game()
            self.rematch_votes = set()
            log(f"Partie lancée : "
                f"{self.voleur.name if self.voleur else '?'} (voleur) vs "
                f"{self.police.name if self.police else '?'} (police)")
            for c, role in ((self.voleur, VOLEUR), (self.police, POLICE)):
                if c is None:
                    continue
                adversaire = self.police if role == VOLEUR else self.voleur
                c.send(self._config({"type": "welcome", "role": role,
                                     "adversaire": adversaire.name
                                     if adversaire else "?"}))
                c.send(self._config({"type": "start",
                                     "state": self.game.to_dict()}))
            self._demarrer_auto()
            self.cond.notify_all()

    def broadcast(self, obj):
        """Diffuse un message aux deux clients (état identique des deux
        côtés), avec la configuration du mode spectateur."""
        msg = self._config(obj)
        for c in (self.voleur, self.police):
            if c is not None:
                c.send(msg)

    def handle_move(self, client, msg):
        with self.lock:
            if self.auto:
                client.send(self._config({
                    "type": "error", "msg": texte("auto_refuse")}))
                return
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
            # En mode spectateur, un seul des deux spectateurs suffit à
            # relancer la partie (les deux peuvent cliquer sur « Rejouer »).
            if self.auto or len(self.rematch_votes) >= 2:
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
                autre.send(self._config({
                    "type": "info",
                    "msg": "Votre adversaire s'est déconnecté. "
                           "Vous pouvez quitter (Échap) ou attendre."}))
            if self.voleur is None and self.police is None:
                self._arret_auto.set()
                self.cond.notify_all()
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
                                     "msg": "En attente d'un adversaire...",
                                     "auto": client.auto,
                                     "niveau": client.niveau})
                        log(f"{client.name} attend un adversaire")
                    else:
                        room.start()

                elif mtype == "move":
                    if client.room is not None:
                        client.room.handle_move(client, msg)

                elif mtype in ("auto", "niveau"):
                    # Config possible avant même l'appariement : elle sera
                    # appliquée à la création de la Room.
                    if msg.get("niveau") in NIVEAUX:
                        client.niveau = msg["niveau"]
                    if "enabled" in msg:
                        client.auto = bool(msg["enabled"])
                    if client.room is not None:
                        client.room.handle_auto(client, msg)
                    else:
                        client.send({
                            "type": "auto", "enabled": client.auto,
                            "niveau": client.niveau,
                            "msg": texte("auto_active" if client.auto
                                         else "auto_desactive"),
                        })

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
