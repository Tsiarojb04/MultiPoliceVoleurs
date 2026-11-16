# -*- coding: utf-8 -*-
"""
render.py — Affichage Pygame du plateau et des pions.

Rendu volontairement MINIMALISTE, conforme au dessin à la main (Jeu.png) :
  * UN grand cercle extérieur ;
  * deux axes (horizontal et vertical) qui se croisent au centre ;
  * un petit cercle central ;
  * quatre demi-cercles (anses) INTÉRIEURS, centrés sur les
    intersections du grand cercle avec les axes (les portes N, E, S, W)
    et courbés vers le centre ; rien ne dépasse du grand cercle ;
  * aucun lettrage ni point d'intersection superflu : seuls les PIONS
    sont visibles (rouge = voleur, bleus = police), plus les indications
    de jeu (pion sélectionné, destinations légales, barre d'état).

Ce module centralise tout ce qui est graphique afin que main.py (jeu local)
et client.py (jeu en réseau) partagent exactement le même rendu.

AFFICHAGE RESPONSIVE : la fenêtre est redimensionnable (pygame.RESIZABLE).
La classe Layout recalcule le centre du plateau et le rayon du grand cercle
à partir de la taille actuelle de la fenêtre — tous les éléments (grand
cercle, axes, petit cercle, anses internes, pions) sont recalculés
proportionnellement et restent entièrement visibles, et le plateau reste
exactement centré, quelle que soit la dimension de la fenêtre.
"""

import math

import pygame

from board import NODES, R_MAX, R_PETIT, anse_points
from game import POLICE, VOLEUR
from locales import texte

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COL_BG = (24, 26, 34)
COL_BOARD = (196, 198, 206)
COL_THIEF = (232, 68, 57)
COL_COP = (66, 133, 244)
COL_SEL = (255, 214, 0)
COL_TARGET = (88, 214, 141)
COL_STATUS_BG = (15, 16, 22)
COL_TEXT = (230, 230, 235)
COL_TEXT_DIM = (150, 152, 165)

R_PAWN = 12            # rayon d'un pion (valeur de référence, échelle ~270 px)
R_HIT = 20             # rayon de détection à la souris (valeur de référence)

STATUS_H = 78          # hauteur de la barre d'état


# ---------------------------------------------------------------------------
# Polices
# ---------------------------------------------------------------------------
def load_font(size, bold=False):
    try:
        f = pygame.font.SysFont("segoe ui,arial,helvetica", size, bold=bold)
        if f:
            return f
    except Exception:
        pass
    return pygame.font.Font(None, size)


# ---------------------------------------------------------------------------
# Mise en page RESPONSIVE : coordonnées normalisées -> pixels
# ---------------------------------------------------------------------------
class Layout:
    """Mise en page dynamique, recalculée à partir de la taille ACTUELLE
    de la fenêtre (largeur × hauteur).

    La fenêtre est redimensionnable (pygame.RESIZABLE dans main.py /
    client.py) : à chaque événement pygame.VIDEORESIZE il suffit de
    recréer un Layout avec la nouvelle taille —

      * le centre du plateau reste EXACTEMENT au milieu de la zone de
        jeu (fenêtre moins la barre d'état) ;
      * le rayon du grand cercle (self.scale) est recalculé pour que
        TOUT le plateau (cercle, axes, petit cercle, anses internes)
        reste entièrement visible, quelle que soit la dimension ;
      * les pions et la sélection à la souris sont mis à l'échelle,
        eux aussi, proportionnellement au plateau.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.status_h = STATUS_H
        board_w, board_h = width, height - self.status_h
        # centre du plateau : exactement au milieu de la zone de jeu
        self.center = (board_w // 2, board_h // 2)
        # échelle dynamique : rayon du grand cercle en pixels, avec une
        # marge pour que le plateau reste entièrement visible
        marge = 26
        self.scale = max(30.0, (min(board_w, board_h) // 2 - marge) / R_MAX)
        # rayon des pions, proportionnel au plateau (borné pour rester
        # lisible en très petit / pas démesuré en très grand)
        self.pawn_r = max(4, min(18, int(round(self.scale * 0.045))))
        # rayon de détection à la souris (toujours cliquable)
        self.hit_r = max(12, self.pawn_r + 8)

    def to_screen(self, node_or_xy):
        x, y = node_or_xy if not isinstance(node_or_xy, str) else NODES[node_or_xy]
        cx, cy = self.center
        return (int(cx + x * self.scale), int(cy + y * self.scale))

    def pick_node(self, pos):
        """Nœud le plus proche du point (x, y) s'il est assez proche, sinon None."""
        best, dist_best = None, self.hit_r
        for node in NODES:
            sx, sy = self.to_screen(node)
            d = math.hypot(pos[0] - sx, pos[1] - sy)
            if d < dist_best:
                best, dist_best = node, d
        return best


# ---------------------------------------------------------------------------
# Plateau statique (strictement conforme au dessin de référence)
# ---------------------------------------------------------------------------
def draw_board(screen, layout):
    cx, cy = layout.center
    s = layout.scale

    # --- UN grand cercle extérieur ---
    pygame.draw.circle(screen, COL_BOARD, (cx, cy), int(s), width=3)

    # --- deux axes qui se croisent au centre (bord à bord du grand cercle) ---
    pygame.draw.line(screen, COL_BOARD, (cx - s, cy), (cx + s, cy), 2)
    pygame.draw.line(screen, COL_BOARD, (cx, cy - s), (cx, cy + s), 2)

    # --- petit cercle central ---
    pygame.draw.circle(screen, COL_BOARD, (cx, cy), int(R_PETIT * s), width=2)

    # --- quatre anses INTERNES : demi-cercles centrés sur les portes
    #     (intersections du grand cercle avec les axes), courbés vers le
    #     centre, raccordés au grand cercle de part et d'autre de la porte,
    #     croisées par l'axe en leur sommet ---
    for card in ("N", "E", "S", "W"):
        pts = [layout.to_screen(p) for p in anse_points(card)]
        pygame.draw.lines(screen, COL_BOARD, False, pts, 2)


# ---------------------------------------------------------------------------
# Pions, sélection, destinations légales
# ---------------------------------------------------------------------------
def draw_pieces(screen, layout, game):
    # voleur (rouge), exactement au centre du petit cercle au départ
    pr = layout.pawn_r
    tx, ty = layout.to_screen(game.thief)
    pygame.draw.circle(screen, COL_THIEF, (tx, ty), pr)
    pygame.draw.circle(screen, (255, 255, 255), (tx, ty), pr, 2)
    # police (bleus)
    for cop in game.cops:
        px, py = layout.to_screen(cop)
        pygame.draw.circle(screen, COL_COP, (px, py), pr)
        pygame.draw.circle(screen, (255, 255, 255), (px, py), pr, 2)


def draw_selection(screen, layout, node):
    sx, sy = layout.to_screen(node)
    pygame.draw.circle(screen, COL_SEL, (sx, sy), layout.pawn_r + 5, 3)


def draw_highlights(screen, layout, targets):
    for t in targets:
        sx, sy = layout.to_screen(t)
        pygame.draw.circle(screen, COL_TARGET, (sx, sy), layout.pawn_r + 4, 3)


# ---------------------------------------------------------------------------
# Barre d'état (bas de fenêtre)
# ---------------------------------------------------------------------------
def draw_status(screen, layout, game, info="", langue=None):
    rect = pygame.Rect(0, layout.height - layout.status_h, layout.width, layout.status_h)
    pygame.draw.rect(screen, COL_STATUS_BG, rect)

    f_titre = load_font(15, bold=True)
    f_txt = load_font(14)

    # ligne 1 : tour actuel / vainqueur (traduit FR / MG)
    if game.winner == VOLEUR:
        ligne1 = f_titre.render(texte("victoire_voleur", langue), True, COL_THIEF)
    elif game.winner == POLICE:
        ligne1 = f_titre.render(texte("victoire_police", langue), True, COL_COP)
    elif game.turn == VOLEUR:
        ligne1 = f_titre.render(texte("tour_voleur", langue), True, COL_THIEF)
    else:
        ligne1 = f_titre.render(texte("tour_police", langue), True, COL_COP)
    screen.blit(ligne1, (12, rect.y + 8))

    # ligne 2 : progression du circuit / fin de partie
    ligne2 = f_txt.render(game.progress_text(langue), True, COL_TEXT_DIM)
    screen.blit(ligne2, (12, rect.y + 32))

    # ligne 3 : message d'info éventuel
    if info:
        ligne3 = f_txt.render(info, True, COL_TEXT)
        screen.blit(ligne3, (12, rect.y + 55))


def draw_scene(screen, layout, game, selected=None, targets=(), info="", langue=None):
    """Rendu complet d'une frame (utilisé par main.py et client.py)."""
    screen.fill(COL_BG)
    draw_board(screen, layout)
    draw_pieces(screen, layout, game)
    if targets:
        draw_highlights(screen, layout, targets)
    if selected:
        draw_selection(screen, layout, selected)
    draw_status(screen, layout, game, info, langue)
