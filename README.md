# Jeu du Gendarme et du Voleur — multijoueur en ligne

Jeu de stratégie tour par tour en Python + **Pygame**, **uniquement en
multijoueur en ligne**. Deux joueurs se connectent facilement et, s'ils le
souhaitent, peuvent transformer la partie en duel d'IA entièrement
automatique : **Auto-Play (IA vs IA) / Mode Spectateur IA**.

Langues disponibles : français et malgache (`L` dans le menu pour basculer).

## Connexion en 2 gestes

```bash
python -m pip install -r requirements.txt
python main.py
```

**Joueur 1 (l'hôte)** : clique sur **« Héberger une partie »**. Le serveur
démarre automatiquement et l'adresse à partager (par exemple
`192.168.1.20:5555`) s'affiche à l'écran. Il n'a qu'à l'envoyer à l'autre
joueur (messagerie, SMS...).

**Joueur 2** : clique sur **« Rejoindre une partie »**. Les parties présentes
sur le même réseau sont détectées automatiquement : un clic sur le bouton
`Rejoindre <IP>` suffit. Si la détection échoue (réseaux différents ou
pare-feu), il saisit simplement l'adresse IP partagée dans le champ prévu à
cet effet — le port est toujours le même (5555), rien d'autre à régler. Si
l'adresse partagée comporte un autre port (ex. `192.168.1.20:5556`), il suffit
de la copier telle quelle.

Les rôles sont attribués automatiquement : l'un joue le Voleur (pion rouge),
l'autre la Police (3 pions bleus). Aucun réglage à synchroniser.

Il est aussi possible de jouer à deux sur la même machine : lancer
`python main.py` deux fois, héberger d'un côté et rejoindre de l'autre (la
partie locale est détectée automatiquement).

### Lancement en ligne de commande (facultatif)

```bash
python server.py                 # côté hôte, écoute sur le port 5555
python client.py                 # détecte automatiquement le serveur
python client.py --host 192.168.1.20   # ou connexion manuelle
```

## Mode Auto-Play (IA vs IA / spectateur)

Le bouton **« Auto-Play (IA) : OFF/ON »** est disponible dans la salle
d'attente **et** dans le HUD, avec un bouton de difficulté (`Mora` = facile,
`Antonony` = moyen, `Sarotra` = difficile, ce dernier étant le défaut
équilibré). Un raccourci `A` bascule aussi le mode.

Lorsqu'il est actif :

- **le serveur** calcule les coups de la police *et* du voleur avec `ai.py`,
  puis diffuse le même état aux deux écrans : aucun risque de désync ;
- les clics sur le plateau sont ignorés des deux côtés ; les boutons du HUD
  (désactiver le mode, changer la difficulté, rejouer) et `Échap` restent
  utilisables ;
- la bascule est immédiate, même en cours de partie : reprendre le contrôle
  rend la main au joueur dont c'est le tour ;
- en fin de partie, l'écran de victoire s'affiche sur les deux clients et
  **« Rejouer (R) »** relance une partie spectateur (un seul spectateur
  suffit à voter).

Un garde-fou de 200 coups départage les parties qui n'aboutissent pas
(vainqueur choisi selon l'évaluation de la position). Le rythme des coups
peut être réglé pour les tests via les variables d'environnement
`POLICE_VOLEUR_AUTO_DELAI` (défaut `0.45` s) et
`POLICE_VOLEUR_AUTO_TEMPS` (budget de recherche Sarotra, défaut `0.35` s).

## Commandes pendant la partie

- cliquer sur **un de ses pions**, puis sur une **destination verte** ;
- `A` : activer / désactiver l'Auto-Play ;
- `R` : proposer de rejouer (les deux joueurs doivent être d'accord, sauf
  en mode Auto-Play où un suffit) ;
- `Échap` : quitter la partie et revenir à l'écran de connexion ;
- `L` (menu) : français / malgache.

La fenêtre est redimensionnable : le plateau, les pions et la barre d'état
sont recalculés proportionnellement et restent centrés.

## Règles du jeu

- Le **voleur** commence, depuis le centre. À chaque tour, un joueur déplace
  un seul pion vers une intersection adjacente ; deux pions ne peuvent pas
  occuper le même nœud. La police n'a pas le droit d'entrer au centre.
- La **police gagne** si le voleur n'a plus aucun coup légal.
- Le **voleur gagne** s'il sort du centre, visite les quatre portes
  `N`, `E`, `S`, `W` puis revient au centre. Rentrer trop tôt remet la
  progression à zéro.

Le plateau (21 intersections) et la géométrie sont définis dans `board.py`,
les règles dans `game.py`, le rendu dans `render.py`.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `main.py` | Interface de connexion et lancement du jeu |
| `menu.py` | Écran « Héberger » / « Rejoindre » + détection des parties |
| `discovery.py` | Annonce UDP et recherche des serveurs sur le LAN |
| `server.py` | Serveur TCP : appariage, validation des coups, diffusion et pilotage IA du mode Auto-Play |
| `client.py` | Client pygame : réception de l'état, coups et HUD Auto-Play |
| `ai.py` | IA réintroduite du solo : Mora / Antonony / Sarotra (minimax alpha-bêta) |
| `game.py`, `board.py`, `render.py` | Règles, plateau et affichage partagés |
| `locales.py` | Textes affichés (français / malgache) |

## Tests

```bash
python game.py
python ai.py
python locales.py
python tests/test_menu.py
python tests/test_ia_auto.py
python tests/test_rendu.py
python tests/test_resize.py
python tests/test_reseau.py
```

`test_reseau.py` lance un vrai serveur sur un port libre, joue un dialogue
client/serveur complet (appariement, coups légaux et illégaux, rematch,
déconnexion) et vérifie que le serveur est bien découvert automatiquement.
