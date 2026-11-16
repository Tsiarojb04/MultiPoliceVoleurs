# -*- coding: utf-8 -*-
"""
game.py — Règles du « Jeu du Gendarme et du Voleur » (tour par tour).

Rôles :
  * JOUEUR 1 : le VOLEUR (un seul pion rouge, départ exactement au centre
    du petit cercle central) ;
  * JOUEUR 2 : la POLICE (trois pions bleus : un sur le haut du petit
    cercle central (cx, cy-r), deux aux sommets des anses internes
    gauche et droite — sur les axes, contre la bordure du grand cercle).

Règles de déplacement :
  * à son tour, un joueur déplace UN de ses pions ;
  * le déplacement se fait d'une seule intersection vers une intersection
    ADJACENTE, en suivant une ligne (arête) du plateau ;
  * une intersection ne peut contenir qu'un seul pion : on ne peut pas
    se déplacer sur un nœud occupé ;
  * la police n'a pas le droit d'entrer au centre « C » (la tanière du
    voleur) — sinon elle pourrait y camper et bloquer la victoire à jamais.

Conditions de victoire :
  * la POLICE gagne si le voleur est totalement bloqué (plus aucun
    mouvement légal possible au début de son tour) ;
  * le VOLEUR gagne s'il sort du centre, parcourt le circuit extérieur
    (visiter les 4 « portes » N, E, S, W) puis revient au centre.
    Rentrer au centre avec un tour incommet remet le circuit à zéro.
"""

from board import CENTER, GATES, NEIGHBORS, NODES

from locales import texte

VOLEUR = "voleur"
POLICE = "police"

# Voisins pré-triés (stable pour l'IA et l'affichage, évite un sorted()
# à chaque appel de legal_targets)
_VOISINS_TRIES = {n: sorted(v) for n, v in NEIGHBORS.items()}

# Positions de départ (modifiables ici) — conformes au dessin de référence :
# voleur strictement au centre (cx, cy) ; un policier sur le HAUT du petit
# cercle central (cx, cy-r) ; deux policiers aux sommets des anses interne
# gauche et droite (cx∓(R-ANSE_R), cy) — sur les axes, contre la bordure.
INITIAL_THIEF = "C"
INITIAL_COPS = ("tn", "aW", "aE")


class IllegalMove(Exception):
    """Le coup demandé ne respecte pas les règles du jeu."""


class Game:
    """État complet d'une partie + règles. Aucune dépendance à pygame :
    cette classe est partagée par le jeu local (main.py), le client réseau
    (client.py) et le serveur (server.py)."""

    def __init__(self):
        self.thief = INITIAL_THIEF
        self.cops = list(INITIAL_COPS)
        self.turn = VOLEUR          # le voleur commence
        self.winner = None
        self.gates_visited = set()  # portes visitées depuis la sortie du centre
        self.move_count = 0
        self.history = []           # liste des coups joués
        self._check_police_win()    # voleur bloqué dès le départ ?

    # ------------------------------------------------------------------ #
    # Représentation sérialisable (pour le réseau / l'affichage)
    # ------------------------------------------------------------------ #
    def to_dict(self):
        return {
            "thief": self.thief,
            "cops": list(self.cops),
            "turn": self.turn,
            "winner": self.winner,
            "gates_visited": sorted(self.gates_visited),
            "move_count": self.move_count,
        }

    @classmethod
    def from_dict(cls, data):
        g = cls.__new__(cls)
        g.thief = data["thief"]
        g.cops = list(data["cops"])
        g.turn = data["turn"]
        g.winner = data["winner"]
        g.gates_visited = set(data.get("gates_visited", []))
        g.move_count = data.get("move_count", 0)
        g.history = []
        return g

    # ------------------------------------------------------------------ #
    # Aides
    # ------------------------------------------------------------------ #
    def occupied(self, node):
        """Un pion (voleur ou policier) occupe-t-il ce nœud ?"""
        return node == self.thief or node in self.cops

    def pieces_of(self, player):
        """Nœuds occupés par les pions du joueur demandé."""
        if player == VOLEUR:
            return [self.thief]
        return list(self.cops)

    def legal_targets(self, player, frm):
        """Destinations légales pour le pion situé sur `frm`."""
        if self.winner is not None:
            return []
        if player == VOLEUR:
            if frm != self.thief:
                raise IllegalMove(texte("err_pas_voleur"))
        elif frm not in self.cops:
            raise IllegalMove(texte("err_pas_police"))
        targets = []
        for to in _VOISINS_TRIES[frm]:
            if self.occupied(to):
                continue                    # nœud occupé -> interdit
            if player == POLICE and to == CENTER:
                continue                    # la police n'entre pas au centre
            targets.append(to)
        return targets

    def legal_moves(self, player):
        """Tous les coups légaux du joueur : liste de (frm, to)."""
        moves = []
        for frm in self.pieces_of(player):
            moves.extend((frm, to) for to in self.legal_targets(player, frm))
        return moves

    def has_legal_move(self, player):
        for frm in self.pieces_of(player):
            if self.legal_targets(player, frm):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Jouer un coup
    # ------------------------------------------------------------------ #
    def move(self, player, frm, to):
        """Applique le coup `frm -> to` pour `player` après validation.

        Lève IllegalMove si le coup est invalide ; renvoie True si le
        coup a bien été joué."""
        if self.winner is not None:
            raise IllegalMove(texte("err_partie_finie"))
        if player != self.turn:
            raise IllegalMove(texte("err_pas_tour", qui=player))
        if to not in NODES:
            raise IllegalMove(texte("err_noeud", noeud=to))
        if to not in NEIGHBORS[frm]:
            raise IllegalMove(texte("err_adjacents", frm=frm, to=to))
        targets = self.legal_targets(player, frm)
        if to not in targets:
            if self.occupied(to):
                raise IllegalMove(texte("err_occupe", noeud=to))
            raise IllegalMove(texte("err_centre"))

        # --- application ---
        if player == VOLEUR:
            self.thief = to
        else:
            self.cops[self.cops.index(frm)] = to
        self.move_count += 1
        self.history.append((player, frm, to))
        self._after_move(player)
        return True

    def _after_move(self, player):
        """Conditions de victoire + passage au tour suivant."""
        if player == VOLEUR:
            if self.thief == CENTER:
                if set(GATES) <= self.gates_visited:
                    self.winner = VOLEUR   # tour complet + retour au centre
                else:
                    self.gates_visited.clear()  # rentrée prématurée : reset
            elif self.thief in GATES:
                self.gates_visited.add(self.thief)

        # joueur suivant
        self.turn = POLICE if player == VOLEUR else VOLEUR

        if self.winner is not None:
            return
        self._check_police_win()
        # Cas limite : si la police ne peut plus bouger du tout, on repasse
        # la main au voleur (impossible en pratique sur ce plateau).
        if self.turn == POLICE and not self.has_legal_move(POLICE):
            self.turn = VOLEUR

    def _check_police_win(self):
        """La police gagne si le voleur n'a plus AUCUN mouvement possible."""
        if self.winner is None and self.turn == VOLEUR \
                and not self.has_legal_move(VOLEUR):
            self.winner = POLICE

    # ------------------------------------------------------------------ #
    # Copie légère (recherche de l'IA : minimax / alpha-bêta)
    # ------------------------------------------------------------------ #
    def clone(self):
        """Copie indépendante de l'état (sans l'historique des coups).

        Utilisée par ai.py pour explorer les coups possibles sans
        modifier la partie en cours."""
        g = Game.__new__(Game)
        g.thief = self.thief
        g.cops = list(self.cops)
        g.turn = self.turn
        g.winner = self.winner
        g.gates_visited = set(self.gates_visited)
        g.move_count = self.move_count
        g.history = []
        return g

    # ------------------------------------------------------------------ #
    def progress_text(self, langue=None):
        """Texte de progression du circuit (barre d'état, ligne 2)."""
        if self.winner == VOLEUR:
            return texte("prog_boucle", langue)
        if self.winner == POLICE:
            return texte("prog_bloque", langue)
        missing = [g for g in GATES if g not in self.gates_visited]
        if self.thief == CENTER:
            return texte("prog_centre", langue)
        if missing:
            return texte("prog_portes", langue,
                         visitees=", ".join(sorted(self.gates_visited)) or "-",
                         manque=", ".join(missing))
        return texte("prog_fini", langue)

    def status_text(self, langue=None):
        """Texte d'état complet affiché dans la barre du bas (partagé par les UI)."""
        if self.winner is not None:
            return (texte("victoire_voleur", langue) if self.winner == VOLEUR
                    else texte("victoire_police", langue)) + " " + self.progress_text(langue)
        who = "VOLEUR" if self.turn == VOLEUR else "POLICE"
        return f"[Tour {self.move_count + 1}] Au tour du joueur {who}. {self.progress_text(langue)}"


if __name__ == "__main__":
    # Auto-test des règles en console (coups recalculés pour le plateau à
    # 4 anses : portes N/E/S/W degré 3, sommets d'anses degré 2, raccords
    # degré 3, petit cercle degré 4)
    # --- Scénario 1 : le voleur boucle le circuit et rentre -> il gagne ---
    g = Game()
    print("Départ :", g.to_dict())
    scenario_voleur = [
        (VOLEUR, "C", "te"),   (POLICE, "aE", "eN"),   # libère l'anse est
        (VOLEUR, "te", "aE"),  (POLICE, "tn", "tw"),   # libère le retour
        (VOLEUR, "aE", "E"),   (POLICE, "tw", "ts"),   # porte E
        (VOLEUR, "E", "eS"),   (POLICE, "ts", "tw"),
        (VOLEUR, "eS", "sE"),  (POLICE, "tw", "ts"),
        (VOLEUR, "sE", "S"),   (POLICE, "ts", "tw"),   # porte S
        (VOLEUR, "S", "sW"),   (POLICE, "tw", "ts"),
        (VOLEUR, "sW", "wS"),  (POLICE, "ts", "tw"),
        (VOLEUR, "wS", "W"),   (POLICE, "tw", "ts"),   # porte W
        (VOLEUR, "W", "wN"),   (POLICE, "ts", "tw"),
        (VOLEUR, "wN", "nW"),  (POLICE, "tw", "ts"),
        (VOLEUR, "nW", "N"),   (POLICE, "ts", "tw"),   # porte N
        (VOLEUR, "N", "aN"),   (POLICE, "tw", "ts"),
        (VOLEUR, "aN", "tn"),  (POLICE, "ts", "tw"),
        (VOLEUR, "tn", "C"),   # retour au centre : circuit complet !
    ]
    for player, frm, to in scenario_voleur:
        g.move(player, frm, to)
    assert g.winner == VOLEUR, "le voleur devrait avoir gagné"
    print("Test 1 OK — victoire du voleur :", g.status_text())

    # --- Scénario 2 : le voleur est coincé sur une porte -> police gagne
    #     (la police verrouille les 3 voisins de la porte E)
    g2 = Game()
    scenario_police = [
        (VOLEUR, "C", "ts"),   (POLICE, "aE", "eN"),
        (VOLEUR, "ts", "tw"),  (POLICE, "aW", "wS"),
        (VOLEUR, "tw", "ts"),  (POLICE, "wS", "sW"),
        (VOLEUR, "ts", "tw"),  (POLICE, "sW", "S"),
        (VOLEUR, "tw", "ts"),  (POLICE, "S", "sE"),
        (VOLEUR, "ts", "tw"),  (POLICE, "sE", "eS"),
        (VOLEUR, "tw", "ts"),  (POLICE, "tn", "tw"),   # rattrape le sud
        (VOLEUR, "ts", "te"),  (POLICE, "tw", "ts"),
        (VOLEUR, "te", "aE"),  (POLICE, "ts", "te"),   # dernière sortie libre
        (VOLEUR, "aE", "E"),   (POLICE, "te", "aE"),  # verrouillage total !
    ]
    for player, frm, to in scenario_police:
        g2.move(player, frm, to)
    # le voleur est sur E : voisins aE, eN et eS, tous occupés par la police
    assert g2.winner == POLICE, "la police devrait avoir gagné"
    print("Test 2 OK — victoire de la police :", g2.status_text())

    # --- Scénario 3 : rentrer au centre trop tôt remet le circuit à zéro ---
    g3 = Game()
    for player, frm, to in [(VOLEUR, "C", "te"), (POLICE, "aE", "eN"),
                            (VOLEUR, "te", "aE"), (POLICE, "eN", "nE"),
                            (VOLEUR, "aE", "E"), (POLICE, "nE", "eN"),
                            (VOLEUR, "E", "aE"), (POLICE, "eN", "nE"),
                            (VOLEUR, "aE", "te"), (POLICE, "nE", "eN"),
                            (VOLEUR, "te", "C")]:
        g3.move(player, frm, to)
    assert g3.gates_visited == set() and g3.winner is None
    print("Test 3 OK — retour prématuré au centre : circuit remis à zéro.")

    # --- Scénario 4 : coups illégaux refusés ---
    g4 = Game()
    for mauvais, msg in [
        ((POLICE, "C", "te"), "la police joue hors tour"),
        ((VOLEUR, "C", "tn"), "destination occupée"),
        ((VOLEUR, "C", "N"), "nœuds non adjacents"),
        ((VOLEUR, "te", "E"), "l'axe est coupé par le sommet d'anse"),
        ((POLICE, "tn", "C"), "la police n'entre pas au centre"),
        ((VOLEUR, "C", "aN"), "nœuds non adjacents (sommet d'anse)"),
    ]:
        try:
            g4.move(*mauvais)
            raise SystemExit(f"ECHEC : {msg} aurait dû être refusé")
        except IllegalMove:
            print(f"Test 4 OK — refus correct : {msg}")
