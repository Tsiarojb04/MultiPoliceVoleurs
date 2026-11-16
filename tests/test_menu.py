# -*- coding: utf-8 -*-
"""test_menu.py — Tests non interactifs du menu de démarrage (menu.py).

Vérifie, avec le pilote vidéo « dummy » (aucune fenêtre réelle) :
  1. le rendu des trois écrans (mode / solo / ligne) en FR et en MG ;
  2. les identifiants des boutons construits sur chaque écran ;
  3. la construction des configurations via _activer : solo (rôle +
     niveau), local, ligne (host / port / nom / rôle) ;
  4. la validation du port (message d'erreur inline) ;
  5. la sentinelle _QUITTER, le bouton Retour, la bascule de langue ;
  6. la saisie clavier des champs texte (ChampTexte.taper) ;
  7. bonus : degrés du plateau (le blocage TOTAL de la police est-il
     possible ? — utile pour justifier le garde-fou ia_passe de main.py).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()
screen = pygame.display.set_mode((880, 920))

from board import NEIGHBORS
from menu import _QUITTER, ChampTexte, Menu

# ------------------------------------------------------------------ 1. rendu
for langue in ("fr", "mg"):
    m = Menu(langue)
    for ecran in ("mode", "solo", "ligne"):
        m.ecran = ecran
        boutons = m._construire()
        assert boutons, "aucun bouton construit"
        m._dessiner(screen, (0, 0))
        pygame.display.flip()
    print(f"1. rendu mode/solo/ligne [{langue}] : OK")

# ------------------------------------------- 2. identifiants par écran
m = Menu("fr")
m.ecran = "mode"
assert [b.id for b in m._construire()] == [
    "langue", "mode_solo", "mode_local", "mode_ligne", "quitter"]
m.ecran = "solo"
assert [b.id for b in m._construire()] == [
    "langue", "role_voleur", "role_police",
    "niveau_mora", "niveau_antonony", "niveau_sarotra",
    "retour", "commencer"]
m.ecran = "ligne"
assert [b.id for b in m._construire()] == [
    "langue", "ligne_role_voleur", "ligne_role_police", "ligne_role_any",
    "retour", "commencer"]
print("2. identifiants des boutons par écran : OK")

# -------------------------------------------------------- 3. config SOLO
m = Menu("fr")
assert m._activer("mode_solo") is None and m.ecran == "solo"
assert m._activer("role_police") is None and m.role == "police"
assert m._activer("niveau_sarotra") is None and m.niveau == "sarotra"
cfg = m._activer("commencer")
assert cfg == {"mode": "solo", "role": "police", "niveau": "sarotra",
               "langue": "fr"}, cfg
print("3. config solo (police / sarotra / fr) : OK")

m = Menu("mg")                       # valeurs par défaut : voleur / antonony
m._activer("mode_solo")
cfg = m._activer("commencer")
assert cfg == {"mode": "solo", "role": "voleur", "niveau": "antonony",
               "langue": "mg"}, cfg
print("   défauts (voleur / antonony / mg) : OK")

# ------------------------------------------------------- 4. config LOCAL
m = Menu("fr")
assert m._activer("mode_local") == {"mode": "local", "langue": "fr"}
print("4. config local : OK")

# ------------------------------------------------------- 5. config LIGNE
m = Menu("fr")
m._activer("mode_ligne")
assert m.ecran == "ligne"
m.champs["port"].valeur = "abc"            # port non numérique
assert m._activer("commencer") is None and m.erreur, "port 'abc' accepté !"
m.champs["port"].valeur = "99999"          # hors bornes
assert m._activer("commencer") is None and m.erreur, "port 99999 accepté !"
m.champs["host"].valeur = "192.168.1.20"
m.champs["port"].valeur = " 5555 "
m.champs["nom"].valeur = "Alice"
m._activer("ligne_role_police")
cfg = m._activer("commencer")
assert cfg == {"mode": "ligne", "host": "192.168.1.20", "port": 5555,
               "nom": "Alice", "role": "police", "langue": "fr"}, cfg
print("5. config ligne (validation du port incluse) : OK")

m = Menu("fr")                             # nom vide -> None, rôle any
m._activer("mode_ligne")
cfg = m._activer("commencer")
assert cfg["nom"] is None and cfg["role"] == "any" and cfg["host"] == "127.0.0.1"
print("   défauts ligne (127.0.0.1:5555, nom None, any) : OK")

# --------------------------------------- 6. quitter / Échap / retour / langue
m = Menu("fr")
assert m._activer("quitter") is _QUITTER
ev_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
m.ecran = "mode"
assert m._touche(ev_esc) is _QUITTER
m.ecran = "solo"
assert m._touche(ev_esc) is None and m.ecran == "mode"      # retour
m._activer("langue"); assert m.langue == "mg"
m._activer("langue"); assert m.langue == "fr"
print("6. quitter / Échap / retour / bascule langue : OK")

# --------------------------------------------------------- 7. ChampTexte
c = ChampTexte("x", "libellé", "")
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, unicode="b"))
assert c.valeur == "ab"
c.taper(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
assert c.valeur == "a"
print("7. saisie ChampTexte : OK")

# -------------------------------------------------------- 8. degrés plateau
degres = {n: len(v) for n, v in NEIGHBORS.items()}
print(f"8. degrés des {len(degres)} nœuds : min={min(degres.values())}, "
      f"max={max(degres.values())}, "
      f"moyen={sum(degres.values()) / len(degres):.2f}")

print("test_menu : TOUS OK")

