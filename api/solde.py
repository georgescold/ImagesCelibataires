# -*- coding: utf-8 -*-
"""Solde fal restant, pour l'afficher en direct dans la barre."""
import json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        cle = _os.environ.get("FAL_KEY", "")
        if not cle:
            return L.json_rep(self, {"erreur": "FAL_KEY absente"}, 500)
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                "https://rest.alpha.fal.ai/billing/user_balance",
                headers={"Authorization": "Key " + cle}), timeout=20)
            L.json_rep(self, {"solde": float(r.read().decode().strip())},
                       entetes={"Cache-Control": "no-store"})
        except (urllib.error.URLError, ValueError) as e:
            L.json_rep(self, {"erreur": str(e)[:120]}, 502)
