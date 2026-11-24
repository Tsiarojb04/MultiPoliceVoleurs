# -*- coding: utf-8 -*-
"""
locales.py — Textes affichés par le jeu (français uniquement).

Le projet ne propose plus que le multijoueur en ligne : le sélecteur de
langue, les textes du mode solo (IA) et ceux du mode local ont été retirés.
La fonction texte() garde son ancienne signature (un paramètre `langue`
ignoré) pour que game.py et render.py restent inchangés.
"""

import re

LANGUES = ("fr",)
LANGUE_DEFAUT = "fr"

TEXTES = {
    # --- titres / menu de connexion
    "titre": "Jeu du Gendarme et du Voleur",
    "titre_menu": "Multijoueur en ligne — Connexion",
    "titre_ligne": "Gendarme & Voleur — en ligne",
    "menu_sous_titre": "Jouez à deux, sur le même réseau ou à distance",
    "menu_aide": "Le serveur démarre automatiquement : partagez l'adresse affichée.",
    "btn_heberger": "Héberger une partie",
    "btn_rejoindre": "Rejoindre une partie",
    "btn_connecter": "Se connecter",
    "btn_rafraichir": "Rechercher à nouveau",
    "btn_quitter": "Quitter",
    "btn_retour": "Retour",
    "champ_nom": "Votre nom (facultatif)",
    "champ_hote": "Adresse IP du joueur qui héberge",
    "champ_hote_aide": "Exemple : 192.168.1.20  (ou 192.168.1.20:5556)",
    "champ_ip_vide": "Saisissez une adresse IP ou choisissez une partie détectée.",
    "port_invalide": "Port invalide (nombre entre 1 et 65535).",
    "decouverte_titre": "Parties détectées sur le réseau",
    "decouverte_recherche": "Recherche des parties en cours...",
    "decouverte_aucune": "Aucune partie détectée — saisissez l'adresse IP ci-dessous.",
    "serveur_trouve": "Rejoindre {hote}",
    # --- connexion / salle d'attente
    "net_erreur": "Connexion impossible à {hote}:{port} ({erreur})",
    "net_perdu": "Connexion perdue avec le serveur.",
    "net_deconnecte": "Serveur déconnecté.",
    "net_connexion": "Connexion au serveur...",
    "net_attente": "En attente d'un adversaire...",
    "net_partage": "Partagez cette adresse avec l'autre joueur :",
    "net_partage_aide": "Il lui suffit de cliquer sur « Rejoindre une partie ».",
    "net_adversaire": "Adversaire trouvé : {qui}",
    "net_termine": "Partie terminée — appuyez sur R pour proposer de rejouer.",
    "net_refuse": "Refusé : {msg}",
    "net_rematch": "Demande de rejouer envoyée...",
    "net_envoye": "Coup envoyé : {frm} → {to}...",
    "net_pas_tour": "Ce n'est pas votre tour !",
    "net_vous_voleur": "Vous êtes le VOLEUR",
    "net_vous_police": "Vous êtes la POLICE",
    "net_adversaire_court": "adversaire",
    "info_selection": "Pion sélectionné en {node} — cliquez une destination verte.",
    # --- barre d'état / règles (game.py, render.py)
    "tour_voleur": "Au tour du VOLEUR",
    "tour_police": "Au tour de la POLICE",
    "victoire_voleur": "LE VOLEUR GAGNE !",
    "victoire_police": "LA POLICE GAGNE !",
    "prog_boucle": "Il a bouclé le circuit et regagné le centre.",
    "prog_bloque": "Le voleur est totalement bloqué.",
    "prog_centre": "Le voleur est au centre (circuit à recommencer à zéro).",
    "prog_portes": "Portes visitées : {visitees} — manque {manque}.",
    "prog_fini": "Circuit complet ! Le voleur doit rentrer au centre pour gagner.",
    # --- erreurs du moteur de règles
    "err_partie_finie": "La partie est terminée.",
    "err_pas_tour": "Ce n'est pas le tour de {qui}.",
    "err_noeud": "Nœud inconnu : {noeud}.",
    "err_adjacents": "{frm} et {to} ne sont pas adjacents.",
    "err_occupe": "{noeud} est occupé.",
    "err_centre": "Coup interdit (la police n'entre pas au centre).",
    "err_pas_voleur": "Ce pion rouge n'est pas le voleur.",
    "err_pas_police": "Ce pion bleu n'est pas un policier.",
}

_langue_courante = LANGUE_DEFAUT


def set_langue(langue):
    """Conservé pour compatibilité : l'interface est désormais en français."""
    global _langue_courante
    if langue in LANGUES:
        _langue_courante = langue


def langue_courante():
    return _langue_courante


def texte(cle, langue=None, **params):
    """Renvoie le texte `cle` (le paramètre `langue` est ignoré)."""
    chaine = TEXTES.get(cle, cle)
    if params:
        try:
            return chaine.format(**params)
        except (KeyError, IndexError):
            return chaine
    return chaine


if __name__ == "__main__":
    assert all(TEXTES.values()), "traduction vide"
    motifs = {cle: set(re.findall(r"\{(\w+)\}", val))
              for cle, val in TEXTES.items()}
    print(f"Auto-test locales : OK — {len(TEXTES)} textes")
    print("  ", texte("titre"), "|", texte("btn_heberger"))
