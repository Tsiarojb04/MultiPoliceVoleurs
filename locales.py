# -*- coding: utf-8 -*-
"""
locales.py — Localisation du jeu : FRANÇAIS (fr) et MALAGASY (mg).

Toutes les chaînes affichées à l'écran passent par la fonction texte() :

    texte("victoire_police", "mg")        -> "Nandresy ny Polisy !"
    texte("info_coup", "fr", frm="te", to="aE", qui="voleur")

Les textes du moteur de règles (game.py) utilisent aussi cette table via
la langue « courante » (set_langue) : les UI fixent la langue au démarrage.
Le module ne dépend d'aucune bibliothèque (pygame y compris) afin d'être
importable partout, y compris par le serveur réseau (reste en "fr").

Niveaux de difficulté : mora (facile), antonony (moyen), sarotra (difficile).
"""

LANGUES = ("fr", "mg")
LANGUE_DEFAUT = "fr"

# ---------------------------------------------------------------------------
# La table des textes : clé -> traduction, pour chaque langue.
# Les accolades {x} sont des paramètres de formatage.
# ---------------------------------------------------------------------------
TEXTES = {
    "fr": {
        # --- titres des fenêtres
        "titre": "Jeu du Gendarme et du Voleur",
        "titre_menu": "Jeu du Gendarme et du Voleur",
        "titre_solo": "Jeu du Gendarme et du Voleur — solo contre l'IA",
        "titre_local": "Jeu du Gendarme et du Voleur — 2 joueurs locaux",
        "titre_ligne": "Jeu du Gendarme et du Voleur — mode en ligne",
        "erreur_connexion": "Connexion impossible au serveur {hote}:{port}. "
                            "Vérifiez que server.py est bien lancé, "
                            "puis réessayez depuis le menu.",
        # --- menu principal
        "menu_sous_titre": "Choisissez votre mode de jeu",
        "mode_solo": "Solo (contre l'IA)",
        "mode_local": "2 joueurs (même écran)",
        "mode_ligne": "Multijoueur (en ligne)",
        # --- menu : rôle et difficulté
        "menu_role": "Choisis ton rôle",
        "role_voleur": "Voleur (point rouge)",
        "role_police": "Police (3 points bleus)",
        "role_any": "Peu importe",
        "menu_niveau": "Difficulté de l'IA",
        "niveau_mora": "Facile (Mora)",
        "niveau_antonony": "Moyen (Antonony)",
        "niveau_sarotra": "Difficile (Sarotra)",
        # --- boutons génériques
        "btn_commencer": "Commencer",
        "btn_quitter": "Quitter",
        "btn_retour": "Retour",
        "btn_langue": "Langue : Français",
        # --- menu en ligne : champs
        "champ_hote": "Adresse du serveur",
        "champ_port": "Port",
        "champ_nom": "Votre nom (facultatif)",
        "port_invalide": "Port invalide (nombre entre 1 et 65535).",
        # --- noms des rôles / niveaux, seuls
        "nom_voleur": "voleur",
        "nom_police": "police",
        "nom_voleur_maj": "VOLEUR",
        "nom_police_maj": "POLICE",
        # --- barre d'état (render.py)
        "tour_voleur": "Au tour du joueur 1 : le VOLEUR",
        "tour_police": "Au tour du joueur 2 : la POLICE",
        "victoire_voleur": "LE VOLEUR GAGNE !",
        "victoire_police": "LA POLICE GAGNE !",
        # --- progression du circuit (game.py)
        "prog_boucle": "Il a bouclé le circuit et regagné le centre.",
        "prog_bloque": "Le voleur est totalement bloqué.",
        "prog_centre": "Le voleur est au centre (circuit à recommencer à zéro).",
        "prog_portes": "Portes visitées : {visitees} — manque {manque}.",
        "prog_fini": "Circuit complet ! Le voleur doit rentrer au centre pour gagner.",
        # --- messages du jeu local / solo
        "info_depart": "Joueur 1 (voleur) : cliquez sur le point rouge pour commencer.",
        "info_nouvelle": "Nouvelle partie ! Le voleur commence.",
        "info_termine": "Partie terminée — appuyez sur R pour rejouer.",
        "info_coup": "Coup joué : {frm} → {to} ({qui}).",
        "info_refuse": "Coup refusé : {erreur}",
        "info_selection": "Pion {qui} sélectionné en {node} — cliquez une destination verte.",
        "info_clic_faux": "Cliquez sur un de VOS pions (rouge au tour du voleur, "
                          "bleus au tour de la police).",
        "qui_voleur": "voleur",
        "qui_police": "policier",
        # --- mode solo contre l'IA
        "solo_bandeau": "Vous jouez les {role} — l'IA ({niveau}) joue les {role_ia}.",
        "ia_reflechit": "L'IA ({niveau}) réfléchit...",
        "ia_coup": "L'IA ({niveau}) a joué : {frm} → {to}.",
        "ia_bloquee": "L'IA n'a plus aucun coup légal — partie figée.",
        # --- mode réseau (client.py)
        "net_attente": "En attente d'un adversaire...",
        "net_connexion": "Connexion au serveur... en attente d'un adversaire.",
        "net_adversaire": "Adversaire trouvé : {qui}",
        "net_termine": "Partie terminée — appuyez sur R pour proposer de rejouer.",
        "net_refuse": "Refusé : {msg}",
        "net_envoye": "Coup envoyé : {frm} → {to}...",
        "net_pas_tour": "Ce n'est pas votre tour !",
        "net_rematch": "Demande de rejouer envoyée...",
        "net_vous_voleur": "Vous êtes le VOLEUR",
        "net_vous_police": "Vous êtes la POLICE",
        "net_adversaire_court": "adversaire",
        "net_serveur_role": "Serveur {hote}:{port} — rôle souhaité : {role}",
        "net_perdu": "Connexion perdue avec le serveur.",
        "net_deconnecte": "Serveur déconnecté.",
        "net_erreur": "Connexion impossible à {hote}:{port} ({erreur})",
        # --- invites console (client.py en ligne de commande)
        "con_role_titre": "Quel rôle voulez-vous jouer ?",
        "con_role_options": "  v = VOLEUR (pion rouge)    "
                            "p = POLICE (3 pions bleus)    a = peu importe",
        "con_role_choix": "Votre choix [v/p/a] : ",
        "con_hote": "Adresse du serveur (Entrée = 127.0.0.1) : ",
        "con_port": "Port (Entrée = 5555) : ",
        "con_nom": "Votre nom (facultatif) : ",
        # --- erreurs du moteur de règles (game.py)
        "err_partie_finie": "La partie est terminée.",
        "err_pas_tour": "Ce n'est pas le tour de {qui}.",
        "err_noeud": "Nœud inconnu : {noeud}.",
        "err_adjacents": "{frm} et {to} ne sont pas adjacents.",
        "err_occupe": "{noeud} est occupé.",
        "err_centre": "Coup interdit (la police n'entre pas au centre).",
        "err_pas_voleur": "Ce pion rouge n'est pas le voleur.",
        "err_pas_police": "Ce pion bleu n'est pas un policier.",
    },

    # -------------------------------------------------------------------
    "mg": {
        # --- titres des fenêtres
        "titre": "Kilalaon'ny Zandarma sy ny Mpangalatra",
        "titre_menu": "Kilalaon'ny Zandarma sy ny Mpangalatra",
        "titre_solo": "Kilalaon'ny Zandarma sy ny Mpangalatra — mpilalao tokana "
                      "(manohitra ny solosaina)",
        "titre_local": "Kilalaon'ny Zandarma sy ny Mpangalatra — mpilalao roa",
        "titre_ligne": "Kilalaon'ny Zandarma sy ny Mpangalatra — an-tranonkala",
        "erreur_connexion": "Tsy afaka mifandray amin'ny seva {hote}:{port}. "
                            "Jereo raha mandeha ny server.py, dia andramo "
                            "indray avy amin'ny menio.",
        # --- menu principal
        "menu_sous_titre": "Safidio ny fomba fikilalaoanao",
        "mode_solo": "Kilalao tokana (manohitra ny solosaina)",
        "mode_local": "Mpilalao roa (efijery iray)",
        "mode_ligne": "Kilalao an-tranonkala",
        # --- menu : rôle et difficulté
        "menu_role": "Safidio ny anjara asanao",
        "role_voleur": "Mpangalatra (teboka mena)",
        "role_police": "Polisy (teboka manga telo)",
        "role_any": "Na inona na inona",
        "menu_niveau": "Fahasarotan'ny solosaina (IA)",
        "niveau_mora": "Mora",
        "niveau_antonony": "Antonony",
        "niveau_sarotra": "Sarotra",
        # --- boutons génériques
        "btn_commencer": "Hanomboka",
        "btn_quitter": "Hiala",
        "btn_retour": "Hiverina",
        "btn_langue": "Fiteny : Malagasy",
        # --- menu en ligne : champs
        "champ_hote": "Aderesin'ny seva",
        "champ_port": "Port",
        "champ_nom": "Ny anaranao (tsy voatery)",
        "port_invalide": "Port tsy mety (isa 1 hatramin'ny 65535).",
        # --- noms des rôles / niveaux, seuls
        "nom_voleur": "mpangalatra",
        "nom_police": "polisy",
        "nom_voleur_maj": "MPANGALATRA",
        "nom_police_maj": "POLISY",
        # --- barre d'état (render.py)
        "tour_voleur": "Anjaran'ny mpilalao 1 : ny MPANGALATRA",
        "tour_police": "Anjaran'ny mpilalao 2 : ny POLISY",
        "victoire_voleur": "Nandresy ny Mpangalatra !",
        "victoire_police": "Nandresy ny Polisy !",
        # --- progression du circuit (game.py)
        "prog_boucle": "Nitafo ny lalana rehetra izy ary niverina tao afovoany.",
        "prog_bloque": "Voasakana tanteraka ny mpangalatra.",
        "prog_centre": "Ao afovoany ny mpangalatra (averina amin'ny zero ny lalana).",
        "prog_portes": "Vavahady efa nodiavina : {visitees} — tsy mbola : {manque}.",
        "prog_fini": "Vita ny lalana ! Tsy maintsy miverina afovoany ny "
                     "mpangalatra mba handresy.",
        # --- messages du jeu local / solo
        "info_depart": "Mpilalao 1 (mpangalatra) : tsindrio ny teboka mena "
                       "hanomboka.",
        "info_nouvelle": "Kilalao vaovao ! Ny mpangalatra no manomboka.",
        "info_termine": "Vita ny kilalao — tsindrio R mba hamerenana milalao.",
        "info_coup": "Lalana natao : {frm} → {to} ({qui}).",
        "info_refuse": "Tsy nekena ny lalana : {erreur}",
        "info_selection": "Pion {qui} no safidina ao {node} — tsindrio ny "
                          "toerana maitso.",
        "info_clic_faux": "Tsindrio ny PION NAOTOMBOHOKA (mena rehez anjaran'ny "
                          "mpangalatra, manga rehez anjaran'ny polisy).",
        "qui_voleur": "mpangalatra",
        "qui_police": "polisy",
        # --- mode solo contre l'IA
        "solo_bandeau": "Ianao no {role} — ny solosaina ({niveau}) no {role_ia}.",
        "ia_reflechit": "Mieritreritra ny solosaina ({niveau})...",
        "ia_coup": "Nataon'ny solosaina ({niveau}) : {frm} → {to}.",
        "ia_bloquee": "Tsy manana lalana intsony ny solosaina — mijanona ny kilalao.",
        # --- mode réseau (client.py)
        "net_attente": "Miandry mpifanandrina...",
        "net_connexion": "Mifandray amin'ny seva... miandry mpifanandina.",
        "net_adversaire": "Hit ny mpifanandina : {qui}",
        "net_termine": "Vita ny kilalao — tsindrio R hanoloana hiverina milalao.",
        "net_refuse": "Tsy nekena : {msg}",
        "net_envoye": "Nalefa ny lalana : {frm} → {to}...",
        "net_pas_tour": "Tsy anjaranao izao !",
        "net_rematch": "Nalefa ny fangatahana hiverina milalao...",
        "net_vous_voleur": "Ianao no MPANGALATRA",
        "net_vous_police": "Ianao no POLISY",
        "net_adversaire_court": "mpifanandina",
        "net_serveur_role": "Seva {hote}:{port} — anjara irina : {role}",
        "net_perdu": "Very ny fifandraisana amin'ny seva.",
        "net_deconnecte": "Tapaka ny fifandraisana amin'ny seva.",
        "net_erreur": "Tsy afaka mifandray amin'ny {hote}:{port} ({erreur})",
        # --- invites console (client.py en ligne de commande)
        "con_role_titre": "Inona ny anjara asa tianao ?",
        "con_role_options": "  v = MPANGALATRA (pion mena)    "
                            "p = POLISY (pion manga 3)    a = na inona na inona",
        "con_role_choix": "Ny safidinao [v/p/a] : ",
        "con_hote": "Aderesin'ny seva (Entrée = 127.0.0.1) : ",
        "con_port": "Port (Entrée = 5555) : ",
        "con_nom": "Ny anaranao (tsy voatery) : ",
        # --- erreurs du moteur de règles (game.py)
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

# ---------------------------------------------------------------------------
# Langue « courante » (utilisée par le moteur game.py pour ses messages
# d'erreur — les UI la fixent via set_langue ; le serveur reste en "fr").
# ---------------------------------------------------------------------------
_langue_courante = LANGUE_DEFAUT


def set_langue(langue):
    """Fixe la langue courante du programme (game.py s'en sert)."""
    global _langue_courante
    if langue in LANGUES:
        _langue_courante = langue


def langue_courante():
    return _langue_courante


def texte(cle, langue=None, **params):
    """Renvoie le texte `cle` dans `langue` (défaut : langue courante).

    Les paramètres nommés remplissent les accolades : texte("info_coup",
    frm="te", to="aE", qui="voleur"). Si la clé manque, la clé elle-même
    est renvoyée (l'interface reste utilisable)."""
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


# ---------------------------------------------------------------------------
# Petites aides partagées par les UI
# ---------------------------------------------------------------------------
def nom_role(role, langue=None):
    """Nom affichable d'un rôle ("voleur"/"police")."""
    return texte("nom_voleur" if role == "voleur" else "nom_police", langue)


def nom_niveau(niveau, langue=None):
    """Nom affichable d'un niveau d'IA ("mora"/"antonony"/"sarotra")."""
    return texte(f"niveau_{niveau}", langue)


if __name__ == "__main__":
    # Auto-test : les deux langues contiennent exactement les mêmes clés,
    # avec les mêmes paramètres de formatage, et aucune traduction vide.
    cles_fr, cles_mg = set(TEXTES["fr"]), set(TEXTES["mg"])
    assert cles_fr == cles_mg, (cles_fr ^ cles_mg)
    for cle in cles_fr:
        vf, vm = TEXTES["fr"][cle], TEXTES["mg"][cle]
        assert vf and vm, f"traduction vide : {cle}"
        def params(s):
            import re
            return set(re.findall(r"\{(\w+)\}", s))
        assert params(vf) == params(vm), f"paramètres différents : {cle}"
    # la clé "btn_langue" porte le nom de SA langue
    assert "Français" in TEXTES["fr"]["btn_langue"]
    assert "Malagasy" in TEXTES["mg"]["btn_langue"]
    print(f"Auto-test locales : OK — {len(cles_fr)} clés x {len(LANGUES)} langues")
    for l in LANGUES:
        print(f"  [{l}] {texte('mode_solo', l)} | {texte('victoire_police', l)} "
              f"| {texte('btn_commencer', l)}")
