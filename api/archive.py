# -*- coding: utf-8 -*-
"""Archive zip d'un carrousel : les 5 photos et leurs textes."""
import io, zipfile
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        nom = parse_qs(urlparse(self.path).query).get("nom", [""])[0]
        if not nom.replace("_", "").replace("-", "").isalnum():
            return L.repondre(self, 400, "text/plain", "nom refuse")

        c, d = L.rest(f"carrousels?nom=eq.{nom}")
        if c != 200 or not isinstance(d, list) or not d:
            return L.repondre(self, 404, "text/plain", "introuvable")
        fiche = d[0]

        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w") as z:
            for i in range(1, 6):
                brut = L.lire_objet(f"{nom}/{i}.jpg")
                if brut:
                    z.writestr(f"{nom}/{i}.jpg", brut)
            textes = fiche.get("textes") or []
            z.writestr(f"{nom}/textes.txt",
                       "
".join(f"Photo {i+1} : {t}" for i, t in enumerate(textes)))
        L.repondre(self, 200, "application/zip", tampon.getvalue(),
                   {"Content-Disposition": f'attachment; filename="{nom}.zip"'})
