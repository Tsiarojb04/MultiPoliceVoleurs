# -*- coding: utf-8 -*-
"""
client.py — Client du « Jeu du Gendarme et du Voleur » (multijoueur en ligne).

Le client se connecte au serveur (server.py), reçoit l'état de la partie en
temps réel et n'autorise la souris que pendant SON tour :

   1. attendre « Bienvenue » + rôle attribué automatiquement ;
   2. cliquer sur un de ses pions pour le sélectionner ;
   3. cliquer sur une destination verte pour jouer (le serveur valide et
      diffuse le nouvel état aux deux joueurs).

Lancement normal :  python main.py  (menu « Héberger » / « Rejoindre »).
Lancement direct :  python client.py                (serveur détecté auto)
                    python client.py --host 192.168.1.20

Touches : Échap = quitter, R = proposer de rejouer, A = basculer le mode
« Auto-Play (IA vs IA) ». Dans ce mode, le serveur pilote les deux camps :
les clics sur le plateau sont ignorés, mais les boutons du HUD restent
accessibles pour désactiver le mode ou relancer une partie.

La fenêtre est redimensionnable : le plateau reste centré et proportionnel.
"""

import argparse
import json
import queue
import socket
import sys
import threading

import pygame

from ai import NIVEAUX, NIVEAU_DEFAUT
from discovery import chercher_serveurs
from game import POLICE, VOLEUR, Game
from locales import texte
from render import COL_BG, COL_COP, COL_SEL, COL_STATUS_BG, COL_TARGET, \
    COL_TEXT, COL_TEXT_DIM, COL_THIEF, Layout, draw_scene, load_font

WIDTH, HEIGHT = 880, 920
MIN_W, MIN_H = 480, 540
FPS = 60
PORT_PAR_DEFAUT = 5555


class Reseau:
    """Socket dans un thread dédié (réception) + envoi thread-safe."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.recus = queue.Queue()
        self.lock = threading.Lock()
        self.connecte = False
        self.erreur = None

    def connecter(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=5)
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


class BoutonHUD:
    """Petit bouton cliquable du HUD (auto-play, difficulté, rejouer)."""

    def __init__(self, identifiant, libelle, rect, couleur=COL_TEXT):
        self.id = identifiant
        self.libelle = libelle
        self.rect = rect
        self.couleur = couleur

    def dessiner(self, screen):
        pygame.draw.rect(screen, COL_STATUS_BG, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.couleur, self.rect, 2, border_radius=8)
        img = load_font(13, bold=True).render(self.libelle, True, self.couleur)
        screen.blit(img, img.get_rect(center=self.rect.center))


def _libelle_auto(auto_play):
    return texte("auto_bouton",
                 etat=texte("auto_on") if auto_play else texte("auto_off"))


def _libelle_niveau(niveau):
    return texte("niveau_bouton", niveau=texte(f"niveau_{niveau}"))


def _boutons_hud(w, h, auto_play, niveau, partie_finie):
    """Boutons en haut à droite : ils restent cliquables même en spectateur."""
    largeur = min(210, max(150, w // 3))
    x = w - largeur - 12
    boutons = [
        BoutonHUD("auto", _libelle_auto(auto_play),
                  pygame.Rect(x, 8, largeur, 30),
                  COL_SEL if auto_play else COL_TEXT),
        BoutonHUD("niveau", _libelle_niveau(niveau),
                  pygame.Rect(x, 44, largeur, 30), COL_TARGET),
    ]
    if partie_finie:
        boutons.append(BoutonHUD("rejouer", texte("btn_rejouer"),
                                 pygame.Rect(x, 80, largeur, 30), COL_COP))
    return boutons


def _boutons_attente(w, h, auto_play, niveau):
    """Mêmes réglages, mais dans la salle d'attente (avant la partie)."""
    largeur = min(320, w - 40)
    x = (w - largeur) // 2
    y = h // 2 + 150
    return [
        BoutonHUD("auto", _libelle_auto(auto_play),
                  pygame.Rect(x, y, largeur, 32),
                  COL_SEL if auto_play else COL_TEXT),
        BoutonHUD("niveau", _libelle_niveau(niveau),
                  pygame.Rect(x, y + 40, largeur, 32), COL_TARGET),
    ]


def _clic_bouton(boutons, pos):
    """Renvoie l'identifiant du bouton cliqué, ou None."""
    for bouton in boutons:
        if bouton.rect.collidepoint(pos):
            return bouton.id
    return None


def _ecran_connexion(screen, host, port):
    """Affiche un message pendant la (courte) tentative de connexion."""
    w, h = screen.get_size()
    screen.fill(COL_BG)
    img = load_font(24, bold=True).render(texte("net_connexion"), True, COL_TEXT)
    screen.blit(img, img.get_rect(center=(w // 2, h // 2 - 20)))
    petit = load_font(15).render(f"{host}:{port}", True, COL_TEXT_DIM)
    screen.blit(petit, petit.get_rect(center=(w // 2, h // 2 + 20)))
    pygame.display.flip()


def lancer_client(host=None, port=None, nom=None, role="any", screen=None,
                  partage=None):
    """Lance le client dans une fenêtre pygame.

    * `host` : adresse IP du serveur ; None / "" / "auto" -> détection
      automatique d'une partie sur le réseau local ;
    * `port` : port TCP (5555 par défaut) ;
    * `screen` : fenêtre du menu à réutiliser (sinon une fenêtre est créée) ;
    * `partage` : texte affiché à l'hôte (« partagez 192.168.x.y:5555 »).

    Renvoie False si la connexion a échoué, True si la session s'est
    déroulée (même terminée)."""
    port = PORT_PAR_DEFAUT if port is None else port
    if not host or host == "auto":
        serveurs = chercher_serveurs()
        if not serveurs:
            return False
        host = serveurs[0]["host"]
        port = serveurs[0]["port"]

    if screen is None:
        pygame.init()
        info_ecran = pygame.display.Info()
        w0 = max(MIN_W, min(WIDTH, info_ecran.current_w - 80))
        h0 = max(MIN_H, min(HEIGHT, info_ecran.current_h - 120))
        screen = pygame.display.set_mode((w0, h0), pygame.RESIZABLE)
    _ecran_connexion(screen, host, port)

    reseau = Reseau(host, port)
    if not reseau.connecter():
        return False

    join = {"type": "join", "role": role or "any"}
    if nom:
        join["name"] = nom
    reseau.envoyer(join)

    pygame.display.set_caption(texte("titre_ligne"))
    clock = pygame.time.Clock()
    layout = Layout(*screen.get_size())
    font_titre = load_font(16, bold=True)
    font_centre = load_font(24, bold=True)
    font_petit = load_font(15)

    game = None
    mon_role = None
    adversaire = "?"
    selected, targets = None, []
    info = texte("net_attente")
    auto_play = False          # mode spectateur IA, imposé par le serveur
    niveau_ia = NIVEAU_DEFAUT

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
            # Le serveur est la source de vérité : tout message de partie
            # resynchronise le mode et la difficulté sur ce client.
            if "auto" in msg:
                auto_play = bool(msg["auto"])
            if msg.get("niveau") in NIVEAUX:
                niveau_ia = msg["niveau"]
            if mtype == "auto":
                info = msg.get("msg", "")
                selected, targets = None, []
            elif mtype == "waiting":
                info = msg.get("msg", texte("net_attente"))
            elif mtype == "welcome":
                mon_role = msg.get("role")
                adversaire = msg.get("adversaire", "?")
                info = texte("net_adversaire", qui=adversaire)
                selected, targets = None, []
            elif mtype in ("start", "state"):
                game = Game.from_dict(msg["state"])
                selected, targets = None, []
                info = ""
            elif mtype == "game_over":
                game = Game.from_dict(msg["state"])
                selected, targets = None, []
                info = texte("net_termine")
            elif mtype == "error":
                info = texte("net_refuse", msg=msg.get("msg", "?"))
                selected, targets = None, []
            elif mtype == "info":
                info = msg.get("msg", "")

        # ---------- événements ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
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
                        info = texte("net_rematch")
                elif event.key == pygame.K_a:
                    reseau.envoyer({"type": "auto", "enabled": not auto_play})
                    info = texte("auto_demande")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Les boutons du HUD restent toujours accessibles, y compris
                # en mode spectateur ou après la fin de la partie.
                w_b, h_b = screen.get_size()
                boutons = (_boutons_attente(w_b, h_b, auto_play, niveau_ia)
                           if game is None else
                           _boutons_hud(w_b, h_b, auto_play, niveau_ia,
                                        game.winner is not None))
                ident = _clic_bouton(boutons, event.pos)
                if ident == "auto":
                    reseau.envoyer({"type": "auto", "enabled": not auto_play})
                    info = texte("auto_demande")
                    continue
                if ident == "niveau":
                    suivant = NIVEAUX[(NIVEAUX.index(niveau_ia) + 1) % len(NIVEAUX)]
                    reseau.envoyer({"type": "niveau", "niveau": suivant})
                    info = texte("auto_niveau", niveau=texte(f"niveau_{suivant}"))
                    continue
                if ident == "rejouer":
                    reseau.envoyer({"type": "rematch"})
                    info = texte("net_rematch")
                    continue
                # Plateau désactivé en mode Auto-Play : l'IA joue des deux côtés.
                if (game is None or auto_play or game.winner is not None
                        or mon_role != game.turn):
                    if (game is not None and not auto_play
                            and game.winner is None and mon_role != game.turn):
                        info = texte("net_pas_tour")
                    continue
                node = layout.pick_node(event.pos)
                if node is None:
                    continue
                if selected and node in targets:
                    reseau.envoyer({"type": "move", "frm": selected, "to": node})
                    info = texte("net_envoye", frm=selected, to=node)
                    selected, targets = None, []
                elif node in game.pieces_of(mon_role):
                    selected = node
                    try:
                        targets = game.legal_targets(mon_role, node)
                    except Exception:
                        targets = []
                    info = texte("info_selection", qui="", node=node)
                else:
                    selected, targets = None, []

        # ---------- affichage ----------
        w_fen, h_fen = screen.get_size()
        if game is None:
            screen.fill(COL_BG)
            attente = font_centre.render(texte("net_attente"), True, COL_TEXT)
            screen.blit(attente, attente.get_rect(
                center=(w_fen // 2, h_fen // 2 - 60)))
            if partage:
                img = load_font(17, bold=True).render(texte("net_partage"),
                                                      True, COL_TEXT)
                screen.blit(img, img.get_rect(center=(w_fen // 2, h_fen // 2 - 10)))
                img = load_font(26, bold=True).render(partage, True, COL_THIEF)
                screen.blit(img, img.get_rect(center=(w_fen // 2, h_fen // 2 + 30)))
                img = font_petit.render(texte("net_partage_aide"), True,
                                        COL_TEXT_DIM)
                screen.blit(img, img.get_rect(center=(w_fen // 2, h_fen // 2 + 70)))
            else:
                img = font_petit.render(f"{host}:{port}", True, COL_TEXT_DIM)
                screen.blit(img, img.get_rect(center=(w_fen // 2, h_fen // 2 - 10)))
            if info:
                img = font_petit.render(info, True, COL_TEXT_DIM)
                screen.blit(img, img.get_rect(center=(w_fen // 2, h_fen // 2 + 120)))
            for bouton in _boutons_attente(w_fen, h_fen, auto_play, niveau_ia):
                bouton.dessiner(screen)
        else:
            draw_scene(screen, layout, game, selected, targets, info)
            couleur = COL_THIEF if mon_role == VOLEUR else COL_COP
            libelle = (texte("net_vous_voleur") if mon_role == VOLEUR
                       else texte("net_vous_police"))
            entete = f"{libelle}  —  {texte('net_adversaire_court')} : {adversaire}"
            img_entete = font_titre.render(entete, True, couleur)
            largeur_boutons = min(210, max(150, w_fen // 3)) + 30
            if img_entete.get_width() > w_fen - largeur_boutons:
                entete = f"{libelle}  —  {adversaire}"
                img_entete = font_titre.render(entete, True, couleur)
            if img_entete.get_width() > w_fen - largeur_boutons:
                img_entete = font_titre.render(
                    "VOLEUR" if mon_role == VOLEUR else "POLICE", True, couleur)
            screen.blit(img_entete, (12, 8))
            if auto_play:
                badge = load_font(15, bold=True).render(
                    texte("auto_bandeau"), True, COL_SEL)
                screen.blit(badge, badge.get_rect(center=(
                    w_fen // 2, h_fen - layout.status_h - 16)))
            for bouton in _boutons_hud(w_fen, h_fen, auto_play, niveau_ia,
                                       game.winner is not None):
                bouton.dessiner(screen)

        pygame.display.flip()
        clock.tick(FPS)

    reseau.deconnexion()
    return True


def main():
    parser = argparse.ArgumentParser(description="Client du jeu Gendarme & Voleur")
    parser.add_argument("--host", default=None,
                        help="IP du serveur (détection automatique si omise)")
    parser.add_argument("--port", type=int, default=PORT_PAR_DEFAUT)
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    ok = lancer_client(args.host, args.port, args.name, role="any")
    if not ok:
        print("Aucun serveur trouvé : lancez 'python main.py' chez l'hôte, "
              "ou indiquez son IP avec --host.")
        sys.exit(1)
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
