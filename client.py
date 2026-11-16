# -*- coding: utf-8 -*-
"""
client.py — Client réseau du « Jeu du Gendarme et du Voleur » (pygame).

Un joueur incarne le VOLEUR (pion rouge), l'autre la POLICE (pions bleus).
Le client se connecte au serveur (server.py), reçoit l'état de la partie en
temps réel et n'autorise la souris que pendant SON tour :

  1. attendre « Bienvenue » + rôle attribué ;
  2. cliquer sur un de ses pions pour le sélectionner ;
  3. cliquer sur une destination verte pour jouer (envoyé au serveur,
     qui valide le coup et diffuse le nouvel état aux deux joueurs).

Lancement direct (ligne de commande) :
    python client.py                              # 127.0.0.1:5555, rôle demandé
    python client.py --host 192.168.1.20         # serveur distant
    python client.py --role voleur                # forcer un rôle
    python client.py --role police --name Alice --port 9000

Ou DEPUIS LE MENU de main.py (mode « En ligne ») : la fonction
lancer_client() réutilise alors la fenêtre du menu.

Touches : Échap = quitter, R = demander à rejouer (après une fin de partie).
La fenêtre est redimensionnable (pygame.RESIZABLE) : le plateau est
recalculé proportionnellement et reste exactement centré.
"""

import argparse
import json
import queue
import socket
import sys
import threading

import pygame

from game import POLICE, VOLEUR, Game
from locales import set_langue, texte
from render import COL_COP, COL_THIEF, Layout, draw_scene, load_font

WIDTH, HEIGHT = 880, 920
MIN_W, MIN_H = 480, 540   # taille minimale de la fenêtre (plateau jouable)
FPS = 60


class Reseau:
    """Gestion de la socket dans un thread dédié.

    Les messages reçus sont poussés dans une file ; l'envoi des messages
    se fait depuis la boucle principale (thread-safe via un verrou)."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.recus = queue.Queue()       # messages à traiter par la boucle
        self.lock = threading.Lock()
        self.connecte = False
        self.erreur = None

    def connecter(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=10)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(None)
        except OSError as e:
            self.erreur = texte("net_erreur", hote=self.host, port=self.port,
                                erreur=e)
            return False
        self.connecte = True
        threading.Thread(target=self._boucle_reception, daemon=True).start()
        return True

    def envoyer(self, obj):
        if not self.connecte:
            return
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            with self.lock:
                self.sock.sendall(data)
        except OSError:
            self.connecte = False
            self.erreur = texte("net_perdu")

    def _boucle_reception(self):
        buf = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                chunk = b""
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, _, buf = buf.partition(b"\n")
                try:
                    self.recus.put(json.loads(line.decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    continue
        self.connecte = False
        self.recus.put({"type": "info", "msg": texte("net_deconnecte")})

    def deconnexion(self):
        try:
            self.envoyer({"type": "quit"})
            self.sock.close()
        except OSError:
            pass
        self.connecte = False


# ---------------------------------------------------------------------------
# Boucle de jeu réseau — utilisable depuis le menu (screen fourni) ou
# en ligne de commande (fenêtre créée ici)
# ---------------------------------------------------------------------------
def lancer_client(host, port, nom=None, role=None, langue="fr", screen=None):
    """Lance le client réseau dans une fenêtre pygame.

    * `screen` : fenêtre à réutiliser (celle du menu) ; si None, une
      fenêtre redimensionnable est créée.
    * `role` : VOLEUR, POLICE ou "any" (None -> "any").

    Renvoie True si la session s'est déroulée (même finie), False si la
    connexion au serveur a échoué."""
    set_langue(langue)
    role = role or "any"

    reseau = Reseau(host, port)
    if not reseau.connecter():
        return False

    # --- identification auprès du serveur ---
    join = {"type": "join", "role": role}
    if nom:
        join["name"] = nom
    reseau.envoyer(join)

    # --- fenêtre pygame (redimensionnable ; réutilise celle du menu) ---
    possede_fenetre = screen is not None
    if screen is None:
        pygame.init()
        info_ecran = pygame.display.Info()
        w0 = max(MIN_W, min(WIDTH, info_ecran.current_w - 80))
        h0 = max(MIN_H, min(HEIGHT, info_ecran.current_h - 120))
        screen = pygame.display.set_mode((w0, h0), pygame.RESIZABLE)
    pygame.display.set_caption(texte("titre_ligne", langue))
    clock = pygame.time.Clock()
    layout = Layout(*screen.get_size())
    font_titre = load_font(16, bold=True)
    font_centre = load_font(26, bold=True)

    game = None                 # miroir local de l'état (None = en attente)
    mon_role = None
    adversaire = "?"
    selected, targets = None, []
    info = texte("net_connexion", langue)

    running = True
    while running:
        # ---------- messages réseau ----------
        messages = []
        try:
            while True:
                messages.append(reseau.recus.get_nowait())
        except queue.Empty:
            pass
        for msg in messages:
            mtype = msg.get("type")
            if mtype == "waiting":
                info = msg.get("msg", texte("net_attente", langue))
            elif mtype == "welcome":
                mon_role = msg.get("role")
                adversaire = msg.get("adversaire", "?")
                info = texte("net_adversaire", langue, qui=adversaire)
                selected, targets = None, []
            elif mtype in ("start", "state"):
                game = Game.from_dict(msg["state"])
                selected, targets = None, []
                info = ""
            elif mtype == "game_over":
                game = Game.from_dict(msg["state"])
                selected, targets = None, []
                info = texte("net_termine", langue)
            elif mtype == "error":
                info = texte("net_refuse", langue, msg=msg.get("msg", "?"))
                selected, targets = None, []
            elif mtype == "info":
                info = msg.get("msg", "")

        # ---------- événements ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                # --- REDIMENSIONNEMENT : échelle et centrage recalculés
                #     dynamiquement pour que le plateau reste entièrement
                #     visible et exactement centré dans la nouvelle fenêtre
                w, h = max(MIN_W, event.w), max(MIN_H, event.h)
                if (event.w, event.h) != (w, h):
                    screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                layout = Layout(w, h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    if game is not None and game.winner is not None:
                        reseau.envoyer({"type": "rematch"})
                        info = texte("net_rematch", langue)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # on ne joue que pendant SON tour, sur SES pions
                if game is None or game.winner is not None or mon_role != game.turn:
                    if game is not None and mon_role != game.turn and game.winner is None:
                        info = texte("net_pas_tour", langue)
                    continue
                node = layout.pick_node(event.pos)
                if node is None:
                    continue
                if selected and node in targets:
                    reseau.envoyer({"type": "move", "frm": selected, "to": node})
                    info = texte("net_envoye", langue, frm=selected, to=node)
                    selected, targets = None, []
                elif node in game.pieces_of(mon_role):
                    selected = node
                    try:
                        targets = game.legal_targets(mon_role, node)
                    except Exception:
                        targets = []
                    info = texte("info_selection", langue, qui="", node=node)
                else:
                    selected, targets = None, []

        # ---------- affichage ----------
        w_fen, h_fen = screen.get_size()
        if game is None:
            screen.fill((24, 26, 34))
            texte_img = font_centre.render(texte("net_attente", langue), True,
                                           (220, 220, 228))
            screen.blit(texte_img,
                        texte_img.get_rect(center=(w_fen // 2, h_fen // 2 - 40)))
            petit = load_font(15).render(
                texte("net_serveur_role", langue, hote=host, port=port,
                      role=role), True, (150, 152, 165))
            screen.blit(petit, petit.get_rect(center=(w_fen // 2, h_fen // 2)))
        else:
            draw_scene(screen, layout, game, selected, targets, info, langue)
            # bandeau indiquant QUI on est
            couleur = COL_THIEF if mon_role == VOLEUR else COL_COP
            libelle = (texte("net_vous_voleur", langue) if mon_role == VOLEUR
                       else texte("net_vous_police", langue))
            screen.blit(font_titre.render(
                f"{libelle}  —  {texte('net_adversaire_court', langue)} : "
                f"{adversaire}", True, couleur), (12, 8))

        pygame.display.flip()
        clock.tick(FPS)

    reseau.deconnexion()
    return True


# ---------------------------------------------------------------------------
# Utilisation en ligne de commande
# ---------------------------------------------------------------------------
def choisir_role_console(langue="fr"):
    print(texte("con_role_titre", langue))
    print(texte("con_role_options", langue))
    rep = input(texte("con_role_choix", langue)).strip().lower()
    return {"v": VOLEUR, "p": POLICE}.get(rep, "any")


def main():
    parser = argparse.ArgumentParser(description="Client du jeu Gendarme & Voleur")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5555)
    parser.add_argument("--name", default=None)
    parser.add_argument("--langue", default="fr", choices=("fr", "mg"))
    parser.add_argument("--role", choices=[VOLEUR, POLICE, "any", "a", "v", "p"],
                        default=None)
    args = parser.parse_args()

    role_voulu = args.role
    if role_voulu in ("a",):
        role_voulu = "any"
    elif role_voulu in ("v",):
        role_voulu = VOLEUR
    elif role_voulu in ("p",):
        role_voulu = POLICE
    if role_voulu is None:
        role_voulu = choisir_role_console(args.langue)

    ok = lancer_client(args.host, args.port, args.name, role_voulu, args.langue)
    if not ok:
        print("Erreur : connexion impossible.")
        sys.exit(1)
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
