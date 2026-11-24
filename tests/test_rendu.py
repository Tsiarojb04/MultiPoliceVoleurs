# -*- coding: utf-8 -*-
"""test_rendu.py — Vérifications PIXELS du rendu (render.py) sur 5 tailles
de fenêtre (mode responsive), avec le pilote vidéo « dummy ».

Vérifie notamment :
  * le fond, la barre d'état, le centre EXACT du plateau à chaque taille ;
  * le voleur rouge au centre et les 3 policiers bleus en tn / aW / aE ;
  * les axes, le grand cercle, le petit cercle, les arcs des anses ;
  * rien en dehors du grand cercle, et AUCUN texte sur la zone de plateau
    (minimalisme : seules les couleurs du plateau et des pions y sont
    autorisées) ;
  * l'anneau de sélection jaune et les anneaux verts des destinations ;
  * la barre d'état contient du texte (en français).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()

from board import R_PETIT, anse_points
from game import Game
from render import (COL_BG, COL_BOARD, COL_COP, COL_SEL, COL_STATUS_BG,
                    COL_TARGET, COL_THIEF, STATUS_H, Layout, draw_scene,
                    draw_status)

TAILLES = [(480, 540), (640, 700), (880, 920), (1200, 1000), (1600, 1100)]
NB = 0


def ok(cond, label):
    global NB
    assert cond, f"ÉCHEC : {label}"
    NB += 1


def autour(screen, pos, couleur, marge=3):
    """True si `couleur` apparaît près de `pos` (fenêtre (2m+1)²)."""
    x, y = pos
    w, h = screen.get_size()
    for dx in range(-marge, marge + 1):
        for dy in range(-marge, marge + 1):
            if 0 <= x + dx < w and 0 <= y + dy < h:
                if screen.get_at((x + dx, y + dy))[:3] == couleur:
                    return True
    return False


# couleurs autorisées sur la ZONE DE PLATEAU (minimalisme : aucun texte)
AUTORISES = {COL_BG, COL_BOARD, COL_THIEF, COL_COP, (255, 255, 255)}

for (w, h) in TAILLES:
    screen = pygame.display.set_mode((w, h))
    layout = Layout(w, h)
    cx, cy = layout.center
    s = layout.scale
    etiquette = f"{w}x{h}"

    # ---------------------------------------------------------- mise en page
    ok(layout.center == (w // 2, (h - STATUS_H) // 2),
       f"centre exact du plateau {etiquette}")
    ok(30 <= s <= min(w, h - STATUS_H) / 2, f"échelle ajustée {etiquette}")
    ok(4 <= layout.pawn_r <= 18, f"rayon des pions borné {etiquette}")
    ok(layout.hit_r >= 12, f"rayon de clic {etiquette}")
    ok(cx - s >= 0 and cx + s <= w and cy - s >= 0 and cy + s <= h - STATUS_H,
       f"plateau entièrement visible {etiquette}")

    # ------------------------------------------------------------- rendu base
    g = Game()
    draw_scene(screen, layout, g)
    ok(screen.get_at((3, 3))[:3] == COL_BG, f"fond {etiquette}")
    ok(screen.get_at((w - 5, h - STATUS_H // 2))[:3] == COL_STATUS_BG,
       f"barre d'état {etiquette}")

    # ---------------------------------------------------------------- pions
    ok(screen.get_at(layout.to_screen("C"))[:3] == COL_THIEF,
       f"voleur rouge au centre {etiquette}")
    for cop in ("tn", "aW", "aE"):
        ok(screen.get_at(layout.to_screen(cop))[:3] == COL_COP,
           f"policier bleu en {cop} {etiquette}")

    # --------------------------------------------------------------- plateau
    ok(autour(screen, (cx + int(s * 0.5), cy), COL_BOARD),
       f"axe horizontal {etiquette}")
    ok(autour(screen, (cx, cy + int(s * 0.5)), COL_BOARD),
       f"axe vertical {etiquette}")
    ok(autour(screen, (cx + int(s * 0.707), cy - int(s * 0.707)),
              COL_BOARD, 4), f"grand cercle {etiquette}")
    px = cx + int(R_PETIT * s * 0.866)
    py = cy - int(R_PETIT * s * 0.5)
    ok(autour(screen, (px, py), COL_BOARD, 4), f"petit cercle {etiquette}")
    # arcs des anses internes (hors axes : points réellement sur l'arc)
    for card in ("N", "E"):
        ax, ay = layout.to_screen(anse_points(card)[12])
        ok(autour(screen, (ax, ay), COL_BOARD, 4), f"arc d'anse {card} {etiquette}")
    # rien au-delà du grand cercle, sur l'axe horizontal
    ok(screen.get_at((cx + int(s * 1.08), cy))[:3] == COL_BG,
       f"extérieur du grand cercle vide {etiquette}")

    # ------------------------------------------- minimalisme : aucun texte
    mauvais = None
    for y in range(0, h - STATUS_H, 4):
        for x in range(0, w, 4):
            if screen.get_at((x, y))[:3] not in AUTORISES:
                mauvais = (x, y)
                break
        if mauvais:
            break
    ok(mauvais is None,
       f"zone de plateau sans texte ni point superflu {etiquette} {mauvais}")

    # ----------------------------------------- sélection et destinations
    g2 = Game()
    cibles = g2.legal_targets("voleur", "C")
    ok(sorted(cibles) == ["te", "ts", "tw"],
       f"3 destinations légales au départ {etiquette}")
    draw_scene(screen, layout, g2, selected="C", targets=cibles,
               info="", langue="fr")
    ok(autour(screen, (cx + layout.pawn_r + 5, cy), COL_SEL, 2),
       f"anneau de sélection jaune {etiquette}")
    for t in cibles:
        tx, ty = layout.to_screen(t)
        ok(autour(screen, (tx + layout.pawn_r + 4, ty), COL_TARGET, 2),
           f"destination verte {t} {etiquette}")

    # ------------------------------------------------------- pick_node
    ok(layout.pick_node(layout.to_screen("C")) == "C",
       f"clic exact sur le voleur {etiquette}")
    ok(layout.pick_node((5, 5)) is None, f"clic dans le vide {etiquette}")
    ok(layout.pick_node(layout.to_screen("N")) == "N",
       f"clic exact sur la porte N {etiquette}")

    # -------------------------------------------- texte présent dans la barre
    nb_texte = 0
    for y in range(h - STATUS_H + 4, h - 4, 3):
        for x in range(8, w - 8, 3):
            if screen.get_at((x, y))[:3] not in (COL_STATUS_BG,):
                nb_texte += 1
    ok(nb_texte > 10, f"barre d'état non vide {etiquette}")

    print(f"taille {etiquette} : OK")

# ----------------------------- barre d'état en français (une fois, 880x920)
screen = pygame.display.set_mode((880, 920))
layout = Layout(880, 920)
g3 = Game()
g3.winner = "voleur"
img = pygame.Surface((880, 920))
draw_status(img, layout, g3, "", "fr")
ok("GAGNE" in g3.status_text("fr"), "message de victoire français")
ok("circuit" in g3.progress_text("fr").lower(), "progression française")
print("rendu de la barre d'état (français) : OK")

print(f"test_rendu : TOUS OK - {NB + 2} vérifications")

