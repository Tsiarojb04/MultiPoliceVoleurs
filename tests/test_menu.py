# -*- coding: utf-8 -*-
"""test_menu.py — Tests non interactifs de l'écran de connexion (menu.py).

Vérifie, avec le pilote vidéo « dummy » (aucune fenêtre réelle) :
  1. le rendu des deux écrans (accueil / rejoindre) ;
  2. les identifiants des boutons ;
  3. les configurations renvoyées (hébergement, partie détectée, IP saisie) ;
  4. le refus d'une adresse vide ;
  5. la sentinelle _QUITTER, le retour et la saisie clavier ;
  6. la détection UDP d'un serveur local (discovery.py).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()
screen = pygame.display.set_mode((880, 920))

from discovery import Annonceur, chercher_serveurs
from menu import _QUITTER, ChampTexte, Menu

# ------------------------------------------------------------------ 1. rendu
m = Menu()
for ecran in ("accueil", "rejoindre"):
    m.ecran = ecran
    boutons = m._construire()
    assert boutons, "aucun bouton construit"
    m._dessiner(screen, (0, 0))
    pygame.display.flip()
print("1. rendu accueil/rejoindre : OK")

# ------------------------------------------- 2. identifiants par écran
m = Menu()
m.ecran = "accueil"
assert [b.id for b in m._construire()] == ["heberger", "rejoindre", "quitter"]
m.ecran = "rejoindre"
assert [b.id for b in m._construire()] == ["rafraichir", "connecter", "retour"]
m.serveurs = [{"host": "192.168.1.20", "port": 5555}]
assert "serveur_0" in [b.id for b in m._construire()]
print("2. identifiants des boutons par écran : OK")

# ------------------------------------------------------- 3. configurations
m = Menu()
m.champs["nom"].valeur = " Alice "
assert m._activer("heberger") == {"action": "host", "nom": "Alice"}

m = Menu()
assert m._activer("rejoindre") is None and m.ecran == "rejoindre"
m.serveurs = [{"host": "192.168.1.20", "port": 6000}]
cfg = m._activer("serveur_0")
assert cfg == {"action": "join", "host": "192.168.1.20", "port": 6000,
               "nom": None}, cfg
print("3. config hébergement + partie détectée : OK")

m = Menu()
m.champs["host"].valeur = " 10.0.0.5 "
cfg = m._activer("connecter")
assert cfg == {"action": "join", "host": "10.0.0.5", "port": 5555,
               "nom": None}, cfg
m.champs["host"].valeur = "10.0.0.5:6001"
assert m._activer("connecter")["port"] == 6001
m.champs["host"].valeur = "10.0.0.5:abc"
assert m._activer("connecter") is None and m.erreur
print("   config IP saisie (IP:port ou port par défaut) : OK")

# ------------------------------------------------- 4. adresse vide refusée
m = Menu()
assert m._activer("connecter") is None and m.erreur
print("4. adresse vide refusée : OK")

# ------------------------------- 5. quitter / retour / saisie clavier
m = Menu()
assert m._activer("quitter") is _QUITTER
ev_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
assert m._touche(ev_esc) is _QUITTER
m._activer("rejoindre")
assert m._touche(ev_esc) is None and m.ecran == "accueil"
assert m._activer("retour") is None and m.ecran == "accueil"

c = ChampTexte("x", "libellé", "")
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, unicode="b"))
assert c.valeur == "ab"
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
assert c.valeur == "a"
print("5. quitter / retour / saisie clavier : OK")

# --------------------------------------- 6. découverte UDP locale
import discovery
port_udp_test = 56789
discovery.PORT_DECOUVERTE = port_udp_test
annonce = Annonceur(port_tcp=5555, host="127.0.0.1")
annonce.PORT_DECOUVERTE = port_udp_test
# l'annonceur lit la constante globale au moment du bind
try:
    assert annonce.demarrer(), "bind UDP impossible"
    trouves = chercher_serveurs(delai=0.8, port=port_udp_test)
    assert {"host": "127.0.0.1", "port": 5555} in trouves, trouves
    print(f"6. découverte UDP : {trouves} : OK")
finally:
    annonce.arreter()

print("test_menu : TOUS OK")
