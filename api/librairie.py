# -*- coding: utf-8 -*-
"""Liste des carrousels, avec les URL signees de leurs vignettes."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

# Photos ajoutees en une fois par le bouton « Plus de photos ». Cinq, parce que
# les cinq textes a incruster tournent en boucle : un lot de cinq se poste tel
# quel comme un deuxieme carrousel de la meme personne.
LOT = 5


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        q = parse_qs(urlparse(self.path).query)

        if q.get("favoris", ["0"])[0] == "1":
            # les favoris sont une categorie a part : ils melangent a poster et
            # archivees, et n'excluent que la corbeille
            filtre = "favori=is.true&statut=neq.corbeille"
            archivees_ici = None
        else:
            statut = "archive" if q.get("archives", ["0"])[0] == "1" else "a_poster"
            filtre = f"statut=eq.{statut}"
            archivees_ici = statut == "archive"

        c, fiches = L.rest(f"carrousels?{filtre}&order=cree.desc")
        if c != 200 or not isinstance(fiches, list):
            return L.json_rep(self, {"erreur": f"base : {c} {fiches}"}, 500)

        noms = [f["nom"] for f in fiches]
        photos = {}
        if noms:
            liste = ",".join(f'"{n}"' for n in noms)
            c2, ph = L.rest(f"photos?carrousel=in.({liste})&order=numero")
            if c2 == 200 and isinstance(ph, list):
                for p in ph:
                    photos.setdefault(p["carrousel"], []).append(p)

        # une seule signature pour toutes les vignettes de la page
        chemins = [f"{n}/vignettes/{p['numero']}.jpg"
                   for n in noms for p in photos.get(n, [])]
        signees = L.urls_signees(chemins)

        for f in fiches:
            f["photos"] = [str(p["numero"]) + ".jpg" for p in photos.get(f["nom"], [])]
            f["vignettes"] = {str(p["numero"]): signees.get(f"{f['nom']}/vignettes/{p['numero']}.jpg")
                              for p in photos.get(f["nom"], [])}
            f["archivee"] = f["statut"] == "archive" if archivees_ici is None else archivees_ici
            # sans description de visage, la fiche est trop ancienne pour etre etendue
            f["extensible"] = bool(f.get("visage"))

        c3, tous = L.rest("carrousels?select=statut,favori")
        if c3 == 200 and isinstance(tous, list):
            n_act = sum(1 for x in tous if x["statut"] == "a_poster")
            n_arc = sum(1 for x in tous if x["statut"] == "archive")
            n_fav = sum(1 for x in tous if x.get("favori") and x["statut"] != "corbeille")
        else:
            n_act = n_arc = n_fav = 0

        L.json_rep(self, {"femmes": fiches, "personas": L.PERSONAS, "lot": LOT,
                          "nb_actives": n_act, "nb_archivees": n_arc, "nb_favoris": n_fav})
