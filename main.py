# -*- coding: utf-8 -*-
"""
main.py — Jeu du Gendarme et du Voleur (point d'entrée principal).

Au lancement, un MENU permet de choisir :

  * la LANGUE de l'interface : Français / Malagasy ;
  * le MODE de jeu :
        - SOLO (hors ligne) contre l'IA — 3 niveaux de difficulté :
          mora (facile), antonony (moyen), sarotra (difficile) ;
        - 2 JOUEURS sur le même écran (mode local d'origine) ;
        - MULTIJOUEUR en ligne (connexion à server.py) ;
  * en solo : le RÔLE du joueur humain (Voleur ou Police) — l'IA prend
    automatiquement le contrôle du rôle opposé.

Pendant une partie (souris) : cliquer un de ses pions puis une
destination verte. Touches : Échap = retour au menu, R = nouvelle partie.
"""

import sys

import pygame

import ai
import client
from game import POLICE, VOLEUR, Game, IllegalMove
from locales import set_langue, texte
from menu import Menu
from render import COL_COP, COL_THIEF, Layout, draw_scene, load_font

WIDTH, HEIGHT = 880, 920
MIN_W, MIN_H = 480, 540   # taille minimale de la fenêtre (plateau jouable)
FPS = 60
IA_DELAI_MS = 400         # délai d'affichage avant que l'IA joue


def ouvrir_fenetre():
    """Ouvre la fenêtre principale : ajustée à l'écran, redimensionnable."""
    pygame.init()
    info_ecran = pygame.display.Info()
    w0 = max(MIN_W, min(WIDTH, info_ecran.current_w - 80))
    h0 = max(MIN_H, min(HEIGHT, info_ecran.current_h - 120))
    return pygame.display.set_mode((w0, h0), pygame.RESIZABLE)


# ---------------------------------------------------------------------------
# Boucle de partie locale (2 joueurs OU solo contre l'IA)
# ---------------------------------------------------------------------------
def boucle_jeu(screen, langue, role_humain=None, niveau=None):
    """Boucle d'une partie jouée dans la fenêtre principale.

    * role_humain = None  -> 2 joueurs humains, même écran ;
    * role_humain = rôle  -> solo : le humain joue `role_humain`, l'IA
      (niveau `niveau`) joue le rôle opposé.

    Retourne quand le joueur appuie sur Échap (retour au menu)."""
    set_langue(langue)
    clock = pygame.time.Clock()
    layout = Layout(*screen.get_size())

    role_ia = None
    if role_humain is not None:
        role_ia = POLICE if role_humain == VOLEUR else VOLEUR
        pygame.display.set_caption(texte("titre_solo", langue))
    else:
        pygame.display.set_caption(texte("titre_local", langue))

    game = Game()
    selected, targets = None, []
    ia_passe = False        # True = l'IA n'a plus aucun coup légal (figé)
    if role_humain is not None:
        info = texte("solo_bandeau", langue,
                     role=texte("nom_voleur" if role_humain == VOLEUR
                                else "nom_police", langue),
                     niveau=texte(f"niveau_{niveau}", langue),
                     role_ia=texte("nom_police" if role_humain == VOLEUR
                                   else "nom_voleur", langue))
    else:
        info = texte("info_depart", langue)

    running = True
    while running:
        # ---------------- événements ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                w, h = max(MIN_W, event.w), max(MIN_H, event.h)
                if (event.w, event.h) != (w, h):
                    screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                layout = Layout(w, h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False          # retour au menu
                elif event.key == pygame.K_r:
                    game = Game()
                    selected, targets = None, []
                    ia_passe = False
                    info = texte("info_nouvelle", langue)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.winner is not None:
                    info = texte("info_termine", langue)
                    continue
                if role_ia is not None and game.turn == role_ia:
                    info = texte("ia_reflechit", langue,
                                 niveau=texte(f"niveau_{niveau}", langue))
                    continue
                node = layout.pick_node(event.pos)
                if node is None:
                    continue
                if selected and node in targets:
                    # --- coup validé ---
                    try:
                        qui = texte("qui_voleur" if game.turn == VOLEUR
                                    else "qui_police", langue)
                        game.move(game.turn, selected, node)
                        info = texte("info_coup", langue, frm=selected,
                                     to=node, qui=qui)
                        selected, targets = None, []
                    except IllegalMove as e:
                        info = texte("info_refuse", langue, erreur=e)
                elif node in game.pieces_of(game.turn):
                    # --- sélection d'un de ses pions ---
                    selected = node
                    targets = game.legal_targets(game.turn, node)
                    qui = texte("qui_voleur" if game.turn == VOLEUR
                                else "qui_police", langue)
                    info = texte("info_selection", langue, qui=qui, node=node)
                else:
                    selected, targets = None, []
                    info = texte("info_clic_faux", langue)

        # ---------------- tour de l'IA ----------------
        if (role_ia is not None and game.winner is None
                and game.turn == role_ia and not ia_passe):
            # une frame « L'IA réfléchit... » pour que le joueur voie
            # l'état, puis le calcul (bloquant mais déjà annoncé)
            _dessiner_frame(screen, layout, game, langue, selected, targets,
                            texte("ia_reflechit", langue,
                                  niveau=texte(f"niveau_{niveau}", langue)),
                            role_humain, niveau)
            pygame.display.flip()
            pygame.time.wait(IA_DELAI_MS)
            coup = ai.choisir_coup(game, role_ia, niveau)
            if coup is not None:
                game.move(role_ia, *coup)
                info = texte("ia_coup", langue,
                             niveau=texte(f"niveau_{niveau}", langue),
                             frm=coup[0], to=coup[1])
            else:
                # cas pathologique : plus AUCUN coup légal pour l'IA — on
                # fige la partie plutôt que de boucler indéfiniment
                ia_passe = True
                info = texte("ia_bloquee", langue)
            selected, targets = None, []

        # ---------------- rendu ----------------
        _dessiner_frame(screen, layout, game, langue, selected, targets,
                        info, role_humain, niveau)
        pygame.display.flip()
        clock.tick(FPS)


def _dessiner_frame(screen, layout, game, langue, selected, targets, info,
                    role_humain, niveau):
    """Frame complète : plateau + bandeau du haut (titre / qui est qui)."""
    draw_scene(screen, layout, game, selected, targets, info, langue)
    if role_humain is not None:
        couleur = COL_THIEF if role_humain == VOLEUR else COL_COP
        bandeau = load_font(16, bold=True).render(
            texte("solo_bandeau", langue,
                  role=texte("nom_voleur" if role_humain == VOLEUR
                             else "nom_police", langue),
                  niveau=texte(f"niveau_{niveau}", langue),
                  role_ia=texte("nom_police" if role_humain == VOLEUR
                                else "nom_voleur", langue)),
            True, couleur)
        screen.blit(bandeau, (12, 8))
    else:
        titre = load_font(16, bold=True).render(
            texte("titre_local", langue), True, (220, 220, 228))
        screen.blit(titre, (12, 8))


# ---------------------------------------------------------------------------
# Écran d'erreur de connexion (mode en ligne)
# ---------------------------------------------------------------------------
def ecran_erreur_connexion(screen, langue, hote, port):
    """Affiche l'échec de connexion ; clic ou touche -> retour au menu."""
    from render import COL_BG, COL_TEXT_DIM
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        w, h = screen.get_size()
        screen.fill(COL_BG)
        # message découpé en lignes (il est long)
        message = texte("erreur_connexion", langue, hote=hote, port=port)
        lignes = _envelopper(message, 46)
        y = h // 2 - len(lignes) * 18
        for ligne in lignes:
            img = load_font(18, bold=True).render(ligne, True, COL_THIEF)
            screen.blit(img, img.get_rect(center=(w // 2, y)))
            y += 40
        img2 = load_font(14).render("— " + texte("btn_retour", langue) + " —",
                                    True, COL_TEXT_DIM)
        screen.blit(img2, img2.get_rect(center=(w // 2, y + 14)))
        pygame.display.flip()
        clock.tick(30)


def _envelopper(message, largeur):
    """Découpe `message` en lignes d'au plus `largeur` caractères."""
    lignes, courante = [], ""
    for mot in message.split():
        essai = (courante + " " + mot).strip()
        if len(essai) > largeur and courante:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes


# ---------------------------------------------------------------------------
# Point d'entrée : menu -> partie
# ---------------------------------------------------------------------------
def main():
    screen = ouvrir_fenetre()
    langue = "fr"

    while True:
        config = Menu(langue).run(screen)
        if config is None:                       # quitter
            break
        langue = config["langue"]
        set_langue(langue)

        if config["mode"] == "local":
            boucle_jeu(screen, langue)
        elif config["mode"] == "solo":
            boucle_jeu(screen, langue, role_humain=config["role"],
                       niveau=config["niveau"])
        elif config["mode"] == "ligne":
            ok = client.lancer_client(config["host"], config["port"],
                                      config["nom"], config["role"], langue,
                                      screen=screen)
            if not ok:
                ecran_erreur_connexion(screen, langue,
                                        config["host"], config["port"])

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
