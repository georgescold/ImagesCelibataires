# -*- coding: utf-8 -*-
"""Avancement d'une generation, lu dans la table `jobs`."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import _lib as L


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        jid = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        if not jid:
            return L.json_rep(self, {"etat": "inconnu"})
        c, d = L.rest(f"jobs?id=eq.{jid}")
        if c == 200 and isinstance(d, list) and d:
            return L.json_rep(self, d[0])
        L.json_rep(self, {"etat": "inconnu"})
