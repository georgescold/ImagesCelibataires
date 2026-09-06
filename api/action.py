# -*- coding: utf-8 -*-
"""Archiver, restaurer ou supprimer : un simple changement de statut."""
from http.server import BaseHTTPRequestHandler
import _lib as L

STATUTS = {"archiver": "archive", "restaurer": "a_poster", "supprimer": "corbeille"}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        d = L.corps_json(self)
        nom, quoi = d.get("nom", ""), d.get("action", "")
        if quoi not in STATUTS:
            return L.json_rep(self, {"erreur": "action inconnue"}, 400)
        if not nom or not nom.replace("_", "").replace("-", "").isalnum():
            return L.json_rep(self, {"erreur": "nom refuse"}, 400)
        c, r = L.rest(f"carrousels?nom=eq.{nom}", "PATCH",
                      {"statut": STATUTS[quoi]}, prefer="return=minimal")
        if c not in (200, 204):
            return L.json_rep(self, {"erreur": f"{c} {r}"}, 500)
        L.json_rep(self, {"ok": True, "nom": nom, "statut": STATUTS[quoi]})
