# -*- coding: utf-8 -*-
"""
discovery.py — Connexion facile : découverte des parties sur le réseau local.

Deux petits services UDP, sans dépendance externe :

  * `Annonceur` : tourne chez le joueur qui héberge. Il répond aux probes
    « y a-t-il une partie ? » avec l'adresse IP et le port TCP du serveur ;
  * `chercher_serveurs()` : envoyé par le joueur qui rejoint. Il interroge
    le réseau local (broadcast + bouclage) et renvoie la liste des serveurs
    trouvés.

Le protocole TCP du jeu lui-même reste inchangé (voir server.py) : ce module
ne sert qu'à éviter d'avoir à taper une adresse IP quand les deux joueurs
sont sur le même réseau (Wi-Fi, LAN, ou même sur la même machine).

Si la découverte échoue (réseaux différents, pare-feu...), le menu permet
toujours de saisir l'adresse IP manuellement.
"""

import json
import socket
import threading
import time

PORT_DECOUVERTE = 5556       # port UDP réservé à l'annonce des parties
PROBE = b"GENDARME_VOLEUR_QUIESTLA_V1"


def ip_locale():
    """Adresse IP LAN de cette machine (pour la donner à l'adversaire).

    Le `connect()` UDP n'envoie aucun paquet : il sert uniquement à demander
    à l'OS quelle interface sortirait vers Internet. Repli sur le nom de
    la machine, puis sur la boucle locale."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        try:
            ip = socket.gethostbyname(socket.gethostname())
            return ip if ip and not ip.startswith("127.") else "127.0.0.1"
        except OSError:
            return "127.0.0.1"
    finally:
        s.close()


def port_libre(debut=5555, essais=20):
    """Renvoie le premier port TCP libre à partir de `debut`."""
    for port in range(debut, debut + essais):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", port))
            return port
        except OSError:
            continue
        finally:
            s.close()
    raise OSError(f"aucun port libre entre {debut} et {debut + essais - 1}")


class Annonceur:
    """Répond aux probes UDP avec l'adresse du serveur à rejoindre."""

    def __init__(self, port_tcp, host=None):
        self.port_tcp = port_tcp
        self.host = host or ip_locale()
        self.arret = threading.Event()
        self.sock = None
        self.thread = None

    def demarrer(self):
        """Lance l'annonce en tâche de fond. Renvoie True si c'est ouvert."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("", PORT_DECOUVERTE))
        except OSError:
            s.close()
            return False
        self.sock = s
        self.thread = threading.Thread(target=self._boucle, daemon=True)
        self.thread.start()
        return True

    def _boucle(self):
        self.sock.settimeout(0.4)
        while not self.arret.is_set():
            try:
                data, addr = self.sock.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break
            if data.strip() != PROBE:
                continue
            reponse = json.dumps({"host": self.host,
                                  "port": self.port_tcp}).encode("utf-8")
            try:
                self.sock.sendto(reponse, addr)
            except OSError:
                pass

    def arreter(self):
        """Arrête l'annonceur et libère le port UDP."""
        self.arret.set()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None


def chercher_serveurs(delai=1.6, port=None):
    """Renvoie les serveurs qui répondent, sous forme de listes de dicts
    ``{"host": ip, "port": port_tcp}``.

    La sonde est envoyée en broadcast (pour les autres machines du LAN) et
    en unicast sur 127.0.0.1 (fonctionne toujours, y compris si le broadcast
    est bloqué : permet de jouer à deux sur le même PC)."""
    port = PORT_DECOUVERTE if port is None else port
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.2)
    serveurs = []
    try:
        s.bind(("0.0.0.0", 0))
        for cible in ("255.255.255.255", "127.0.0.1"):
            try:
                s.sendto(PROBE, (cible, port))
            except OSError:
                pass
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            try:
                data, addr = s.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                info = json.loads(data.decode("utf-8"))
                hote = str(info["host"])
                port_tcp = int(info["port"])
                if not 1 <= port_tcp <= 65535:
                    continue
            except (ValueError, TypeError, KeyError, UnicodeDecodeError):
                continue
            if (hote, port_tcp) not in [(x["host"], x["port"]) for x in serveurs]:
                serveurs.append({"host": hote, "port": port_tcp})
    finally:
        s.close()
    return serveurs
