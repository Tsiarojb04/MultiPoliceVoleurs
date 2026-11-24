# -*- coding: utf-8 -*-
"""
ai.py — Intelligence artificielle du « Jeu du Gendarme et du Voleur ».

Historique : ce module existait dans le mode solo ; il est réintroduit pour
le mode « Auto-Play (IA vs IA) » du multijoueur. Le serveur calcule les coups
des DEUX camps avec ce module, puis diffuse l'état aux deux clients : aucun
client ne simule l'IA localement, donc aucune désynchronisation possible.

Trois niveaux de difficulté (noms malgaches, comme dans l'ancien mode solo) :

  * MORA (facile)      : coup aléatoire parmi les coups légaux ;
  * ANTONONY (moyen)   : heuristique — la police coupe les chemins du voleur,
                         le voleur fuit tout en avançant vers sa porte ;
  * SAROTRA (difficile): minimax + élagage alpha-bêta et approfondissement
                         itératif (limite de temps paramétrable).

Le module ne dépend que de board.py / game.py / locales.py (pas de pygame) :
il est utilisable aussi bien par le serveur que depuis la console.

Utilisation :

    from ai import choisir_coup
    frm, to = choisir_coup(game, POLICE, "antonony")   # None si bloqué
    frm, to = choisir_coup(game, POLICE, "sarotra", temps_max=0.3)
"""

import random
import time

from board import CENTER, GATES, NEIGHBORS
from game import POLICE, VOLEUR

# Identifiants des niveaux (clés de traduction "niveau_<id>" dans locales.py)
NIVEAUX = ("mora", "antonony", "sarotra")
NIVEAU_DEFAUT = "antonony"

# ---------------------------------------------------------------------------
# Distances sur le graphe : BFS toutes-paires précalculé à l'import.
# Le plateau n'a que 21 nœuds : l'évaluation devient une lecture de table.
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
_INFINI = 99


def dist(a, b):
    """Distance (nombre d'arêtes) entre deux nœuds du plateau."""
    return DISTANCES[a].get(b, _INFINI)


# ---------------------------------------------------------------------------
# Évaluation : score POSITIF = bon pour le VOLEUR, négatif = bon pour la
# POLICE. Utilisée par ANTONONY (1 coup d'anticipation) et SAROTRA (feuilles).
# ---------------------------------------------------------------------------
def _portes_restantes(g):
    return [p for p in GATES if p not in g.gates_visited]


def _objectif_voleur(g):
    """Prochaine étape du circuit : porte non visitée la plus proche, ou
    centre si toutes les portes ont été visitées (il doit rentrer)."""
    restantes = _portes_restantes(g)
    if not restantes:
        return CENTER
    return min(restantes, key=lambda p: dist(g.thief, p))


def evaluer(g):
    """Heuristique d'évaluation de l'état `g` (voir docstring du module)."""
    if g.winner == VOLEUR:
        return 1_000_000 - 10 * g.move_count   # gagner vite vaut mieux
    if g.winner == POLICE:
        return -1_000_000 + 10 * g.move_count

    score = 0
    score += 40 * len(g.gates_visited)                       # progression
    score -= 6 * dist(g.thief, _objectif_voleur(g))          # avancée
    score += 5 * min(dist(g.thief, c) for c in g.cops)       # fuite
    score += 6 * len(g.legal_moves(VOLEUR))                  # mobilité
    restantes = _portes_restantes(g)
    if restantes:
        garde = sum(min(dist(c, p) for c in g.cops) for p in restantes)
        score -= 2 * garde                                   # pression police
    return score


# ---------------------------------------------------------------------------
# Niveau ANTONONY : heuristique à un coup.
# ---------------------------------------------------------------------------
def _score_heuristique(g, role, frm, to):
    """Qualité du coup (frm -> to) pour `role`."""
    cible = _objectif_voleur(g)
    if role == POLICE:
        return -(2 * dist(to, g.thief) + dist(to, cible))
    fuite = min(dist(to, c) for c in g.cops)
    s = 2 * fuite - 3 * dist(to, cible)
    if to == cible:
        s += 12                      # visiter la porte / rentrer à la fin
    return s


def coup_heuristique(g, role, coups):
    """Meilleur coup selon l'heuristique, avec un léger bruit pour varier."""
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
    """Interne : limite de temps de recherche atteinte."""


def _ordre_coups(g, role, coups):
    """Trie les coups du meilleur au moins bon pour accélérer l'élagage."""
    return sorted(coups,
                  key=lambda c: _score_heuristique(g, role, c[0], c[1]),
                  reverse=True)


def _alphabeta(g, profondeur, alpha, beta, echuance):
    """Le VOLEUR maximise evaluer(), la POLICE la minimise."""
    if time.perf_counter() > echuance:
        raise _TempsEcoule
    if g.winner is not None or profondeur == 0:
        return evaluer(g)

    role = g.turn
    coups = g.legal_moves(role)
    if not coups:
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
                break
        return meilleur

    pire = float("inf")                # --- nœud MIN (police) ---
    for frm, to in _ordre_coups(g, role, coups):
        g2 = g.clone()
        g2.move(POLICE, frm, to)
        pire = min(pire,
                   _alphabeta(g2, profondeur - 1, alpha, beta, echuance))
        beta = min(beta, pire)
        if beta <= alpha:
            break
    return pire


def coup_recherche(g, role, coups, profondeur_max=6, temps_max=1.0):
    """Minimax / alpha-bêta avec approfondissement itératif : on garde le
    meilleur coup COMPLET calculé avant l'échéance."""
    coups = list(coups)
    coups = _ordre_coups(g, role, coups)
    meilleur = coups[0]                # repli : meilleur coup heuristique
    for profondeur in range(2, profondeur_max + 1):
        echuance = time.perf_counter() + temps_max
        alpha, beta = -float("inf"), float("inf")
        meilleur_valeur = None
        meilleur_coup_prof = meilleur
        try:
            for frm, to in coups:
                g2 = g.clone()
                g2.move(role, frm, to)
                v = _alphabeta(g2, profondeur - 1, alpha, beta, echuance)
                if role == VOLEUR:     # le joueur rechercheur maximise
                    if meilleur_valeur is None or v > meilleur_valeur:
                        meilleur_valeur, meilleur_coup_prof = v, (frm, to)
                    alpha = max(alpha, v)
                else:                  # ... ou minimise
                    if meilleur_valeur is None or v < meilleur_valeur:
                        meilleur_valeur, meilleur_coup_prof = v, (frm, to)
                    beta = min(beta, v)
        except _TempsEcoule:
            break                      # on garde la profondeur précédente
        meilleur = meilleur_coup_prof
        coups.remove(meilleur)
        coups.insert(0, meilleur)
    return meilleur


# ---------------------------------------------------------------------------
# Point d'entrée unique
# ---------------------------------------------------------------------------
def choisir_coup(game, role, niveau=NIVEAU_DEFAUT, temps_max=1.0):
    """Choisit le coup de l'IA pour `role` au niveau `niveau`.

    `temps_max` ne concerne que SAROTRA (budget par profondeur). Renvoie un
    couple (frm, to), ou None si le camp n'a aucun coup légal."""
    if role not in (VOLEUR, POLICE):
        raise ValueError(f"rôle inconnu : {role}")
    if niveau not in NIVEAUX:
        niveau = NIVEAU_DEFAUT

    coups = game.legal_moves(role)
    if not coups:
        return None

    if niveau == "mora":
        return random.choice(coups)
    if niveau == "antonony":
        return coup_heuristique(game, role, coups)
    return coup_recherche(game, role, coups, temps_max=temps_max)


if __name__ == "__main__":
    # Auto-test console : légalité des coups pour chaque niveau/rôle, puis
    # deux parties complètes IA contre IA.
    from game import Game

    for niveau in NIVEAUX:
        for role in (VOLEUR, POLICE):
            g = Game()
            if role == POLICE:
                g.move(VOLEUR, "C", "te")
            coup = choisir_coup(g, role, niveau, temps_max=0.05)
            assert coup is not None and coup in g.legal_moves(role), \
                (niveau, role, coup)
            print(f"OK  niveau {niveau:>8} / rôle {role:<6} -> {coup[0]} -> {coup[1]}")

    # clone() doit être indépendant de la partie d'origine
    g = Game()
    copie = g.clone()
    copie.move(VOLEUR, "C", "te")
    assert g.thief == "C" and copie.thief == "te"
    print("OK  clone() indépendant")

    def partie(niveau_voleur, niveau_police, plafond=400):
        g = Game()
        while g.winner is None and g.move_count < plafond:
            niveau = niveau_voleur if g.turn == VOLEUR else niveau_police
            coup = choisir_coup(g, g.turn, niveau, temps_max=0.05)
            if coup is None:
                break
            g.move(g.turn, *coup)
        return g

    for nv, np, attendu in (("sarotra", "mora", VOLEUR),
                            ("mora", "sarotra", POLICE)):
        t0 = time.perf_counter()
        g = partie(nv, np)
        print(f"{nv} (voleur) vs {np} (police) : vainqueur={g.winner} "
              f"en {g.move_count} coups ({time.perf_counter() - t0:.1f}s)")
        assert g.winner == attendu
    print("Auto-test IA : OK")
