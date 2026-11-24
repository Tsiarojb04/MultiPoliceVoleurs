# -*- coding: utf-8 -*-
"""
main.py — Point d'entrée du jeu (multijoueur en ligne uniquement).

Au lancement, un écran de connexion propose simplement :

  * « Héberger une partie » : le serveur démarre dans le jeu, l'adresse IP
    à partager s'affiche pendant l'attente de l'adversaire ;
  * « Rejoindre une partie » : les parties du réseau local sont détectées
    automatiquement (un clic suffit), avec saisie de l'IP en secours.

Les rôles (Voleur / Police) sont attribués automatiquement : aucun réglage
à synchroniser entre les deux joueurs.

Pendant la partie : cliquer un de ses pions puis une destination verte.
Touches : Échap = quitter la partie, R = proposer de rejouer.
"""

import sys

import pygame

import client
from discovery import ip_locale, port_libre
from locales import texte
from menu import Menu
from render import COL_BG, COL_TEXT_DIM, COL_THIEF, load_font
from server import Serveur

WIDTH, HEIGHT = 880, 920
MIN_W, MIN_H = 480, 540
FPS = 60


def ouvrir_fenetre():
    """Ouvre la fenêtre principale : ajustée à l'écran, redimensionnable."""
    pygame.init()
    info_ecran = pygame.display.Info()
    w0 = max(MIN_W, min(WIDTH, info_ecran.current_w - 80))
    h0 = max(MIN_H, min(HEIGHT, info_ecran.current_h - 120))
    return pygame.display.set_mode((w0, h0), pygame.RESIZABLE)


def ecran_erreur_connexion(screen, hote, port):
    """Affiche l'échec de connexion ; clic ou touche -> retour au menu."""
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        w, h = screen.get_size()
        screen.fill(COL_BG)
        message = texte("net_erreur", hote=hote, port=port, erreur="...")
        lignes = _envelopper(message, 46)
        y = h // 2 - len(lignes) * 18
        for ligne in lignes:
            img = load_font(18, bold=True).render(ligne, True, COL_THIEF)
            screen.blit(img, img.get_rect(center=(w // 2, y)))
            y += 40
        img2 = load_font(14).render("— " + texte("btn_retour") + " —",
                                    True, COL_TEXT_DIM)
        screen.blit(img2, img2.get_rect(center=(w // 2, y + 14)))
        pygame.display.flip()
        clock.tick(30)


def _envelopper(message, largeur):
    """Découpe `message` en lignes d'au plus `largeur` caractères."""
    lignes, courante = [], ""
    for mot in message.split():
        essai = (courante + " " + mot).strip()
        if len(essai) > largeur and courante:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes


def main():
    screen = ouvrir_fenetre()
    serveur = None
    try:
        while True:
            config = Menu().run(screen)
            if config is None:
                break
            nom = config.get("nom")

            if config["action"] == "host":
                if serveur is None:
                    serveur = Serveur(port=port_libre()).demarrer()
                ok = client.lancer_client(
                    "127.0.0.1", serveur.port, nom,
                    screen=screen,
                    partage=f"{ip_locale()}:{serveur.port}")
                hote, port = "127.0.0.1", serveur.port
            else:
                hote, port = config["host"], config["port"]
                ok = client.lancer_client(hote, port, nom, screen=screen)

            if not ok:
                ecran_erreur_connexion(screen, hote, port)
    finally:
        if serveur is not None:
            serveur.arreter()
        pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
