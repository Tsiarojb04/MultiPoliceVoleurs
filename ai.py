# -*- coding: utf-8 -*-
"""
ai.py — Intelligence artificielle du « Jeu du Gendarme et du Voleur ».

Trois niveaux de difficulté (noms malgaches, comme demandé) :

  * MORA (facile)     : l'IA choisit un coup au HASARD parmi les coups
                        valides — elle se contente de respecter les règles ;
  * ANTONONY (moyen)  : heuristique simple — la POLICE se rapproche des
                        chemins du voleur (lui-même et sa prochaine porte),
                        le VOLEUR fuit la police tout en avançant vers
                        l'objectif de son circuit ;
  * SAROTRA (difficile): recherche adversariale MINIMAX avec élagage
                        ALPHA-BÊTA et approfondissement itératif (limite de
                        temps) — la police maximise le blocage, le voleur
                        maximise son évasion / son bouclage de circuit.

Utilisation :

    from ai import choisir_coup
    frm, to = choisir_coup(game, POLICE, "sarotra")   # None si bloqué

Le module ne dépend que de board.py / game.py (pas de pygame) : il est
testable en console et utilisable partout.
"""

import random
import time

from board import CENTER, GATES, NEIGHBORS
from game import POLICE, VOLEUR

# Identifiants des niveaux (ce sont aussi les clés de traduction
# "niveau_mora" / "niveau_antonony" / "niveau_sarotra" dans locales.py)
NIVEAUX = ("mora", "antonony", "sarotra")
NIVEAU_DEFAUT = "antonony"

# ---------------------------------------------------------------------------
# Distances sur le graphe : BFS toutes-paires, précalculé à l'import
# (le plateau n'a que 21 nœuds ; c'est instantané et l'évaluation de
# l'IA devient une simple lecture de table).
# ---------------------------------------------------------------------------
def _bfs(source):
    dist = {source: 0}
    file = [source]
    while file:
        u = file.pop(0)
        for v in NEIGHBORS[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                file.append(v)
    return dist


DISTANCES = {n: _bfs(n) for n in NEIGHBORS}
_INFINI = 99        # « très loin » (nœuds non connexes ; n'arrive pas ici)


def dist(a, b):
    """Distance (nombre d'arêtes) entre deux nœuds du plateau."""
    return DISTANCES[a].get(b, _INFINI)


# ---------------------------------------------------------------------------
# Évaluation d'une position : score POSITIF = situation bonne pour le
# VOLEUR, négatif = bonne pour la POLICE. Utilisée par ANTONONY (1 coup
# d'anticipation) et par SAROTRA (feuilles du minimax).
# ---------------------------------------------------------------------------
def _portes_restantes(g):
    return [p for p in GATES if p not in g.gates_visited]


def _objectif_voleur(g):
    """Prochaine étape du circuit du voleur : la porte non visitée la
    plus proche, ou le centre s'il a tout visité (il doit rentrer)."""
    restantes = _portes_restantes(g)
    if not restantes:
        return CENTER
    return min(restantes, key=lambda p: dist(g.thief, p))


def evaluer(g):
    """Heuristique d'évaluation de l'état `g` (voir docstring du module)."""
    if g.winner == VOLEUR:
        # gagner VITE vaut mieux que gagner lentement
        return 1_000_000 - 10 * g.move_count
    if g.winner == POLICE:
        return -1_000_000 + 10 * g.move_count

    score = 0
    # --- progression du circuit (le vrai objectif du voleur)
    score += 40 * len(g.gates_visited)
    # --- avancer vers l'objectif (porte suivante / retour au centre)
    score -= 6 * dist(g.thief, _objectif_voleur(g))
    # --- fuir : distance au policier le plus proche
    dmin = min(dist(g.thief, c) for c in g.cops)
    score += 5 * dmin
    # --- mobilité du voleur (être bloqué = perdre)
    score += 6 * len(g.legal_moves(VOLEUR))
    # --- pression policière sur les chemins du voleur : plus les
    #     policiers sont proches des portes restantes, plus c'est mauvais
    restantes = _portes_restantes(g)
    if restantes:
        garde = sum(min(dist(c, p) for c in g.cops) for p in restantes)
        score -= 2 * garde
    return score


# ---------------------------------------------------------------------------
# Niveau ANTONONY : heuristique à un coup.
# ---------------------------------------------------------------------------
def _score_heuristique(g, role, frm, to):
    """Qualité « à la main » du coup (frm -> to) pour `role`.

    * POLICE : se rapprocher du voleur ET de sa prochaine porte (couper
      les chemins du circuit) ;
    * VOLEUR : fuir le policier le plus proche tout en avançant vers
      l'objectif, avec un gros bonus s'il visite sa prochaine porte
      (ou s'il rentre au centre après un tour complet).
    """
    cible = _objectif_voleur(g)
    if role == POLICE:
        return -(2 * dist(to, g.thief) + dist(to, cible))
    # voleur : après le coup il est sur `to`, les policiers ne bougent pas
    fuite = min(dist(to, c) for c in g.cops)
    s = 2 * fuite - 3 * dist(to, cible)
    if to == cible:
        s += 12          # visiter la porte suivante / rentrer à la fin
    return s


def coup_heuristique(g, role, coups):
    """Meilleur coup selon l'heuristique (avec un léger bruit pour varier)."""
    meilleur, meilleur_score = None, None
    for coup in coups:
        s = _score_heuristique(g, role, *coup) + random.uniform(0.0, 0.5)
        if meilleur_score is None or s > meilleur_score:
            meilleur, meilleur_score = coup, s
    return meilleur


# ---------------------------------------------------------------------------
# Niveau SAROTRA : minimax + élagage alpha-bêta + approfondissement itératif.
# ---------------------------------------------------------------------------
class _TempsEcoule(Exception):
    """Interne : la limite de temps de la recherche est atteinte."""


def _ordre_coups(g, role, coups):
    """Trie les coups du « probablement le meilleur » au moins bon, pour
    rendre l'élagage alpha-bêta plus efficace."""
    return sorted(coups,
                  key=lambda c: _score_heuristique(g, role, c[0], c[1]),
                  reverse=True)


def _alphabeta(g, profondeur, alpha, beta, echuance):
    """Recherche adversariale : le VOLEUR maximise evaluer(), la POLICE
    le minimise. `echuance` est l'instant (time.perf_counter) au-delà
    duquel la recherche s'interrompt."""
    if time.perf_counter() > echuance:
        raise _TempsEcoule
    if g.winner is not None or profondeur == 0:
        return evaluer(g)

    role = g.turn
    coups = g.legal_moves(role)
    if not coups:                      # défense : état sans coup jouable
        return evaluer(g)

    if role == VOLEUR:                 # --- nœud MAX ---
        meilleur = -float("inf")
        for frm, to in _ordre_coups(g, role, coups):
            g2 = g.clone()
            g2.move(VOLEUR, frm, to)
            meilleur = max(meilleur,
                           _alphabeta(g2, profondeur - 1, alpha, beta, echuance))
            alpha = max(alpha, meilleur)
            if beta <= alpha:
                break                  # élagage bêta
        return meilleur
    # --- nœud MIN (police) ---
    pire = float("inf")
    for frm, to in _ordre_coups(g, role, coups):
        g2 = g.clone()
        g2.move(POLICE, frm, to)
        pire = min(pire,
                   _alphabeta(g2, profondeur - 1, alpha, beta, echuance))
        beta = min(beta, pire)
        if beta <= alpha:
            break                      # élagage alpha
    return pire


def coup_recherche(g, role, coups, profondeur_max=6, temps_max=1.0):
    """Meilleur coup par minimax / alpha-bêta, avec approfondissement
    itératif : on augmente la profondeur (2, 3, 4...) jusqu'à la limite
    de temps et on garde le meilleur résultat COMPLET obtenu (celui de
    la dernière profondeur terminée dans les temps)."""
    coups = _ordre_coups(g, role, coups)
    meilleur = coups[0]                     # repli : meilleur coup heuristique
    for profondeur in range(2, profondeur_max + 1):
        echuance = time.perf_counter() + temps_max
        alpha, beta = -float("inf"), float("inf")
        meilleur_valeur = None
        meilleur_coup_prof = meilleur       # si la recherche est interrompue
        try:
            for frm, to in coups:
                g2 = g.clone()
                g2.move(role, frm, to)
                v = _alphabeta(g2, profondeur - 1, alpha, beta, echuance)
                if role == VOLEUR:          # le joueur rechercheur maximise
                    if meilleur_valeur is None or v > meilleur_valeur:
                        meilleur_valeur, meilleur_coup_prof = v, (frm, to)
                    alpha = max(alpha, v)
                else:                      # ... ou minimise
                    if meilleur_valeur is None or v < meilleur_valeur:
                        meilleur_valeur, meilleur_coup_prof = v, (frm, to)
                    beta = min(beta, v)
        except _TempsEcoule:
            break                           # on garde la profondeur précédente
        # profondeur terminée dans les temps : résultat retenu, et le
        # coup gagnant passe en tête pour la suivante (meilleur élagage)
        meilleur = meilleur_coup_prof
        coups.remove(meilleur)
        coups.insert(0, meilleur)
    return meilleur


# ---------------------------------------------------------------------------
# Point d'entrée unique
# ---------------------------------------------------------------------------
def choisir_coup(game, role, niveau=NIVEAU_DEFAUT):
    """Choisit le coup de l'IA pour `role` ("voleur" ou "police") au
    niveau `niveau` ("mora", "antonony" ou "sarotra").

    Renvoie un couple (frm, to), ou None si aucun coup légal n'existe
    (l'IA est elle-même bloquée)."""
    if role not in (VOLEUR, POLICE):
        raise ValueError(f"rôle inconnu : {role}")
    if niveau not in NIVEAUX:
        niveau = NIVEAU_DEFAUT

    coups = game.legal_moves(role)
    if not coups:
        return None

    if niveau == "mora":               # --- FACILE : pur hasard ---
        return random.choice(coups)
    if niveau == "antonony":           # --- MOYEN : heuristique ---
        return coup_heuristique(game, role, coups)
    # --- DIFFICILE : minimax + alpha-bêta ---
    return coup_recherche(game, role, coups)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Auto-test en console : chaque niveau joue les deux rôles, on vérifie
    # que les coups renvoyés sont légaux, puis une partie complète
    # « sarotra (voleur) vs mora (police) » doit être gagnée par le voleur.
    from game import Game, IllegalMove

    for niveau in NIVEAUX:
        for role in (VOLEUR, POLICE):
            g = Game()
            if role == POLICE:
                g.move(VOLEUR, "C", "te")     # on donne le tour à la police
            coup = choisir_coup(g, role, niveau)
            assert coup is not None and coup in g.legal_moves(role), \
                (niveau, role, coup)
            print(f"OK  niveau {niveau:>8} / rôle {role:<6} "
                  f"-> coup proposé {coup[0]} → {coup[1]}")

    # parties complètes IA contre IA
    def partie(niveau_voleur, niveau_police, plafond=400):
        g = Game()
        while g.winner is None and g.move_count < plafond:
            coup = choisir_coup(g, g.turn, niveau_voleur if g.turn == VOLEUR
                               else niveau_police)
            if coup is None:
                break
            g.move(g.turn, *coup)
        return g

    t0 = time.perf_counter()
    g = partie("sarotra", "mora")
    print(f"sarotra (voleur) vs mora (police) : vainqueur = {g.winner} "
          f"en {g.move_count} coups ({time.perf_counter() - t0:.1f}s)")
    assert g.winner == VOLEUR, "le voleur sarotra doit battre la police mora"

    t0 = time.perf_counter()
    g = partie("mora", "sarotra")
    print(f"mora (voleur) vs sarotra (police) : vainqueur = {g.winner} "
          f"en {g.move_count} coups ({time.perf_counter() - t0:.1f}s)")
    assert g.winner == POLICE, "la police sarotra doit battre le voleur mora"
    print("Auto-test IA : OK")
