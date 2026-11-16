# -*- coding: utf-8 -*-
"""
menu.py — Menu de démarrage graphique du « Jeu du Gendarme et du Voleur ».

Écran de sélection avant la partie ; permet de choisir :

  * la LANGUE de l'interface : Français / Malagasy (bouton en haut à
    droite, bascule instantanée de tout le menu) ;
  * le MODE de jeu :
        - Solo (hors ligne) : contre l'IA au niveau choisi (mora /
          antonony / sarotra) ;
        - 2 joueurs (même écran) : la partie locale d'origine ;
        - Multijoueur (en ligne) : connexion à server.py ;
  * en Solo : le RÔLE du joueur humain (Voleur / Police), l'IA prend
    le contrôle du rôle opposé ;
  * en ligne : adresse et port du serveur, nom, rôle souhaité.

Le menu est RESPONSIVE (fenêtre redimensionnable) : les boutons sont
recentrés à chaque frame en fonction de la taille actuelle.

Valeur de retour de Menu.run() (dict de configuration, ou None si
l'utilisateur quitte) :

    {"mode": "solo",  "role": "voleur", "niveau": "sarotra", "langue": "mg"}
    {"mode": "local", "langue": "fr"}
    {"mode": "ligne", "host": "192.168.1.20", "port": 5555,
     "nom": "Alice", "role": "voleur", "langue": "fr"}
"""

import pygame

from game import POLICE, VOLEUR
from locales import LANGUES, texte
from render import (COL_BG, COL_BOARD, COL_COP, COL_SEL, COL_STATUS_BG,
                    COL_TARGET, COL_TEXT, COL_TEXT_DIM, COL_THIEF, load_font)


# Sentinelle interne : l'utilisateur veut fermer le menu (Quitter / Échap
# sur l'écran principal). Distincte de None qui signifie « continuer ».
_QUITTER = "menu:quitter"


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------
class Bouton:
    """Bouton rectangulaire, avec états « survolé » et « sélectionné »."""

    def __init__(self, identifiant, libelle, rect, couleur=COL_TEXT,
                 selectionne=False, taille_police=18):
        self.id = identifiant
        self.libelle = libelle
        self.rect = rect
        self.couleur = couleur
        self.selectionne = selectionne
        self.taille_police = taille_police

    def contient(self, pos):
        return self.rect.collidepoint(pos)

    def dessiner(self, screen, souris):
        survole = self.rect.collidepoint(souris)
        fond = COL_STATUS_BG
        if self.selectionne:
            fond = (46, 50, 66)          # teinte de sélection
        pygame.draw.rect(screen, fond, self.rect, border_radius=10)
        bordure = COL_SEL if survole else (COL_BOARD if not self.selectionne
                                           else COL_TARGET)
        pygame.draw.rect(screen, bordure, self.rect, 2, border_radius=10)
        police = load_font(self.taille_police, bold=True)
        img = police.render(self.libelle, True, self.couleur)
        screen.blit(img, img.get_rect(center=self.rect.center))


class ChampTexte:
    """Champ de saisie d'une ligne (clavier) : adresse, port, nom."""

    def __init__(self, identifiant, libelle, valeur="", actif=False):
        self.id = identifiant
        self.libelle = libelle
        self.valeur = valeur
        self.actif = actif
        self.rect = None                # rempli au dessin (responsive)

    def dessiner(self, screen, rect, souris):
        self.rect = rect
        survole = rect.collidepoint(souris)
        libelle_img = load_font(14).render(self.libelle, True, COL_TEXT_DIM)
        screen.blit(libelle_img, (rect.x, rect.y - 22))
        pygame.draw.rect(screen, COL_STATUS_BG, rect, border_radius=8)
        pygame.draw.rect(screen, COL_SEL if (self.actif or survole) else COL_BOARD,
                         rect, 2, border_radius=8)
        valeur = self.valeur + ("_" if self.actif else "")
        img = load_font(17).render(valeur, True, COL_TEXT if self.actif
                                   else COL_TEXT_DIM)
        screen.blit(img, (rect.x + 12, rect.centery - img.get_height() // 2))

    def taper(self, event):
        """Traite un événement KEYDOWN destiné au champ actif."""
        if event.key == pygame.K_BACKSPACE:
            self.valeur = self.valeur[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.valeur) < 40:
                self.valeur += event.unicode


# ---------------------------------------------------------------------------
# Le menu
# ---------------------------------------------------------------------------
class Menu:
    """Écran de sélection. Utilisation : Menu(langue).run(screen)."""

    def __init__(self, langue="fr"):
        self.langue = langue if langue in LANGUES else "fr"
        self.ecran = "mode"             # "mode" -> "solo" / "ligne"
        self.role = VOLEUR              # rôle choisi (solo ET en ligne)
        self.niveau = "antonony"        # difficulté de l'IA (solo)
        self.role_ligne = "any"         # rôle souhaité en ligne
        self.erreur = ""                # message d'erreur inline (en ligne)
        self.champ_actif = None         # id du champ texte actif
        self.champs = {
            "host": ChampTexte("host", "", "127.0.0.1"),
            "port": ChampTexte("port", "", "5555"),
            "nom": ChampTexte("nom", "", ""),
        }

    # ------------------------------------------------------------------ #
    # Boucle principale du menu
    # ------------------------------------------------------------------ #
    def run(self, screen):
        pygame.display.set_caption(texte("titre_menu", self.langue))
        clock = pygame.time.Clock()
        while True:
            resultat = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    # la fenêtre est déjà redimensionnée par pygame ;
                    # le menu se recentre tout seul à la frame suivante
                    continue
                if event.type == pygame.KEYDOWN:
                    resultat = resultat or self._touche(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    resultat = resultat or self._clic(pygame.mouse.get_pos())
                if resultat is not None:
                    break
            if resultat is _QUITTER:
                return None
            if isinstance(resultat, dict):
                return resultat

            self._dessiner(screen, pygame.mouse.get_pos())
            pygame.display.flip()
            clock.tick(30)

    # ------------------------------------------------------------------ #
    # Gestion clavier
    # ------------------------------------------------------------------ #
    def _touche(self, event):
        """Traite une touche. Renvoie None (continuer), _QUITTER ou une
        configuration finale."""
        if self.ecran == "ligne" and self.champ_actif:
            champ = self.champs[self.champ_actif]
            if event.key in (pygame.K_RETURN, pygame.K_TAB):
                self._champ_suivant()
            elif event.key == pygame.K_ESCAPE:
                self.champ_actif = None
            else:
                champ.taper(event)
            return None
        if event.key == pygame.K_ESCAPE:
            if self.ecran == "mode":
                return _QUITTER          # quitter le jeu
            self.ecran = "mode"          # retour à l'écran des modes
            self.erreur = ""
        return None

    def _champ_suivant(self):
        ordre = ["host", "port", "nom"]
        if self.champ_actif in ordre:
            i = ordre.index(self.champ_actif)
            self.champ_actif = ordre[(i + 1) % len(ordre)]

    # ------------------------------------------------------------------ #
    # Gestion souris
    # ------------------------------------------------------------------ #
    def _clic(self, pos):
        """Traite un clic. Renvoie None (continuer), _QUITTER ou une
        configuration finale."""
        boutons = self._construire()
        for bouton in boutons:
            if bouton.contient(pos):
                return self._activer(bouton.id)
        # clic dans un champ texte ?
        if self.ecran == "ligne":
            for champ in self.champs.values():
                if champ.rect and champ.rect.collidepoint(pos):
                    self.champ_actif = champ.id
                    return None
            self.champ_actif = None
        return None

    def _activer(self, id_bouton):
        """Exécute l'action d'un bouton. Renvoie None (continuer),
        _QUITTER ou une configuration finale."""
        if id_bouton == "langue":            # bascule FR <-> MG
            self.langue = "mg" if self.langue == "fr" else "fr"
            return None
        if id_bouton == "quitter":
            return _QUITTER
        if id_bouton == "retour":
            self.ecran = "mode"
            self.erreur = ""
            return None

        if self.ecran == "mode":
            if id_bouton == "mode_solo":
                self.ecran = "solo"
            elif id_bouton == "mode_local":
                return {"mode": "local", "langue": self.langue}
            elif id_bouton == "mode_ligne":
                self.ecran = "ligne"
                self.erreur = ""
                self.champ_actif = "host"
            return None

        if self.ecran == "solo":
            if id_bouton == "role_voleur":
                self.role = VOLEUR
            elif id_bouton == "role_police":
                self.role = POLICE
            elif id_bouton.startswith("niveau_"):
                self.niveau = id_bouton[len("niveau_"):]
            elif id_bouton == "commencer":
                return {"mode": "solo", "role": self.role, "niveau": self.niveau,
                        "langue": self.langue}
            return None

        if self.ecran == "ligne":
            if id_bouton == "ligne_role_voleur":
                self.role_ligne = VOLEUR
            elif id_bouton == "ligne_role_police":
                self.role_ligne = POLICE
            elif id_bouton == "ligne_role_any":
                self.role_ligne = "any"
            elif id_bouton == "commencer":
                host = self.champs["host"].valeur.strip() or "127.0.0.1"
                try:
                    port = int(self.champs["port"].valeur.strip())
                    if not 1 <= port <= 65535:
                        raise ValueError("port hors bornes")
                except ValueError:
                    self.erreur = texte("port_invalide", self.langue)
                    return None
                nom = self.champs["nom"].valeur.strip() or None
                return {"mode": "ligne", "host": host, "port": port, "nom": nom,
                        "role": self.role_ligne, "langue": self.langue}
            return None
        return None

    # ------------------------------------------------------------------ #
    # Construction des widgets (RESPONSIVE : recalculée à chaque frame
    # à partir de la taille actuelle de la fenêtre)
    # ------------------------------------------------------------------ #
    def _rang_centree(self, w, y, n, libelles_ids, hauteur=46, ecart=14):
        """n boutons côte à côte, centrés horizontalement."""
        largeur = min(240, max(120, (w - 60 - (n - 1) * ecart) // n))
        total = n * largeur + (n - 1) * ecart
        x0 = (w - total) // 2
        boutons = []
        for i, (ident, libelle, couleur, selectionne) in enumerate(libelles_ids):
            rect = pygame.Rect(x0 + i * (largeur + ecart), y, largeur, hauteur)
            boutons.append(Bouton(ident, libelle, rect, couleur=couleur,
                                  selectionne=selectionne))
        return boutons

    def _construire(self):
        """Tous les widgets de l'écran courant."""
        w, h = pygame.display.get_surface().get_size()
        boutons = []
        # bouton de langue, en haut à droite (tous les écrans)
        langue_libelle = texte("btn_langue", self.langue)
        rect_langue = pygame.Rect(w - 230, 14, 216, 40)
        boutons.append(Bouton("langue", langue_libelle, rect_langue,
                              couleur=COL_TEXT_DIM))

        if self.ecran == "mode":
            boutons.extend(self._rang_centree(w, h // 3, 1, [
                ("mode_solo", texte("mode_solo", self.langue), COL_TEXT, False)]))
            boutons.extend(self._rang_centree(w, h // 3 + 66, 1, [
                ("mode_local", texte("mode_local", self.langue), COL_TEXT, False)]))
            boutons.extend(self._rang_centree(w, h // 3 + 132, 1, [
                ("mode_ligne", texte("mode_ligne", self.langue), COL_TEXT, False)]))
            boutons.extend(self._rang_centree(w, h - 90, 1, [
                ("quitter", texte("btn_quitter", self.langue),
                 COL_THIEF, False)]))

        elif self.ecran == "solo":
            y = h // 4
            boutons.extend(self._rang_centree(w, y, 2, [
                ("role_voleur", texte("role_voleur", self.langue),
                 COL_THIEF, self.role == VOLEUR),
                ("role_police", texte("role_police", self.langue),
                 COL_COP, self.role == POLICE)]))
            y2 = h // 4 + 96
            boutons.extend(self._rang_centree(w, y2, 3, [
                ("niveau_mora", texte("niveau_mora", self.langue),
                 COL_TEXT, self.niveau == "mora"),
                ("niveau_antonony", texte("niveau_antonony", self.langue),
                 COL_TEXT, self.niveau == "antonony"),
                ("niveau_sarotra", texte("niveau_sarotra", self.langue),
                 COL_TEXT, self.niveau == "sarotra")]))
            boutons.extend(self._rang_centree(w, h - 150, 2, [
                ("retour", texte("btn_retour", self.langue), COL_TEXT_DIM, False),
                ("commencer", texte("btn_commencer", self.langue),
                 COL_TARGET, False)]))

        elif self.ecran == "ligne":
            y = h // 4
            for ident, cle in (("host", "champ_hote"), ("port", "champ_port"),
                              ("nom", "champ_nom")):
                champ = self.champs[ident]
                champ.libelle = texte(cle, self.langue)
                rect = pygame.Rect(w // 2 - 190, y, 380, 42)
                champ.rect = rect
                y += 78
            y_role = y
            boutons.extend(self._rang_centree(w, y_role, 3, [
                ("ligne_role_voleur", texte("role_voleur", self.langue),
                 COL_THIEF, self.role_ligne == VOLEUR),
                ("ligne_role_police", texte("role_police", self.langue),
                 COL_COP, self.role_ligne == POLICE),
                ("ligne_role_any", texte("role_any", self.langue),
                 COL_TEXT, self.role_ligne == "any")]))
            boutons.extend(self._rang_centree(w, h - 150, 2, [
                ("retour", texte("btn_retour", self.langue), COL_TEXT_DIM, False),
                ("commencer", texte("btn_commencer", self.langue),
                 COL_TARGET, False)]))
        return boutons

    # ------------------------------------------------------------------ #
    # Rendu
    # ------------------------------------------------------------------ #
    def _dessiner(self, screen, souris):
        w, h = screen.get_size()
        screen.fill(COL_BG)

        # titre du jeu, centré en haut
        titre = load_font(26, bold=True).render(texte("titre", self.langue),
                                                True, COL_TEXT)
        screen.blit(titre, titre.get_rect(center=(w // 2, 52)))

        boutons = self._construire()

        if self.ecran == "mode":
            sous_titre = load_font(17).render(
                texte("menu_sous_titre", self.langue), True, COL_TEXT_DIM)
            screen.blit(sous_titre, sous_titre.get_rect(center=(w // 2, h // 3 - 36)))

        elif self.ecran == "solo":
            r = load_font(17).render(texte("menu_role", self.langue), True,
                                    COL_TEXT_DIM)
            screen.blit(r, r.get_rect(center=(w // 2, h // 4 - 30)))
            n = load_font(17).render(texte("menu_niveau", self.langue), True,
                                    COL_TEXT_DIM)
            screen.blit(n, n.get_rect(center=(w // 2, h // 4 + 66)))
            bandeau = load_font(14).render(
                texte("solo_bandeau", self.langue,
                      role=texte("nom_voleur" if self.role == VOLEUR else "nom_police",
                                 self.langue),
                      niveau=texte(f"niveau_{self.niveau}", self.langue),
                      role_ia=texte("nom_police" if self.role == VOLEUR else "nom_voleur",
                                    self.langue)),
                True, COL_TEXT)
            screen.blit(bandeau, bandeau.get_rect(center=(w // 2, h // 4 + 130)))

        elif self.ecran == "ligne":
            for champ in self.champs.values():
                champ.dessiner(screen, champ.rect, souris)
            if self.erreur:
                err = load_font(15, bold=True).render(self.erreur, True, COL_THIEF)
                screen.blit(err, err.get_rect(center=(w // 2, h // 4 + 3 * 78 + 44)))

        for bouton in boutons:
            bouton.dessiner(screen, souris)
