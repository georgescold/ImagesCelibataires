# -*- coding: utf-8 -*-
"""Liste des carrousels, avec les URL signees de leurs photos.

Deux URL signees par photo : la vignette, et la photo pleine taille. Toutes deux
sont servies par le CDN du stockage, a Paris : un telechargement ne passe plus
par une fonction, qui lisait l'image dans le stockage avant de la renvoyer —
treize allers-retours pour un « Tout telecharger ».
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

# Photos ajoutees en une fois par le bouton « Plus de photos ». Cinq, parce que
# les cinq textes a incruster tournent en boucle : un lot de cinq se poste tel
# quel comme un deuxieme carrousel de la meme personne.
LOT = 5

# Ce que l'interface lit d'une fiche. Le reste — plans des photos, signes
# particuliers — alourdissait chaque chargement sans jamais servir a l'ecran ;
# la description du visage n'est lue que pour savoir si la fiche est extensible.
CHAMPS = "nom,prenom,age,genre,metier,recherche,persona,textes,statut,favori,cree,visage"


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

        # Les compteurs des onglets ne dependent de rien : lus en meme temps que
        # la liste, plutot qu'apres elle.
        with ThreadPoolExecutor(2) as ex:
            comptage = ex.submit(L.rest, "carrousels?select=statut,favori")
            c, fiches = L.rest(f"carrousels?{filtre}&select={CHAMPS}&order=cree.desc")
            if c != 200 or not isinstance(fiches, list):
                return L.json_rep(self, {"erreur": f"base : {c} {fiches}"}, 500)

            noms = [f["nom"] for f in fiches]
            photos = {}
            if noms:
                liste = ",".join(f'"{n}"' for n in noms)
                c2, ph = L.rest(f"photos?carrousel=in.({liste})&select=carrousel,numero&order=numero")
                if c2 == 200 and isinstance(ph, list):
                    for p in ph:
                        photos.setdefault(p["carrousel"], []).append(p["numero"])

            # une seule signature pour toutes les images de la page
            signees = L.urls_signees(
                [f"{n}/vignettes/{k}.jpg" for n in noms for k in photos.get(n, [])]
                + [f"{n}/{k}.jpg" for n in noms for k in photos.get(n, [])])
            c3, tous = comptage.result()

        for f in fiches:
            nums = photos.get(f["nom"], [])
            f["photos"] = [f"{k}.jpg" for k in nums]
            f["vignettes"] = {str(k): signees.get(f"{f['nom']}/vignettes/{k}.jpg") for k in nums}
            f["pleines"] = {str(k): signees.get(f"{f['nom']}/{k}.jpg") for k in nums}
            f["archivee"] = f["statut"] == "archive" if archivees_ici is None else archivees_ici
            # sans description de visage, la fiche est trop ancienne pour etre etendue
            f["extensible"] = bool(f.pop("visage", None))

        if c3 == 200 and isinstance(tous, list):
            n_act = sum(1 for x in tous if x["statut"] == "a_poster")
            n_arc = sum(1 for x in tous if x["statut"] == "archive")
            n_fav = sum(1 for x in tous if x.get("favori") and x["statut"] != "corbeille")
        else:
            n_act = n_arc = n_fav = 0

        L.json_rep(self, {"femmes": fiches, "personas": L.PERSONAS, "lot": LOT,
                          "nb_actives": n_act, "nb_archivees": n_arc, "nb_favoris": n_fav})
