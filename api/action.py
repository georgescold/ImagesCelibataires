# -*- coding: utf-8 -*-
"""Archiver, restaurer, supprimer, mettre en favori : une colonne a changer."""
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

STATUTS = {"archiver": "archive", "restaurer": "a_poster", "supprimer": "corbeille"}
# le favori est independant du statut : une femme archivee peut rester un favori
FAVORIS = {"favori": True, "defavori": False}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        d = L.corps_json(self)
        nom, quoi = d.get("nom", ""), d.get("action", "")
        if quoi not in STATUTS and quoi not in FAVORIS:
            return L.json_rep(self, {"erreur": "action inconnue"}, 400)
        if not nom or not nom.replace("_", "").replace("-", "").isalnum():
            return L.json_rep(self, {"erreur": "nom refuse"}, 400)

        if quoi in FAVORIS:
            champ = {"favori": FAVORIS[quoi]}
        else:
            champ = {"statut": STATUTS[quoi]}
            if quoi == "supprimer":
                # un carrousel en corbeille ne doit plus compter dans les favoris
                champ["favori"] = False

        c, r = L.rest(f"carrousels?nom=eq.{nom}", "PATCH", champ, prefer="return=minimal")
        if c not in (200, 204):
            return L.json_rep(self, {"erreur": f"{c} {r}"}, 500)
        L.json_rep(self, dict({"ok": True, "nom": nom}, **champ))
