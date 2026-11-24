# -*- coding: utf-8 -*-
"""
menu.py — Écran de connexion du jeu (multijoueur en ligne uniquement).

Deux actions seulement :

  * « Héberger une partie » : le joueur 1 lance le serveur depuis le jeu ;
    son adresse IP s'affiche ensuite pour être partagée avec l'adversaire ;
  * « Rejoindre une partie » : les serveurs présents sur le réseau local
    sont détectés automatiquement et affichés sous forme de boutons. En
    secours, un champ permet de saisir l'adresse IP de l'hôte.

Aucun choix de rôle ou de port : les rôles sont attribués automatiquement
et le port par défaut est utilisé partout. Touche `L` : basculer la langue
des textes (français / malgache). Le mode « Auto-Play (IA vs IA) » se règle
ensuite dans la salle d'attente ou directement dans le HUD.

Menu.run(screen) renvoie :
    {"action": "host", "nom": "Alice" | None}
    {"action": "join", "host": "192.168.1.20", "port": 5555, "nom": "Bob"}
    None si l'utilisateur quitte.
"""

import threading

import pygame

from discovery import chercher_serveurs
from locales import langue_courante, set_langue, texte
from render import (COL_BG, COL_BOARD, COL_COP, COL_SEL, COL_STATUS_BG,
                    COL_TARGET, COL_TEXT, COL_TEXT_DIM, COL_THIEF, load_font)

_QUITTER = "menu:quitter"
PORT_PAR_DEFAUT = 5555
NB_SERVEURS_AFFICHES = 3


class Bouton:
    """Bouton rectangulaire avec état « survolé »."""

    def __init__(self, identifiant, libelle, rect, couleur=COL_TEXT,
                 taille_police=18):
        self.id = identifiant
        self.libelle = libelle
        self.rect = rect
        self.couleur = couleur
        self.taille_police = taille_police

    def contient(self, pos):
        return self.rect.collidepoint(pos)

    def dessiner(self, screen, souris):
        survole = self.rect.collidepoint(souris)
        pygame.draw.rect(screen, (46, 50, 66) if survole else COL_STATUS_BG,
                         self.rect, border_radius=10)
        pygame.draw.rect(screen, COL_SEL if survole else COL_BOARD,
                         self.rect, 2, border_radius=10)
        img = load_font(self.taille_police, bold=True).render(
            self.libelle, True, self.couleur)
        screen.blit(img, img.get_rect(center=self.rect.center))


class ChampTexte:
    """Champ de saisie d'une ligne (nom, adresse IP)."""

    def __init__(self, identifiant, libelle, valeur=""):
        self.id = identifiant
        self.libelle = libelle
        self.valeur = valeur
        self.actif = False
        self.rect = None

    def dessiner(self, screen, rect, souris):
        self.rect = rect
        survole = rect.collidepoint(souris)
        screen.blit(load_font(14).render(self.libelle, True, COL_TEXT_DIM),
                    (rect.x, rect.y - 22))
        pygame.draw.rect(screen, COL_STATUS_BG, rect, border_radius=8)
        pygame.draw.rect(screen, COL_SEL if (self.actif or survole) else COL_BOARD,
                         rect, 2, border_radius=8)
        valeur = self.valeur + ("_" if self.actif else "")
        img = load_font(17).render(valeur, True,
                                   COL_TEXT if self.actif else COL_TEXT_DIM)
        screen.blit(img, (rect.x + 12, rect.centery - img.get_height() // 2))

    def taper(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.valeur = self.valeur[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.valeur) < 40:
                self.valeur += event.unicode


class Menu:
    """Écran de connexion. Utilisation : Menu().run(screen)."""

    def __init__(self):
        self.ecran = "accueil"          # "accueil" | "rejoindre"
        self.erreur = ""
        self.serveurs = []
        self.recherche_en_cours = False
        self._verrou = threading.Lock()
        self.champs = {
            "nom": ChampTexte("nom", texte("champ_nom")),
            "host": ChampTexte("host", texte("champ_hote")),
        }
        self.champ_actif = None

    # ------------------------------------------------------------------ #
    # Boucle principale
    # ------------------------------------------------------------------ #
    def run(self, screen):
        pygame.display.set_caption(texte("titre_menu"))
        clock = pygame.time.Clock()
        while True:
            resultat = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    resultat = self._touche(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    resultat = self._clic(pygame.mouse.get_pos())
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
    # Détection automatique (thread)
    # ------------------------------------------------------------------ #
    def _lancer_recherche(self):
        with self._verrou:
            if self.recherche_en_cours:
                return
            self.recherche_en_cours = True
            self.serveurs = []

        def tache():
            trouvees = chercher_serveurs()
            with self._verrou:
                self.serveurs = trouvees
                self.recherche_en_cours = False

        threading.Thread(target=tache, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Clavier / souris
    # ------------------------------------------------------------------ #
    def _touche(self, event):
        if self.champ_actif:
            champ = self.champs[self.champ_actif]
            if event.key in (pygame.K_RETURN, pygame.K_TAB):
                if self.ecran == "rejoindre" and self.champ_actif == "host":
                    return self._connecter_manuel()
                self.champ_actif = None
            elif event.key == pygame.K_ESCAPE:
                self.champ_actif = None
            else:
                champ.taper(event)
            return None
        if event.key == pygame.K_ESCAPE:
            if self.ecran == "accueil":
                return _QUITTER
            self.ecran = "accueil"
            self.erreur = ""
            self.champ_actif = None
        elif event.key == pygame.K_l:
            # Français / Malagasy : les textes sont relus à chaque frame.
            set_langue("mg" if langue_courante() == "fr" else "fr")
            for ident, champ in self.champs.items():
                champ.libelle = texte("champ_nom" if ident == "nom"
                                      else "champ_hote")
        return None

    def _clic(self, pos):
        for bouton in self._construire():
            if bouton.contient(pos):
                return self._activer(bouton.id)
        if self.ecran == "rejoindre":
            for ident in ("host",):
                champ = self.champs[ident]
                if champ.rect and champ.rect.collidepoint(pos):
                    self.champ_actif = ident
                    return None
        elif self.ecran == "accueil":
            champ = self.champs["nom"]
            if champ.rect and champ.rect.collidepoint(pos):
                self.champ_actif = "nom"
                return None
        self.champ_actif = None
        return None

    def _config(self, host=None, port=PORT_PAR_DEFAUT):
        nom = self.champs["nom"].valeur.strip() or None
        if host is None:
            return {"action": "host", "nom": nom}
        return {"action": "join", "host": host, "port": port, "nom": nom}

    def _connecter_manuel(self):
        """Accepte une IP seule ou `IP:port` (port 5555 par défaut)."""
        host = self.champs["host"].valeur.strip()
        port = PORT_PAR_DEFAUT
        if ":" in host:
            host, _, texte_port = host.rpartition(":")
            try:
                port = int(texte_port)
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                self.erreur = texte("port_invalide")
                return None
        if not host:
            self.erreur = texte("champ_ip_vide")
            return None
        return self._config(host=host, port=port)

    def _activer(self, id_bouton):
        if id_bouton == "quitter":
            return _QUITTER
        if id_bouton == "heberger":
            return self._config()
        if id_bouton == "rejoindre":
            self.ecran = "rejoindre"
            self.erreur = ""
            self.champ_actif = None
            self._lancer_recherche()
            return None
        if id_bouton == "retour":
            self.ecran = "accueil"
            self.erreur = ""
            self.champ_actif = None
            return None
        if id_bouton == "rafraichir":
            self.erreur = ""
            self._lancer_recherche()
            return None
        if id_bouton == "connecter":
            return self._connecter_manuel()
        if id_bouton.startswith("serveur_"):
            i = int(id_bouton.split("_")[1])
            with self._verrou:
                if 0 <= i < len(self.serveurs):
                    srv = self.serveurs[i]
                    return self._config(host=srv["host"], port=srv["port"])
        return None

    # ------------------------------------------------------------------ #
    # Widgets (recalculés à chaque frame : fenêtre redimensionnable)
    # ------------------------------------------------------------------ #
    def _rang_centree(self, w, y, libelles_ids, largeur=280, hauteur=48,
                      ecart=14):
        n = len(libelles_ids)
        largeur = min(largeur, max(140, (w - 60 - (n - 1) * ecart) // max(n, 1)))
        total = n * largeur + (n - 1) * ecart
        x0 = (w - total) // 2
        return [Bouton(ident, libelle,
                       pygame.Rect(x0 + i * (largeur + ecart), y,
                                   largeur, hauteur), couleur=couleur)
                for i, (ident, libelle, couleur) in enumerate(libelles_ids)]

    def _construire(self):
        w, h = pygame.display.get_surface().get_size()
        boutons = []
        if self.ecran == "accueil":
            boutons.extend(self._rang_centree(w, h // 2 - 30, [
                ("heberger", texte("btn_heberger"), COL_TARGET)], largeur=340))
            boutons.extend(self._rang_centree(w, h // 2 + 34, [
                ("rejoindre", texte("btn_rejoindre"), COL_COP)], largeur=340))
            boutons.extend(self._rang_centree(w, h - 78, [
                ("quitter", texte("btn_quitter"), COL_THIEF)], largeur=200,
                hauteur=42))
        else:
            with self._verrou:
                serveurs = list(self.serveurs)
            geo = self._geometrie(h)
            for i, srv in enumerate(serveurs[:NB_SERVEURS_AFFICHES]):
                libelle = texte("serveur_trouve", hote=srv["host"])
                boutons.extend(self._rang_centree(
                    w, geo["serveurs"][i],
                    [(f"serveur_{i}", libelle, COL_TARGET)],
                    largeur=340, hauteur=42))
            boutons.extend(self._rang_centree(w, geo["rafraichir"], [
                ("rafraichir", texte("btn_rafraichir"), COL_TEXT)],
                largeur=200, hauteur=40))
            boutons.extend(self._rang_centree(w, geo["connecter"], [
                ("connecter", texte("btn_connecter"), COL_TARGET)],
                largeur=220, hauteur=44))
            boutons.extend(self._rang_centree(w, geo["retour"], [
                ("retour", texte("btn_retour"), COL_TEXT_DIM)],
                largeur=160, hauteur=38))
        return boutons

    # ------------------------------------------------------------------ #
    # Rendu
    # ------------------------------------------------------------------ #
    def _dessiner(self, screen, souris):
        w, h = screen.get_size()
        screen.fill(COL_BG)

        titre = load_font(27, bold=True).render(texte("titre"), True, COL_TEXT)
        screen.blit(titre, titre.get_rect(center=(w // 2, 52)))
        sous = load_font(16).render(texte("menu_sous_titre"), True, COL_TEXT_DIM)
        screen.blit(sous, sous.get_rect(center=(w // 2, 88)))

        boutons = self._construire()

        if self.ecran == "accueil":
            self.champs["nom"].libelle = texte("champ_nom")
            champ = self.champs["nom"]
            rect = pygame.Rect(w // 2 - 170, h // 2 - 108, 340, 42)
            champ.dessiner(screen, rect, souris)
            aide = load_font(14).render(texte("menu_aide"), True, COL_TEXT_DIM)
            screen.blit(aide, aide.get_rect(center=(w // 2, h // 2 + 108)))
        else:
            with self._verrou:
                en_cours = self.recherche_en_cours
                serveurs = list(self.serveurs)
            geo = self._geometrie(h)
            label = load_font(16, bold=True).render(
                texte("decouverte_titre"), True, COL_TEXT)
            screen.blit(label, label.get_rect(center=(w // 2, geo["label"])))

            if en_cours:
                txt = texte("decouverte_recherche")
            elif not serveurs:
                txt = texte("decouverte_aucune")
            else:
                txt = ""
            if txt:
                img = load_font(14).render(txt, True, COL_TEXT_DIM)
                screen.blit(img, img.get_rect(center=(w // 2, geo["status"])))

            champ = self.champs["host"]
            rect = pygame.Rect(w // 2 - 170, geo["champ"], 340, 42)
            champ.dessiner(screen, rect, souris)
            if not self.erreur:
                img = load_font(13).render(texte("champ_hote_aide"), True,
                                           COL_TEXT_DIM)
                screen.blit(img, img.get_rect(
                    center=(w // 2, geo["champ"] + 58)))

        if self.erreur:
            img = load_font(15, bold=True).render(self.erreur, True, COL_THIEF)
            y_erreur = (h - 40 if self.ecran == "accueil"
                        else self._geometrie(h)["champ"] + 58)
            screen.blit(img, img.get_rect(center=(w // 2, y_erreur)))

        for bouton in boutons:
            bouton.dessiner(screen, souris)

    @staticmethod
    def _geometrie(h):
        """Positions verticales de l'écran « Rejoindre » (écran minimal 540 px)."""
        top = max(96, h // 2 - 210)
        return {
            "label": top,
            "status": top + 24,
            "serveurs": [top + 46 + i * 46 for i in range(NB_SERVEURS_AFFICHES)],
            "rafraichir": top + 188,
            "champ": top + 266,
            "connecter": top + 340,
            "retour": top + 398,
        }
