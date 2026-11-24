# -*- coding: utf-8 -*-
"""
locales.py — Localisation du jeu : FRANÇAIS (fr) et MALAGASY (mg).

Toutes les chaînes affichées passent par texte() :

    texte("victoire_police", "mg")        -> "Nandresy ny Polisy !"
    texte("auto_bouton", etat="ON")       -> "Auto-Play (IA) : ON"

Les textes du moteur de règles (game.py) utilisent la langue courante,
fixée par les UI via set_langue (fr par défaut). Le serveur reste en français
pour ses messages de protocole. Aucune dépendance pygame : ce module est
importable partout, y compris par le serveur réseau.
"""

import re

LANGUES = ("fr", "mg")
LANGUE_DEFAUT = "fr"

# ---------------------------------------------------------------------------
# Table des textes : clé -> traduction. Les {paramètres} sont identiques
# dans les deux langues (vérifié par l'auto-test en fin de fichier).
# ---------------------------------------------------------------------------
TEXTES = {
    "fr": {
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
        "btn_langue": "Langue : Français",
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
        # --- auto-play / spectateur IA
        "auto_bouton": "Auto-Play (IA) : {etat}",
        "auto_on": "ON",
        "auto_off": "OFF",
        "niveau_bouton": "IA : {niveau}",
        "niveau_mora": "Facile (Mora)",
        "niveau_antonony": "Moyen (Antonony)",
        "niveau_sarotra": "Difficile (Sarotra)",
        "auto_bandeau": "Mode spectateur IA — l'IA joue des deux côtés",
        "auto_active": "Auto-Play activé : l'IA joue pour les deux joueurs.",
        "auto_desactive": "Auto-Play désactivé : vous reprenez le contrôle.",
        "auto_refuse": "Coup refusé : Auto-Play actif.",
        "auto_demande": "Demande de changement de mode envoyée...",
        "auto_niveau": "Niveau IA : {niveau}.",
        "btn_rejouer": "Rejouer (R)",
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
    },

    "mg": {
        # --- titres / menu de connexion
        "titre": "Kilalaon'ny Zandarma sy ny Mpangalatra",
        "titre_menu": "Lalao an-tranonkala — Fifandraisana",
        "titre_ligne": "Zandarma & Mpangalatra — an-tranonkala",
        "menu_sous_titre": "Milalao roa, amin'ny tambajotra iray na lavitra",
        "menu_aide": "Mandeha ho azy ny seva : zarao ny adrese hita.",
        "btn_heberger": "Mampiantrano lalao",
        "btn_rejoindre": "Miditra lalao",
        "btn_connecter": "Mifandray",
        "btn_rafraichir": "Mitady indray",
        "btn_quitter": "Hiala",
        "btn_retour": "Hiverina",
        "btn_langue": "Fiteny : Malagasy",
        "champ_nom": "Ny anaranao (tsy voatery)",
        "champ_hote": "Aderesin'ny seva",
        "champ_hote_aide": "Ohatra : 192.168.1.20  (na 192.168.1.20:5556)",
        "champ_ip_vide": "Ampidiro adrese IP na safidio ny lalao hita.",
        "port_invalide": "Port tsy mety (isa 1 hatramin'ny 65535).",
        "decouverte_titre": "Lalao hita eo amin'ny tambajotra",
        "decouverte_recherche": "Mitady seva...",
        "decouverte_aucune": "Tsy misy lalao hita — ampidiro ny adrese IP etsy ambany.",
        "serveur_trouve": "Miditra {hote}",
        # --- connexion / salle d'attente
        "net_erreur": "Tsy afaka mifandray amin'ny {hote}:{port} ({erreur})",
        "net_perdu": "Very ny fifandraisana amin'ny seva.",
        "net_deconnecte": "Tapaka ny fifandraisana amin'ny seva.",
        "net_connexion": "Mifandray amin'ny seva...",
        "net_attente": "Miandry mpifanandrina...",
        "net_partage": "Zarao amin'ny mpilalao hafa ity adrese ity :",
        "net_partage_aide": "Tsindrio fotsiny ny « Miditra lalao » izy.",
        "net_adversaire": "Hit ny mpifanandrina : {qui}",
        "net_termine": "Vita ny kilalao — tsindrio R hanoloana hiverina milalao.",
        "net_refuse": "Tsy nekena : {msg}",
        "net_rematch": "Nalefa ny fangatahana hiverina milalao...",
        "net_envoye": "Nalefa ny lalana : {frm} → {to}...",
        "net_pas_tour": "Tsy anjaranao izao !",
        "net_vous_voleur": "Ianao no MPANGALATRA",
        "net_vous_police": "Ianao no POLISY",
        "net_adversaire_court": "mpifanandrina",
        "info_selection": "Voafidy ny pion ao {node} — tsindrio ny toerana maitso.",
        # --- auto-play / spectateur IA
        "auto_bouton": "Lalao mandeha ho azy (IA) : {etat}",
        "auto_on": "ON",
        "auto_off": "OFF",
        "niveau_bouton": "IA : {niveau}",
        "niveau_mora": "Mora",
        "niveau_antonony": "Antonony",
        "niveau_sarotra": "Sarotra",
        "auto_bandeau": "Fomba fijery IA — ny IA no milalao amin'ny lafiny roa",
        "auto_active": "Navela ny Auto-Play : ny IA no milalao ho an'ny mpilalao roa.",
        "auto_desactive": "Najanona ny Auto-Play : ianao no mifehy indray.",
        "auto_refuse": "Tsy nekena ny lalana : mandeha ny Auto-Play.",
        "auto_demande": "Nalefa ny fangatahana fanovana fomba...",
        "auto_niveau": "Fahasarotan'ny IA : {niveau}.",
        "btn_rejouer": "Hiverina milalao (R)",
        # --- barre d'état / règles (game.py, render.py)
        "tour_voleur": "Anjaran'ny MPANGALATRA",
        "tour_police": "Anjaran'ny POLISY",
        "victoire_voleur": "Nandresy ny Mpangalatra !",
        "victoire_police": "Nandresy ny Polisy !",
        "prog_boucle": "Nitafo ny lalana rehetra izy ary niverina tao afovoany.",
        "prog_bloque": "Voasakana tanteraka ny mpangalatra.",
        "prog_centre": "Ao afovoany ny mpangalatra (averina amin'ny zero ny lalana).",
        "prog_portes": "Vavahady efa nodiavina : {visitees} — tsy mbola : {manque}.",
        "prog_fini": "Vita ny lalana ! Tsy maintsy miverina afovoany ny mpangalatra mba handresy.",
        # --- erreurs du moteur de règles
        "err_partie_finie": "Vita ny kilalao.",
        "err_pas_tour": "Tsy anjaran'ny {qui} izao.",
        "err_noeud": "Teboka tsy fantatra : {noeud}.",
        "err_adjacents": "{frm} sy {to} dia tsy mifanila.",
        "err_occupe": "Efa misy mpiasa ny {noeud}.",
        "err_centre": "Lalana tsy nekena (tsy miditra ao afovoany ny polisy).",
        "err_pas_voleur": "Ity pion mena ity dia tsy ny mpangalatra.",
        "err_pas_police": "Ity pion manga ity dia tsy polisy.",
    },
}

_langue_courante = LANGUE_DEFAUT


def set_langue(langue):
    """Fixe la langue courante (utilisée par game.py pour ses messages)."""
    global _langue_courante
    if langue in LANGUES:
        _langue_courante = langue


def langue_courante():
    return _langue_courante


def texte(cle, langue=None, **params):
    """Renvoie le texte `cle` dans `langue` (défaut : langue courante).

    Les paramètres nommés remplissent les accolades. Si une clé manque dans
    une langue, on retombe sur le français, puis sur la clé elle-même."""
    if langue is None:
        langue = _langue_courante
    dico = TEXTES.get(langue) or TEXTES[LANGUE_DEFAUT]
    chaine = dico.get(cle) or TEXTES[LANGUE_DEFAUT].get(cle, cle)
    if params:
        try:
            return chaine.format(**params)
        except (KeyError, IndexError):
            return chaine
    return chaine


def nom_niveau(niveau, langue=None):
    """Nom affichable d'un niveau d'IA ("mora"/"antonony"/"sarotra")."""
    return texte(f"niveau_{niveau}", langue)


if __name__ == "__main__":
    # Auto-test : mêmes clés, mêmes paramètres, aucune traduction vide.
    cles_fr, cles_mg = set(TEXTES["fr"]), set(TEXTES["mg"])
    assert cles_fr == cles_mg, (cles_fr ^ cles_mg)
    for cle in cles_fr:
        vf, vm = TEXTES["fr"][cle], TEXTES["mg"][cle]
        assert vf and vm, f"traduction vide : {cle}"
        params = lambda s: set(re.findall(r"\{(\w+)\}", s))
        assert params(vf) == params(vm), f"paramètres différents : {cle}"
    assert "Français" in TEXTES["fr"]["btn_langue"]
    assert "Malagasy" in TEXTES["mg"]["btn_langue"]
    print(f"Auto-test locales : OK — {len(cles_fr)} clés x {len(LANGUES)} langues")
    for l in LANGUES:
        print(f"  [{l}] {texte('auto_bouton', l, etat='ON')} | "
              f"{texte('victoire_police', l)} | {nom_niveau('sarotra', l)}")
