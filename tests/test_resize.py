# -*- coding: utf-8 -*-
"""test_resize.py — Test du REDIMENSIONNEMENT (fenêtre responsive).

Le pilote vidéo « dummy » n'applique pas réellement les changements de
taille de fenêtre : on vérifie donc ici
  1. que Layout recalcule correctement centre / échelle / pions pour un
     grand éventail de tailles (le plateau reste entier, exactement
     centré, et la souris reste cliquable) ;
  2. que la séquence de main.py / client.py (clamp aux tailles minimales
     puis recréation du Layout) est cohérente et ne casse jamais la
     mise en page ;
  3. que set_mode n'échoue pour aucune taille testée.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()

from game import Game
from render import STATUS_H, Layout, draw_scene

MIN_W, MIN_H = 480, 540          # mêmes constantes que main.py / client.py

TAILLES = [(480, 540), (640, 700), (880, 920), (1200, 1000),
           (1600, 1100), (2000, 1500)]

for (w, h) in TAILLES:
    screen = pygame.display.set_mode((w, h))       # ne doit pas échouer
    lay = Layout(w, h)
    cx, cy = lay.center

    assert lay.center == (w // 2, (h - STATUS_H) // 2), (w, h)
    assert 30 <= lay.scale <= min(w, h - STATUS_H) / 2, (w, h)
    assert 4 <= lay.pawn_r <= 18, (w, h)
    assert lay.hit_r >= 12, (w, h)
    assert cx - lay.scale >= 0 and cx + lay.scale <= w, (w, h)
    assert cy - lay.scale >= 0 and cy + lay.scale <= h - STATUS_H, (w, h)

    # la souris reste cliquable sur tous les nœuds, à toutes les échelles
    for n in ("C", "N", "aS", "wN", "eS"):
        assert lay.pick_node(lay.to_screen(n)) == n, (w, h, n)

    # un rendu complet à chaque taille ne lève aucune erreur
    draw_scene(screen, lay, Game(), langue="fr")
    print(f"taille {w}x{h} : centre={lay.center}, échelle={lay.scale:.0f}, "
          f"pion={lay.pawn_r} -> OK")

# ------------------------------------------------- clamp aux tailles minimales
# (logique exacte de main.py / client.py sur VIDEORESIZE)
for (ew, eh, attendu) in [(-50, 100, (480, 540)), (300, 300, (480, 540)),
                          (500, 600, (500, 600)), (900, 400, (900, 540))]:
    w, h = max(MIN_W, ew), max(MIN_H, eh)
    assert (w, h) == attendu, (ew, eh, attendu)
    lay = Layout(w, h)
    assert 30 <= lay.scale <= min(w, h - STATUS_H) / 2, attendu
    assert lay.pick_node(lay.to_screen("C")) == "C", attendu
print("clamp aux tailles minimales : OK")

# ------------------------------ rendu après une suite de « redimensionnements »
# le Layout suit TOUJOURS la taille courante : jamais de débordement
screen = pygame.display.set_mode((880, 920))
for (w, h) in [(640, 700), (1200, 1000), (480, 540), (880, 920)]:
    screen = pygame.display.set_mode((w, h))
    lay = Layout(*screen.get_size())
    draw_scene(screen, lay, Game(), langue="mg")
    assert lay.scale <= min(w, h - STATUS_H) / 2
print("suite de redimensionnements + rendu MG : OK")

pygame.quit()          # évite un segfault SDL à la fermeture (dummy + set_mode répétés)
print("test_resize : TOUS OK")

