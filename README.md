# Jeu du Gendarme et du Voleur (Fanorona simplifié / jeu de piste circulaire)

Jeu de stratégie traditionnel en Python + **Pygame**, jouable :

* en **solo contre l'IA** (3 niveaux de difficulté, l'ordinateur joue le
  rôle opposé) ;
* en **local** (deux joueurs derrière le même écran) ;
* **en réseau** (un joueur incarne le Voleur, l'autre la Police) :
  `server.py` + `client.py` ;
* interface entièrement traduite **français / malagasy**.

Au lancement, un **menu de démarrage** permet de choisir le mode, le
rôle, la difficulté de l'IA et la langue.

## 1. Le plateau

Le plateau est un **graphe** (21 intersections / 36 lignes) défini dans
`board.py`, dans un **repère centré sur l'écran** `(cx, cy)`, avec un
rayon `R` pour le grand cercle — rendu volontairement **minimaliste et
conforme au dessin à la main (Jeu.png)** :

* **UN seul** grand cercle de rayon `R` ;
* l'**axe horizontal** de `(cx-R, cy)` à `(cx+R, cy)` et l'**axe
  vertical** de `(cx, cy-R)` à `(cx, cy+R)` (de bord en bord du grand
  cercle) ;
* un **petit cercle central** concentrique de rayon `r` ;
* **quatre anses INTERNES** : de simples **demi-cercles de rayon
  `ANSE_R`, centrés exactement sur les intersections du grand cercle
  avec les axes** (les portes `N`, `E`, `S`, `W`), mais **courbés vers
  l'intérieur du grand cercle** : le sommet de l'arc du haut
  **descend vers le centre**, celui du bas **remonte**, celui de
  gauche **va vers la droite**, celui de droite **va vers la
  gauche**. Chaque anse se raccorde au grand cercle en deux points de
  part et d'autre de la porte, et **croise l'axe en son sommet** —
  l'axe est donc coupé au sommet de l'anse. **Rien ne dépasse du
  grand cercle.**

```
        nW ——— N ——— nE          •  = intersections traversables
          ⌒ aN ⌒ (interne)       C  = centre (départ du voleur)
   wN — aW ··· C ··· aE — eN     aN/aE/aS/aW = sommets des anses
        sW ——— S ——— sE          (sur les axes, contre la bordure)
          ⌐ aS ⌐ (interne)
```

Positions de départ :

* **Voleur** (point rouge) : **strictement au centre** `(cx, cy)` ;
* **Police** (3 points bleus) : un sur le **haut du petit cercle
  central** `(cx, cy-r)` (`tn`), deux aux **sommets des anses internes
  gauche et droite** (`aW`, `aE` à `(cx∓(R-ANSE_R), cy)` — sur les
  axes, contre la bordure), modifiable via `INITIAL_COPS` dans
  `game.py`.

Toute la géométrie est en **coordonnées normalisées** (grand cercle =
rayon 1) : `R_PETIT` (petit cercle), `ANSE_R` (anses) et la table
`NODES` dans `board.py` — pour adapter le plateau, il suffit d'éditer
ces constantes ; le rendu, les règles et le réseau suivent
automatiquement.

## 2. Les règles

* **Tour par tour**, le voleur commence. À son tour, un joueur déplace **un
  seul** de ses pions d'**une intersection adjacente** en suivant une ligne
  tracée (les destinations légales s'affichent en vert).
* Une intersection contient **au plus un pion** : on ne peut pas jouer sur
  un nœud occupé.
* La **police n'a pas le droit d'entrer au centre** `C` (sinon elle pourrait
  camper dans la tanière et rendre la victoire du voleur impossible).

**Victoire :**

* la **POLICE** gagne si le voleur est **totalement bloqué** (plus aucun
  mouvement légal au début de son tour) ;
* le **VOLEUR** gagne s'il **sort du centre**, parcourt le **circuit
  extérieur** — visiter les 4 portes `N`, `E`, `S`, `W` — puis **revient au
  centre**. Rentrer au centre avant d'avoir bouclé le circuit **remet la
  progression à zéro**.

L'état du jeu (tour actuel, progression du circuit, vainqueur) est affiché
en permanence dans la barre en bas de la fenêtre.

## 3. Installation

```bash
python -m pip install -r requirements.txt   # pygame uniquement
```

Testé avec Python 3.14 + pygame-ce 2.5.8 (fonctionne avec pygame ≥ 2.0).

## 4. Lancer le jeu : le menu de démarrage

```bash
python main.py
```

Le **menu** (`menu.py`) s'affiche d'abord ; il permet de choisir :

* la **langue** : bouton en haut à droite, bascule instantanée
  **français / malagasy** de tout le menu (et de la partie ensuite) ;
* le **mode de jeu** :
  * **Solo (contre l'IA)** — puis choix du **rôle** (Voleur ou Police,
    l'IA prend le contrôle du rôle opposé) et de la **difficulté**
    (Mora / Antonony / Sarotra) ;
  * **2 joueurs (même écran)** — la partie locale d'origine ;
  * **Multijoueur (en ligne)** — saisie de l'adresse, du port, du nom
    et du rôle souhaité ;
* **Quitter** (ou `Échap`) ferme le jeu ; `Retour` (ou `Échap`) remonte
  d'un écran.

Pendant une partie : cliquer un de **ses** pions puis une destination
verte. Touches : `Échap` = retour au menu, `R` = nouvelle partie (ou
proposition de rematch en ligne).

### Fenêtre redimensionnable (affichage adaptatif)

La fenêtre est **redimensionnable librement** (agrandir, maximiser,
réduire — drapeau `pygame.RESIZABLE`). À chaque redimensionnement
(événement `pygame.VIDEORESIZE`), le rendu est **recalculé
proportionnellement** :

* le **rayon du grand cercle** est recalculé à partir de la taille
  actuelle de la fenêtre pour que le plateau reste **entièrement
  visible**, quelle que soit la dimension ;
* le **centre du plateau reste exactement au milieu** de la zone de jeu
  (fenêtre moins la barre d'état), même après un redimensionnement ;
* grand cercle, axes, petit cercle central, anses internes, positions
  des pions et taille des pions suivent l'échelle — tout est défini en
  **coordonnées normalisées** dans `board.py`, converties par la classe
  `Layout` (`render.py`) ;
* la **sélection à la souris** est mise à l'échelle elle aussi ;
* la **taille initiale s'adapte à l'écran** (`pygame.display.Info()`)
  pour ne jamais le dépasser, et une taille minimale (`MIN_W × MIN_H`)
  est garantie.

Le menu se recentre de la même façon à chaque frame.

## 5. Mode solo contre l'IA (`ai.py`)

Trois niveaux de difficulté (noms malgaches), sélectionnables **quel
que soit le rôle confié à l'IA** (voleur ou police) :

| Niveau | FR | Principe |
|---|---|---|
| `mora` | Facile | joue **au hasard** parmi les coups valides |
| `antonony` | Moyen | **heuristique simple** à un coup d'anticipation |
| `sarotra` | Difficile | **minimax + élagage alpha-bêta** (approfondissement itératif) |

* **Mora** : l'IA respecte les règles mais choisit un coup valide au
  hasard — parfait pour débuter.
* **Antonony** : la **police se rapproche des chemins du voleur** (sa
  position et sa prochaine porte, pour couper le circuit) ; le
  **voleur fuit** le policier le plus proche tout en **avançant vers
  l'objectif** de son circuit (prochaine porte, ou retour au centre
  une fois le tour complet).
* **Sarotra** : recherche adversariale **minimax avec élagage
  alpha-bêta**, approfondissement itératif de profondeur 2 à 6 sous
  limite de temps (≈ 1 s par coup), ordre des coups guidé par
  l'heuristique. La fonction d'évaluation mesure la progression du
  circuit, la distance du voleur à son objectif, sa distance à la
  police, sa mobilité et la pression des policiers sur les portes
  restantes ; gagner (ou bloquer) **vite** vaut mieux que lentement.

Utilisation programme (indépendant de pygame) :

```python
from ai import choisir_coup
frm, to = choisir_coup(game, "police", "sarotra")   # None si bloqué
```

Auto-test : `python ai.py` vérifie les coups légaux des 3 niveaux ×
2 rôles, puis joue deux parties complètes — **sarotra bat mora dans
les deux sens** (voleur et police).

En jeu, l'IA « réfléchit » une courte instant (cadence ~1 s max pour
sarotra), son coup est annoncé dans la barre d'état, et elle ne peut
jamais bloquer indéfiniment la partie (garde-fou si plus aucun coup
légal ne lui reste).

## 6. Localisation français / malagasy (`locales.py`)

Toute l'interface passe par la table `locales.py` (**81 clés × 2
langues**) et la fonction `texte()` :

```python
from locales import texte, set_langue
set_langue("mg")
texte("victoire_police")            # "Nandresy ny Polisy !"
texte("info_coup", frm="te", to="E", qui="mpangalatra")
```

Principales traductions (fr → mg) :

| Français | Malagasy |
|---|---|
| Solo | Kilalao tokana |
| Multijoueur (en ligne) | Kilalao an-tranonkala |
| Solo (contre l'IA) | Mpilalao tokana (Manohitra ny solosaina) |
| Voleur | Mpangalatra |
| Police | Polisy |
| Facile / Moyen / Difficile | Mora / Antonony / Sarotra |
| La police a gagné ! | Nandresy ny Polisy ! |
| Le voleur a gagné ! | Nandresy ny Mpangalatra ! |
| C'est le tour de... | Anjaran'i... |
| Commencer | Hanomboka |
| Quitter | Hiala |
| Choisis ton rôle | Safidio ny anjara asanao |

Détails d'implémentation :

* la langue est choisie **dans le menu** puis propagée partout
  (`set_langue`) : plateau, messages d'information, erreurs du moteur
  de règles (`game.py`), victoires ;
* le **serveur** `server.py` reste en français (messages d'erreur
  standards du moteur, langue par défaut) ;
* en ligne de commande : `python client.py --langue mg ...` ;
* `python locales.py` vérifie que les deux langues ont **exactement
  les mêmes clés** (et les mêmes paramètres `{...}`).

## 7. Jouer en réseau (2 machines)

Le serveur peut tourner sur n'importe quelle machine du réseau local ;
les deux clients s'y connectent (même machine possible pour tester).
Deux chemins possibles :

```bash
# via le menu : Multijoueur (en ligne) -> adresse, port, nom, rôle ;
# ou en ligne de commande :
python server.py                     # machine A — écoute sur le port 5555
python client.py --host 192.168.1.20 --role voleur --name Alice   # machine B
python client.py --host 192.168.1.20 --role police --name Bob     # machine C
```

Sans `--role`, le rôle est demandé dans la console (`v` / `p` / `a`).
Si deux joueurs demandent le même rôle, le **premier arrivé** est servi.
Chaque joueur ne peut bouger ses pions **que pendant son tour** ;
l'interface se met à jour dès que l'adversaire joue, et `R` propose un
rematch après une fin de partie (accepté par les deux joueurs).

### Protocole réseau (JSON ligne par ligne, TCP)

| Sens | Message | Rôle |
|---|---|---|
| client → serveur | `{"type":"join","role":"voleur"\|"police"\|"any","name":...}` | connexion / choix du rôle |
| client → serveur | `{"type":"move","frm":"te","to":"E"}` | coup (nœuds du graphe) |
| client → serveur | `{"type":"rematch"}` | rejouer |
| serveur → clients | `{"type":"start"\|"state","state":{...}}` | état synchronisé |
| serveur → client | `{"type":"error","msg":...}` | coup refusé |
| serveur → clients | `{"type":"game_over","winner":...,"state":{...}}` | fin de partie |

Serveur et client n'utilisent que le module **`socket`** de la
bibliothèque standard (aucune dépendance réseau externe) ; le serveur
**valide chaque coup** avec la classe `Game` partagée.

## 8. Structure du projet

| Fichier | Contenu |
|---|---|
| `board.py` | Géométrie + graphe : `NODES`, `EDGES`, `NEIGHBORS`, portes, anses |
| `game.py` | Règles : `Game` (coups légaux, tours, victoires, `clone()`, textes d'état traduits) — sans pygame |
| `render.py` | Rendu Pygame partagé : plateau, pions, surbrillances, barre d'état (i18n), `Layout` responsive |
| `locales.py` | Table de traduction FR / MG : `texte()`, `set_langue()` — sans dépendance |
| `ai.py` | IA solo : 3 niveaux (mora / antonony / sarotra) — sans pygame |
| `menu.py` | Menu de démarrage : langue, mode, rôle, difficulté, connexion |
| `main.py` | Point d'entrée : menu → partie locale / solo IA / lancement en ligne |
| `server.py` | Serveur TCP multi-threads : salons de 2, validation, diffusion |
| `client.py` | Client graphique réseau (thread de réception + file de messages), utilisable aussi depuis le menu |
| `tests/` | Suites de tests non interactifs (voir ci-dessous) |

Chaîne d'imports sans cycle : `locales` → seul ; `game` → `board`,
`locales` ; `ai` → `board`, `game` ; `render` → `board`, `game`,
`locales` ; `menu` → `render`, `game`, `locales` ; `main` → `menu`,
`ai`, `client`, `game`, `render`, `locales` ; `client` → `game`,
`locales`, `render`.

## 9. Tests

Auto-tests en console, sans interaction :

```bash
python board.py      # géométrie des anses, adjacences
python game.py       # victoires, retour prématuré au centre, coups illégaux
python locales.py    # clés FR/MG identiques, paramètres de formatage
python ai.py          # coups légaux des 3 niveaux + sarotra bat mora (2 sens)
```

Suites complètes (dossier `tests/`, pilote vidéo « dummy », aucune
fenêtre réelle) :

| Script | Vérifie |
|---|---|
| `tests/test_rendu.py` | 146 vérifications pixel : plateau, pions, anses, minimalisme (aucun texte sur la zone de jeu), sélection/destinations, i18n, sur 5 tailles de fenêtre |
| `tests/test_resize.py` | logique de redimensionnement : centrage exact, échelle, clamp aux tailles minimales |
| `tests/test_menu.py` | rendu des 3 écrans FR/MG, configurations renvoyées, validation du port, quitter/retour, saisie des champs |
| `tests/test_solo.py` | partie solo bout-en-bout : clics humains simulés + tours d'IA réels, rôles et langues variés |
| `tests/test_reseau.py` | protocole complet sur sockets bruts avec `server.py` en sous-processus (appariement, refus, diffusion, rematch, déconnexion) |

## 10. Idées d'extension

* scoreboard persistant côté serveur ;
* plusieurs niveaux d'IA supplémentaires (par ex. `mora` avec biais
  d'apprentissage par parties) ;
* timer par coup en mode en ligne.
