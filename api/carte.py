# -*- coding: utf-8 -*-
"""
Carte de personnalite en ligne, pendant du bloc de l'atelier local.

Trois usages sur la meme fonction :
  GET  /api/carte?types=1          les 16 types, pour remplir le menu
  GET  /api/carte?fichier=x.jpg    l'image, depuis le bucket prive (&dl=1 : telechargement)
  POST /api/carte                  {"type": ..., "prenom": ...} -> dessine et range la carte

Le dessin n'est pas duplique : c'est gen/carte.py, le meme qu'en local. Deux
choses seulement changent en ligne.

  - Le disque est en lecture seule sauf /tmp. On recree donc l'arborescence
    attendue (_lib.preparer_tmp), on y dessine, puis on televerse dans le
    bucket sous `_cartes/`.
  - Le registre des variantes ne peut pas vivre a cote du code : il est
    telecharge du stockage au debut et renvoye a la fin, comme les registres
    de prenoms, poses et lieux. Sans ca chaque invocation repartirait de zero
    et ressortirait sans cesse les memes segments.

⚠️ Comme en local, la carte est INDEPENDANTE des carrousels (cf. gen/carte.py) :
elle s'ecrit dans son propre prefixe, jamais dans le dossier d'un carrousel.
"""
import os, re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(RACINE, "gen")
PREFIXE = "_cartes"                      # ou les cartes se rangent dans le bucket
FICHIER = re.compile(r"[A-Za-z0-9_-]{1,120}\.jpg")


def _module():
    """gen/carte.py, importe depuis le paquet deploye.

    Le dossier `cartes/` (avatars, blasons, polices, personnalites.json) est
    joint a la fonction par includeFiles : voir vercel.json. S'il manque,
    carte.donnees() leve SystemExit, d'ou les `except BaseException` plus bas.
    """
    if GEN not in _sys.path:
        _sys.path.insert(0, GEN)
    import carte
    return carte


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        q = parse_qs(urlparse(self.path).query)

        if q.get("types", ["0"])[0] == "1":
            try:
                types = _module().donnees()["types"]
            except BaseException as e:
                return L.json_rep(self, {"erreur": str(e)[:200]}, 500)
            return L.json_rep(self, {"types": [{"id": t["id"], "nom": t["nom"]} for t in types]},
                              entetes={"Cache-Control": "private, max-age=3600"})

        fichier = q.get("fichier", [""])[0]
        if not FICHIER.fullmatch(fichier):
            return L.repondre(self, 400, "text/plain", "requete invalide")
        donnees = L.lire_objet(f"{PREFIXE}/{fichier}")
        if donnees is None:
            return L.repondre(self, 404, "text/plain", "introuvable")
        # no-store : regenerer la meme carte doit montrer le nouveau tirage
        ent = {"Cache-Control": "no-store"}
        if q.get("dl", ["0"])[0] == "1":
            ent["Content-Disposition"] = f'attachment; filename="{fichier}"'
        L.repondre(self, 200, "image/jpeg", donnees, ent)

    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        d = L.corps_json(self)
        prenom = str(d.get("prenom") or "").strip()[:40]
        if not prenom:
            return L.json_rep(self, {"erreur": "Indique un prénom."}, 400)

        try:
            racine = L.preparer_tmp()
            os.environ["CARTE_REGISTRE"] = os.path.join(racine, "gen", "_variantes_cartes.json")
            carte = _module()          # carte.registre() relit CARTE_REGISTRE a chaque tirage
            ids = {t["id"] for t in carte.donnees()["types"]}
            type_id = d.get("type")
            if type_id not in ids:
                return L.json_rep(self, {"erreur": "Type de personnalité inconnu."}, 400)

            base = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{prenom}-{type_id}").strip("-").lower() or "carte"
            fichier = f"{base}.jpg"
            chemin = os.path.join(racine, "gen", "_cartes", fichier)
            # Le tirage de la variante relit et renvoie son SEUL registre, sous
            # verrou. Il renvoyait auparavant les cinq registres, y compris ceux
            # des generations, qu'il ecrasait avec la copie lue au debut.
            with L.registres(racine, [L.REGISTRE_CARTES], "cartes"):
                t = carte.rendre(type_id, prenom, chemin)

            if not L.ecrire_objet(f"{PREFIXE}/{fichier}", open(chemin, "rb").read()):
                return L.json_rep(self, {"erreur": "Carte dessinée mais pas enregistrée."}, 502)
        except BaseException as e:
            return L.json_rep(self, {"erreur": str(e)[:300]}, 500)

        L.json_rep(self, {"ok": True, "fichier": fichier, "nom": t["nom"],
                          "variante": t["variante"], "variantes": t["variantes"]})
