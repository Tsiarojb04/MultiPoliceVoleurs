# -*- coding: utf-8 -*-
"""test_reseau.py — Test du protocole réseau avec SOCKETS BRUTS.

Démarre server.py en sous-processus sur un port libre, puis rejoue un
dialogue complet client/serveur :
  1. appariement (join + waiting) et attribution des rôles ;
  2. diffusion de l'état initial (start) aux deux joueurs ;
  3. refus d'un coup joué hors tour ;
  4. coup légal du voleur diffusé aux DEUX joueurs ;
  5. coup illégal (destination occupée) refusé à l'émetteur seul ;
  6. coup légal de la police diffusé ;
  7. rematch refusé avant la fin de la partie ;
  8. message JSON illisible géré proprement ;
  9. quit -> l'adversaire est informé de la déconnexion.
"""
import json
import os
import socket
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)


class MiniClient:
    """Mini client TCP : une ligne JSON par message (protocole du jeu)."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(10)
        self.buf = b""

    def envoyer(self, obj):
        self.sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    def recevoir(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("connexion fermée par le serveur")
            self.buf += chunk
        ligne, _, self.buf = self.buf.partition(b"\n")
        return json.loads(ligne.decode("utf-8"))

    def fermer(self):
        try:
            self.sock.close()
        except OSError:
            pass


def port_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


port = port_libre()
proc = subprocess.Popen(
    [sys.executable, "-u", "server.py", "--host", "127.0.0.1",
     "--port", str(port)],
    cwd=RACINE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8")

try:
    # attendre que le serveur écoute (jusqu'à 5 s)
    for _ in range(50):
        try:
            sonde = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            sonde.close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("le serveur n'a pas démarré")

    # ------------------------- 0. découverte automatique du serveur lance
    from discovery import chercher_serveurs
    trouves = chercher_serveurs(delai=1.0)
    assert any(s["port"] == port for s in trouves), (port, trouves)
    print("0. serveur découvert automatiquement sur le réseau local : OK")

    # ---------------------------------------------- 1. join + appariement
    A = MiniClient("127.0.0.1", port)
    A.envoyer({"type": "join", "role": "voleur", "name": "TesteurA"})
    msg = A.recevoir()
    assert msg["type"] == "waiting", msg

    B = MiniClient("127.0.0.1", port)
    B.envoyer({"type": "join", "role": "any", "name": "TesteurB"})
    wa = A.recevoir()
    assert wa["type"] == "welcome" and wa["role"] == "voleur" \
        and "TesteurB" in wa["adversaire"], wa
    wb = B.recevoir()
    assert wb["type"] == "welcome" and wb["role"] == "police", wb
    sa, sb = A.recevoir(), B.recevoir()
    assert sa["type"] == "start" and sb["type"] == "start", (sa, sb)
    etat = sa["state"]
    assert etat["thief"] == "C" \
        and sorted(etat["cops"]) == ["aE", "aW", "tn"] \
        and etat["turn"] == "voleur" and etat["winner"] is None, etat
    print("1. appariement + diffusion de l'état initial : OK")

    # -------------------------------------- 2. coup joué hors tour refusé
    B.envoyer({"type": "move", "frm": "tn", "to": "te"})
    err = B.recevoir()
    assert err["type"] == "error" and "tour" in err["msg"], err
    print("2. coup hors tour refusé : OK")

    # --------------------------- 3. coup légal diffusé aux deux joueurs
    A.envoyer({"type": "move", "frm": "C", "to": "te"})
    for qui, c in (("A", A), ("B", B)):
        m = c.recevoir()
        assert m["type"] == "state" and m["state"]["thief"] == "te" \
            and m["state"]["turn"] == "police", (qui, m)
    print("3. coup légal du voleur diffusé aux deux joueurs : OK")

    # ------------------- 4. coup illégal (destination occupée) -> erreur
    B.envoyer({"type": "move", "frm": "tn", "to": "te"})
    err = B.recevoir()
    assert err["type"] == "error", err
    print("4. coup illégal (destination occupée) refusé : OK")

    # --------------------------------- 5. coup légal de la police diffusé
    B.envoyer({"type": "move", "frm": "aE", "to": "eN"})
    m = A.recevoir()
    assert m["type"] == "state", m
    m = B.recevoir()
    assert m["type"] == "state" and sorted(m["state"]["cops"]) == \
        ["aW", "eN", "tn"], m
    print("5. coup de la police diffusé : OK")

    # ----------------------------------- 6. rematch prématuré -> refusé
    A.envoyer({"type": "rematch"})
    err = A.recevoir()
    assert err["type"] == "error", err
    print("6. rematch prématuré refusé : OK")

    # --------------------------------------- 7. JSON illisible -> erreur
    A.sock.sendall("ceci n'est pas du json\n".encode("utf-8"))
    err = A.recevoir()
    assert err["type"] == "error" and "illisible" in err["msg"], err
    print("7. JSON illisible géré proprement : OK")

    # ------------------- 8. quit -> l'adversaire est informé, puis fin
    A.envoyer({"type": "quit"})
    info = B.recevoir()
    assert info["type"] == "info" and "déconnecté" in info["msg"], info
    print("8. déconnexion signalée à l'adversaire : OK")

    B.fermer()
    print("test_reseau : TOUS OK")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

