# -*- coding: utf-8 -*-
"""Sert une photo depuis le bucket prive, via une URL signee."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        q = parse_qs(urlparse(self.path).query)
        nom = q.get("nom", [""])[0]
        num = q.get("n", [""])[0]
        plein = q.get("plein", ["0"])[0] == "1"
        if not nom.replace("_", "").replace("-", "").isalnum() or not num.isdigit():
            return L.repondre(self, 400, "text/plain", "requete invalide")

        cible = f"{nom}/{num}.jpg" if plein else f"{nom}/vignettes/{num}.jpg"
        donnees = L.lire_objet(cible)
        if donnees is None and not plein:
            donnees = L.lire_objet(f"{nom}/{num}.jpg")
        if donnees is None:
            return L.repondre(self, 404, "text/plain", "introuvable")

        ent = {"Cache-Control": "private, max-age=3600"}
        if plein:
            ent["Content-Disposition"] = f'attachment; filename="{nom}_{num}.jpg"'
        L.repondre(self, 200, "image/jpeg", donnees, ent)
