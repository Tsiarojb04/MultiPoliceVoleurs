# -*- coding: utf-8 -*-
"""test_ia_auto.py — Tests de l'IA et du mode « Auto-Play (IA vs IA) ».

Partie 1 (unitaire) : coups légaux pour les 3 niveaux / 2 rôles, clone().
Partie 2 (réseau) : vrai serveur en sous-processus, deux clients sockets,
activation par un client, synchronisation des états sur les DEUX écrans,
refus d'un coup manuel, fin de partie, rematch et bascule à chaud.
"""
import json
import os
import socket
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from ai import NIVEAUX, choisir_coup           # noqa: E402
from game import POLICE, VOLEUR, Game          # noqa: E402
from locales import LANGUES, TEXTES, texte     # noqa: E402

# --------------------------------------------------------------- 1. IA / clone
for niveau in NIVEAUX:
    for role in (VOLEUR, POLICE):
        g = Game()
        if role == POLICE:
            g.move(VOLEUR, "C", "te")          # donne le tour à la police
        coup = choisir_coup(g, role, niveau, temps_max=0.05)
        assert coup is not None and coup in g.legal_moves(role), (niveau, role, coup)
print("1. coups IA légaux (3 niveaux x 2 rôles) : OK")

g = Game()
copie = g.clone()
tour_initial = g.turn
copie.move(VOLEUR, "C", "te")
assert g.thief == "C" and copie.thief == "te"
assert g.cops == copie.cops and g.turn == tour_initial
assert copie.turn != tour_initial
print("2. Game.clone() indépendant : OK")

cles_fr, cles_mg = set(TEXTES["fr"]), set(TEXTES["mg"])
assert cles_fr == cles_mg and LANGUES == ("fr", "mg")
for cle in ("auto_bouton", "auto_bandeau", "auto_active", "btn_rejouer"):
    assert texte(cle, "fr") != texte(cle, "mg"), cle
print("3. traductions fr/mg des nouveaux textes : OK")


# --------------------------------------------------------------- 2. réseau IA
class MiniClient:
    """Client TCP minimal : une ligne JSON par message."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(10)
        self.buf = b""

    def envoyer(self, obj):
        self.sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    def recevoir_brut(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("serveur déconnecté")
            self.buf += chunk
        ligne, _, self.buf = self.buf.partition(b"\n")
        return json.loads(ligne.decode("utf-8"))

    def fermer(self):
        try:
            self.sock.close()
        except OSError:
            pass


def recevoir(client, types=None, timeout=10, ignores=None):
    """Lit jusqu'à un message du type attendu ; les autres peuvent être
    conservés dans `ignores` pour ne pas perdre le fil des états reçus."""
    client.sock.settimeout(timeout)
    while True:
        msg = client.recevoir_brut()
        if types is None or msg["type"] in types:
            return msg
        if ignores is not None:
            ignores.append(msg)


def port_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


environ = os.environ.copy()
environ["POLICE_VOLEUR_AUTO_DELAI"] = "0.01"   # spectateur accéléré
environ["POLICE_VOLEUR_AUTO_TEMPS"] = "0.01"
proc = None
try:
    # Petit retry : un port fraîchement libéré peut être pris par un autre
    # processus entre le choix et le bind du serveur.
    for _tentative in range(3):
        port = port_libre()
        proc = subprocess.Popen(
            [sys.executable, "-u", "server.py", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=RACINE, env=environ, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        for _ in range(50):
            try:
                sonde = socket.create_connection(("127.0.0.1", port),
                                                 timeout=0.2)
                sonde.close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            proc.terminate()
            proc.wait(timeout=5)
            proc = None
            continue
        break
    else:
        raise RuntimeError("le serveur n'a pas démarré")

    A = MiniClient("127.0.0.1", port)
    B = MiniClient("127.0.0.1", port)
    A.envoyer({"type": "join", "role": "voleur", "name": "A"})
    B.envoyer({"type": "join", "role": "any", "name": "B"})
    assert recevoir(A, {"welcome"})["role"] == VOLEUR
    assert recevoir(B, {"welcome"})["role"] == POLICE
    s0a, s0b = recevoir(A, {"start"}), recevoir(B, {"start"})
    assert s0a["state"] == s0b["state"] and s0a["auto"] is False
    print("4. appariement + état initial identique : OK")

    # ------- activation par le joueur B, niveau facile pour aller vite
    B.envoyer({"type": "auto", "enabled": True, "niveau": "antonony"})
    ca, cb = recevoir(A, {"auto"}), recevoir(B, {"auto"})
    assert ca["enabled"] is True and ca["niveau"] == "antonony"
    assert cb["enabled"] is True and cb["niveau"] == "antonony"
    print("5. activation diffusée aux deux clients : OK")

    # ------- coup manuel refusé pendant l'auto-play
    A.envoyer({"type": "move", "frm": "C", "to": "te"})
    ignores_a = []
    err = recevoir(A, {"error"}, ignores=ignores_a)
    assert "Auto-Play" in err["msg"], err
    print("6. coup manuel refusé en mode spectateur : OK")

    # ------- la partie se joue seule et les deux écrans reçoivent la même chose
    def collecter(client, initiaux=()):
        # on garde (état, auto, niveau) pour vérifier la resynchronisation
        recus, fin = list(initiaux), None
        while fin is None:
            msg = recevoir(client, timeout=20)
            if msg["type"] == "state":
                recus.append((msg["state"], msg.get("auto"), msg.get("niveau")))
            elif msg["type"] == "game_over":
                fin = msg
            elif msg["type"] in ("info", "error", "auto"):
                continue
            else:
                raise AssertionError(f"message inattendu : {msg}")
        return recus, fin

    initiaux_a = [(m["state"], m.get("auto"), m.get("niveau"))
                  for m in ignores_a if m["type"] == "state"]
    recus_a, fin_a = collecter(A, initiaux_a)
    recus_b, fin_b = collecter(B)
    etats_a = [x[0] for x in recus_a]
    etats_b = [x[0] for x in recus_b]
    assert etats_a and etats_a == etats_b
    assert all(x[1] is True and x[2] == "antonony" for x in recus_a)
    assert fin_a["state"] == fin_b["state"]
    # dernier coup = game_over, sauf si le garde-fou de 500 coups a joué
    if fin_a["state"]["move_count"] == etats_a[-1]["move_count"]:
        assert fin_a["state"]["move_count"] >= 200
    else:
        assert fin_a["state"]["move_count"] == etats_a[-1]["move_count"] + 1
    assert fin_a["winner"] == fin_a["state"]["winner"] in (VOLEUR, POLICE)
    print(f"7. {len(etats_a)} coups IA synchronisés + fin de partie : OK")

    # ------- rematch : un seul spectateur suffit, le mode est conservé
    A.envoyer({"type": "rematch"})
    recevoir(A, {"welcome"})
    recevoir(B, {"welcome"})
    n_a, n_b = recevoir(A, {"start"}), recevoir(B, {"start"})
    assert n_a["auto"] is True and n_a["state"] == n_b["state"]
    print("8. rematch en mode spectateur : OK")

    # ------- bascule à chaud : désactivation puis reprise manuelle
    B.envoyer({"type": "auto", "enabled": False})
    ignores_a2, ignores_b2 = [], []
    assert recevoir(A, {"auto"}, ignores=ignores_a2)["enabled"] is False
    assert recevoir(B, {"auto"}, ignores=ignores_b2)["enabled"] is False
    time.sleep(0.2)                       # on laisse le thread IA s'arrêter

    def drainer(client):
        """Vide les messages déjà en vol (coups joués avant la bascule)."""
        messages = []
        client.sock.settimeout(0.05)
        while True:
            try:
                messages.append(client.recevoir_brut())
            except socket.timeout:
                break
        client.sock.settimeout(10)
        return messages

    en_vol = ignores_a2 + ignores_b2 + drainer(A) + drainer(B)
    etats_en_vol = [m["state"] for m in en_vol if m["type"] == "state"]
    etat = max(etats_en_vol, key=lambda e: e["move_count"],
               default=n_a["state"])
    g = Game.from_dict(etat)
    role = g.turn
    frm, to = g.legal_moves(role)[0]      # coup légal pour le camp au trait
    expediteur = A if role == VOLEUR else B
    expediteur.envoyer({"type": "move", "frm": frm, "to": to})
    m_a, m_b = recevoir(A, {"state"}), recevoir(B, {"state"})
    assert m_a["state"] == m_b["state"]
    assert m_a["state"]["move_count"] == etat["move_count"] + 1
    assert m_a["auto"] is False
    print("9. désactivation à chaud + contrôle manuel rendu : OK")

    A.envoyer({"type": "quit"})
    B.fermer()
    print("test_ia_auto : TOUS OK")
finally:
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
