# -*- coding: utf-8 -*-
"""test_solo.py — Test BOUT-EN-BOUT du mode solo (main.boucle_jeu).

Sans interaction humaine réelle :
  * un « chauffeur » (thread séparé) poste les clics souris du joueur
    humain — clic sur un de ses pions, puis clic sur une destination —
    en lisant l'état RÉEL de la partie, exposé par un espion posé sur
    ai.choisir_coup (qui force le niveau « mora » pour répondre vite) ;
  * pour le tout premier coup du voleur humain (l'IA n'ayant pas encore
    joué, l'état réel n'est pas encore exposé), le chauffeur utilise un
    miroir de la position de départ, identique par construction.

Scénarios :
  (1) humain VOLEUR, interface en FRANÇAIS ;
  (2) humain POLICE, interface en MALAGASY (rendu MG exercé).

On vérifie que des coups humains ET des coups IA sont réellement joués
(par le vrai moteur de règles), et qu'Échap ramène proprement au menu
(boucle_jeu se termine sans erreur).
"""
import os
import random
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()

import ai
import main
from game import POLICE, VOLEUR, Game
from render import Layout

screen = pygame.display.set_mode((880, 920))
LAYOUT = Layout(*screen.get_size())

vrai_choisir_coup = ai.choisir_coup
ETAT = {"game": None, "coups_ia": 0, "coups_humains": 0}


def espion(g, role, niveau):
    """Espion posé sur ai.choisir_coup : mémorise l'état réel de la partie
    et force le niveau « mora » (réponse quasi instantanée pour le test)."""
    ETAT["game"] = g
    ETAT["coups_ia"] += 1
    return vrai_choisir_coup(g, role, "mora")


ai.choisir_coup = espion          # main.py appelle bien ai.choisir_coup(...)


def poster_clic(node):
    """Poste un clic gauche sur la position écran du nœud `node`."""
    pos = LAYOUT.to_screen(node)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                         button=1, pos=pos))


def chauffeur(role_humain, duree_max=12.0):
    """Joue le rôle humain depuis un thread : clic pion + clic destination."""
    fin = time.time() + duree_max
    miroir = Game()               # position de départ (avant le 1er coup IA)
    while time.time() < fin:
        g = ETAT["game"]
        if g is None:
            if ETAT["coups_humains"] == 0 and role_humain == VOLEUR:
                g = miroir        # 1er coup du voleur : miroir identique
            else:
                time.sleep(0.05)
                continue
        if g.winner is not None:
            break
        if g.turn == role_humain:
            coups = g.legal_moves(role_humain)
            if coups:
                frm, to = random.choice(coups)
                poster_clic(frm)             # sélection du pion
                time.sleep(0.04)
                poster_clic(to)              # destination (verte)
                ETAT["coups_humains"] += 1
                if g is miroir:
                    # le miroir ne sert qu'UNE fois : ensuite on attend
                    # que l'IA ait joué et exposé l'état réel
                    while ETAT["game"] is None and time.time() < fin:
                        time.sleep(0.05)
        time.sleep(0.04)
    # quitter proprement la boucle de jeu (Échap -> retour au menu)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))


def scenario(langue, role_humain, niveau="antonony", duree_max=12.0):
    """Lance main.boucle_jeu + le chauffeur, puis vérifie les compteurs."""
    ETAT.update({"game": None, "coups_ia": 0, "coups_humains": 0})
    t = threading.Thread(target=chauffeur, args=(role_humain, duree_max))
    t.start()
    main.boucle_jeu(screen, langue, role_humain=role_humain, niveau=niveau)
    t.join(timeout=5)
    assert not t.is_alive(), "le chauffeur ne s'est pas arrêté"
    g = ETAT["game"]
    print(f"  -> humain={ETAT['coups_humains']} coups, IA={ETAT['coups_ia']} "
          f"coups, tours={g.move_count if g else '?'}, "
          f"vainqueur={g.winner if g else '?'}")
    assert ETAT["coups_humains"] >= 5, ETAT
    assert ETAT["coups_ia"] >= 5, ETAT
    assert g is not None and g.move_count >= 10
    # le moteur a bien alterné les tours : voleur et police ont joué
    assert ETAT["coups_humains"] + ETAT["coups_ia"] >= g.move_count - 1


print("Scénario 1 : humain VOLEUR (fr), IA police")
scenario("fr", VOLEUR)
print("Scénario 2 : humain POLICE (mg), IA voleur")
scenario("mg", POLICE)
print("test_solo : TOUS OK")

