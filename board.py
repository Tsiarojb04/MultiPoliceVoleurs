# -*- coding: utf-8 -*-
"""
board.py — Définition du plateau du « Jeu du Gendarme et du Voleur »
(Fanorona simplifié / jeu de piste circulaire), conforme à Jeu.png.

Le plateau est un GRAPHE : des nœuds (intersections) reliés par des arêtes
(les lignes tracées). Ce module est volontairement SANS pygame afin que
le serveur réseau puisse l'importer aussi.

Géométrie (repère centré sur l'écran ; grand cercle de rayon R = 1) :
  * UN grand cercle de rayon R ;
  * les axes horizontal et vertical, tracés de bord en bord du grand
    cercle : de (cx-R, cy) à (cx+R, cy) et de (cx, cy-R) à (cx, cy+R) ;
  * un petit cercle central concentrique, de rayon r = R_PETIT ;
  * 4 ANSES INTERNES : demi-cercles dont le cercle est centré
    EXACTEMENT sur l'intersection du grand cercle avec l'axe (la
    « porte » N, E, S ou W) et de rayon ANSE_R — mais courbés VERS
    L'INTÉRIEUR du grand cercle : l'arc du haut descend vers le
    centre, celui du bas remonte, celui de gauche va vers la droite,
    celui de droite vers la gauche. Chaque anse se raccorde au grand
    cercle en deux points de part et d'autre de la porte et croise
    l'axe en son sommet (l'axe est donc coupé au sommet de l'anse).

Chaque pion se déplace d'UN nœud à un nœud ADJACENT en suivant une arête.
"""

import math

# ---------------------------------------------------------------------------
# Paramètres (coordonnées normalisées : le grand cercle a un rayon de 1.0,
# soit R pixels à l'écran ; ex. R = 200 px, r = 50 px -> R_PETIT = 0.25)
# ---------------------------------------------------------------------------
R_PETIT = 0.25            # rayon r du petit cercle central
ANSE_R = 0.30             # rayon de chaque demi-cercle intérieur (l'anse)
R_MAX = 1.0               # portée maximale du dessin (le grand cercle)

# ---------------------------------------------------------------------------
# Les nœuds du graphe : identifiant -> (x, y) normalisé
# ---------------------------------------------------------------------------
NODES = {
    # Le centre (départ du voleur, milieu du petit cercle)
    "C": (0.0, 0.0),
    # Bord du petit cercle central (croisements axes × petit cercle)
    "tn": (0.0, -R_PETIT), "te": (R_PETIT, 0.0),
    "ts": (0.0, R_PETIT),  "tw": (-R_PETIT, 0.0),
    # Les 4 portes : intersections du grand cercle avec les axes
    "N": (0.0, -1.0), "E": (1.0, 0.0), "S": (0.0, 1.0), "W": (-1.0, 0.0),
    # Sommets des anses internes : sur l'axe, à la distance ANSE_R EN
    # DEÇÀ de la porte (courbés vers le centre (cx, cy))
    "aN": (0.0, -1.0 + ANSE_R), "aE": (1.0 - ANSE_R, 0.0),
    "aS": (0.0, 1.0 - ANSE_R),  "aW": (-1.0 + ANSE_R, 0.0),
}

# Points de raccord des anses sur le grand cercle, de part et d'autre de
# chaque porte : (porte, côté) -> nom du nœud (côté +1 = sens horaire).
_SIDE_NAME = {
    ("N", +1): "nE", ("N", -1): "nW",
    ("E", +1): "eS", ("E", -1): "eN",
    ("S", +1): "sW", ("S", -1): "sE",
    ("W", +1): "wN", ("W", -1): "wS",
}


def _anse_attach(card, side):
    """Coordonnées du point où l'anse de la porte `card` rejoint le grand
    cercle (côté `side` = ±1).

    L'anse est le cercle de rayon ANSE_R centré sur la porte (qui est à
    distance 1 du centre du plateau) : il recoupe le grand cercle en deux
    points symétriques par rapport à l'axe, à ANSE_R de la porte."""
    ux, uy = NODES[card]                    # direction centre -> porte
    s = 1.0 - ANSE_R ** 2 / 2.0            # position le long de l'axe
    d = math.sqrt(max(0.0, 1.0 - s * s))   # écart latéral
    px, py = -uy, ux                       # perpendiculaire à l'axe
    return (s * ux + side * d * px, s * uy + side * d * py)


for (_card, _side), _name in _SIDE_NAME.items():
    NODES[_name] = _anse_attach(_card, _side)

# ---------------------------------------------------------------------------
# Les arêtes : chaque couple est une ligne tracée sur le plateau.
# ---------------------------------------------------------------------------
EDGES = [
    # Axes (du centre au bord du petit cercle)
    ("C", "tn"), ("C", "te"), ("C", "ts"), ("C", "tw"),
    # Petit cercle central
    ("tn", "te"), ("te", "ts"), ("ts", "tw"), ("tw", "tn"),
    # Axes (du petit cercle aux portes) — coupés au SOMMET de chaque
    # anse, car l'anse interne croise l'axe en son sommet
    ("tn", "aN"), ("aN", "N"),
    ("te", "aE"), ("aE", "E"),
    ("ts", "aS"), ("aS", "S"),
    ("tw", "aW"), ("aW", "W"),
    # Grand cercle extérieur (dans le sens horaire)
    ("N", "nE"), ("nE", "eN"), ("eN", "E"), ("E", "eS"),
    ("eS", "sE"), ("sE", "S"), ("S", "sW"), ("sW", "wS"),
    ("wS", "W"), ("W", "wN"), ("wN", "nW"), ("nW", "N"),
    # Les 4 anses internes : demi-cercles centrés sur les portes, courbés
    # vers le centre, raccordés au grand cercle de part et d'autre
    ("nW", "aN"), ("aN", "nE"),    # anse du haut   (porte N)
    ("eN", "aE"), ("aE", "eS"),    # anse de droite (porte E)
    ("sE", "aS"), ("aS", "sW"),    # anse du bas    (porte S)
    ("wN", "aW"), ("aW", "wS"),    # anse de gauche (porte W)
]

# Table d'adjacence : nœud -> ensemble des voisins
NEIGHBORS = {node: set() for node in NODES}
for a, b in EDGES:
    NEIGHBORS[a].add(b)
    NEIGHBORS[b].add(a)

# Les quatre « portes » du circuit extérieur : le voleur doit toutes les
# visiter (depuis sa sortie du centre) puis revenir au centre pour gagner.
GATES = ("N", "E", "S", "W")
CENTER = "C"


def anse_points(card, steps=48):
    """Points (x, y) normalisés échantillonnant le demi-cercle INTÉRIEUR
    (l'« anse ») de la porte `card` ("N", "E", "S" ou "W").

    L'anse est l'arc du cercle de rayon ANSE_R centré sur la porte, tracé
    À L'INTÉRIEUR du grand cercle : du point de raccord côté +1, en
    passant par le sommet (sur l'axe, à ANSE_R de la porte en direction
    du centre), jusqu'au point de raccord côté -1."""
    cx, cy = NODES[card]
    a = ANSE_R
    phi = math.atan2(cy, cx)               # direction centre -> porte
    s = 1.0 - a ** 2 / 2.0
    beta = math.acos(max(-1.0, min(1.0, (s - 1.0) / a)))
    ouverture = 2.0 * math.pi - 2.0 * beta  # l'arc intérieur (< 180°)
    pts = []
    for i in range(steps + 1):
        t = (phi + beta) + (ouverture * i / steps)
        pts.append((cx + a * math.cos(t), cy + a * math.sin(t)))
    return pts


if __name__ == "__main__":
    # Petit auto-test console (sans pygame)
    print(f"{len(NODES)} nœuds, {len(EDGES)} arêtes")
    for n in sorted(NODES):
        print(f"  {n:>3} {NODES[n]}  degré={len(NEIGHBORS[n])} voisins={sorted(NEIGHBORS[n])}")
    # vérifications géométriques des anses internes
    ok = True
    for card in ("N", "E", "S", "W"):
        pts = anse_points(card)
        sommet = pts[len(pts) // 2]
        deb, fin = pts[0], pts[-1]
        porte = NODES[card]
        # le sommet est sur l'axe, à ANSE_R de la porte EN DIRECTION du
        # centre (donc à l'intérieur du grand cercle)
        attendu = (porte[0] * (1.0 - ANSE_R), porte[1] * (1.0 - ANSE_R))
        sommet_ok = (abs(sommet[0] - attendu[0]) < 1e-9
                     and abs(sommet[1] - attendu[1]) < 1e-9)
        # les extrémités sont sur le grand cercle et coïncident avec les
        # nœuds de raccord
        sur_cercle = abs(math.hypot(*deb) - 1.0) < 1e-9 and abs(math.hypot(*fin) - 1.0) < 1e-9
        side_moins = NODES[_SIDE_NAME[(card, -1)]]
        side_plus = NODES[_SIDE_NAME[(card, +1)]]
        raccord = (abs(deb[0] - side_plus[0]) < 1e-9 and abs(deb[1] - side_plus[1]) < 1e-9
                   and abs(fin[0] - side_moins[0]) < 1e-9 and abs(fin[1] - side_moins[1]) < 1e-9)
        # tout point de l'arc est à l'intérieur (ou sur) le grand cercle
        interieur = all(math.hypot(*p) <= 1.0 + 1e-9 for p in pts)
        print(f"anse {card} : sommet ({sommet[0]:+.3f},{sommet[1]:+.3f}) "
              f"interne={sommet_ok} raccords={sur_cercle and raccord} "
              f"arc_intérieur={interieur}")
        ok = ok and sommet_ok and sur_cercle and raccord and interieur
    print("Auto-test géométrie :", "OK" if ok else "ECHEC")
