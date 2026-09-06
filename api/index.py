# -*- coding: utf-8 -*-
"""Sert l'atelier si la session est ouverte, la page de connexion sinon."""
import os
from http.server import BaseHTTPRequestHandler
import _lib as L

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _page(nom):
    for base in (RACINE, os.getcwd(), "/var/task"):
        p = os.path.join(base, "web", nom)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        nom = "app.html" if L.authentifie(self.headers) else "connexion.html"
        html = _page(nom)
        if html is None:
            return L.repondre(self, 500, "text/plain; charset=utf-8",
                              f"page {nom} introuvable dans le paquet deploye")
        L.repondre(self, 200, "text/html; charset=utf-8", html,
                   {"Cache-Control": "no-store"})
