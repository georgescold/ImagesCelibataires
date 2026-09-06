# -*- coding: utf-8 -*-
"""Ouverture de session : un mot de passe unique, un cookie signe."""
import hmac, time
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

ATTENTE = {}      # adresse -> instant du prochain essai autorise


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        ip = self.headers.get("x-forwarded-for", "?").split(",")[0].strip()
        maintenant = time.time()
        if ATTENTE.get(ip, 0) > maintenant:
            return L.json_rep(self, {"erreur": "trop d'essais, patiente un instant"}, 429)

        mdp = (L.corps_json(self) or {}).get("mdp", "")
        if not L.MDP:
            return L.json_rep(self, {"erreur": "aucun mot de passe configure"}, 500)
        # comparaison a temps constant : une comparaison naive laisse deviner
        # le mot de passe caractere par caractere en mesurant le temps de reponse
        if not hmac.compare_digest(mdp, L.MDP):
            ATTENTE[ip] = maintenant + 2
            return L.json_rep(self, {"erreur": "mot de passe incorrect"}, 401)

        ATTENTE.pop(ip, None)
        biscuit = (f"atelier={L.jeton()}; Path=/; HttpOnly; Secure; "
                   "SameSite=Lax; Max-Age=2592000")
        L.json_rep(self, {"ok": True}, entetes={"Set-Cookie": biscuit})
