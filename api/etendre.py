# -*- coding: utf-8 -*-
"""
Photos supplementaires pour une personne deja generee.

Meme principe que /api/generer : le travail tient dans une invocation, la
reponse part tout de suite et le navigateur suit l'avancement par /api/job.

La difference est qu'il n'y a rien a inventer — le visage, les signes
particuliers et les textes sont deja dans la fiche. On recree dans /tmp le
minimum dont `carrousel.ajouter` a besoin : la fiche en meta.json et la photo
qui sert de reference.
"""
import json, os, time, traceback
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

LOT = 5

# Une fonction Vercel est tuee a 300 s (vercel.json). On arrete d'entamer une
# photo au-dela de cette marge : ce qui est deja fait doit avoir le temps d'etre
# televerse, sinon la depense est perdue.
BUDGET = 235


def _maj(job_id, **champs):
    L.rest(f"jobs?id=eq.{job_id}", "PATCH", champs, prefer="return=minimal")


def _preparer(nom, fiche, racine):
    """Recree dans /tmp la fiche et la photo de reference, et rend le numero
    a partir duquel numeroter les nouvelles photos."""
    dossier = os.path.join(racine, "gen", nom)
    brut = os.path.join(racine, "gen", nom + "_raw")
    os.makedirs(dossier, exist_ok=True)
    os.makedirs(brut, exist_ok=True)

    meta = {k: fiche.get(k) for k in
            ("nom", "genre", "prenom", "age", "metier", "recherche", "persona",
             "textes", "visage", "signes", "slides")}
    json.dump(meta, open(os.path.join(dossier, "meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # la photo 1 d'avant post-traitement si elle existe, sinon celle qui est
    # publiee — les carrousels d'avant cette version n'ont que la seconde
    donnees = L.lire_objet(f"{nom}/brut/1.jpg") or L.lire_objet(f"{nom}/1.jpg")
    if not donnees:
        return meta, None
    open(os.path.join(brut, "1.jpg"), "wb").write(donnees)

    c, ph = L.rest(f"photos?carrousel=eq.{nom}&select=numero&order=numero.desc&limit=1")
    dernier = ph[0]["numero"] if c == 200 and isinstance(ph, list) and ph else 0
    return meta, dernier + 1


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)

        d = L.corps_json(self)
        nom = d.get("nom", "")
        if not nom or not nom.replace("_", "").replace("-", "").isalnum():
            return L.json_rep(self, {"erreur": "nom refuse"}, 400)
        combien = max(1, min(10, int(d.get("combien") or LOT)))

        c, fiches = L.rest(f"carrousels?nom=eq.{nom}")
        if c != 200 or not isinstance(fiches, list) or not fiches:
            return L.json_rep(self, {"erreur": "carrousel introuvable"}, 404)
        fiche = fiches[0]
        if not fiche.get("visage"):
            return L.json_rep(self, {"erreur": "fiche trop ancienne : elle ne contient pas "
                                               "la description du visage"}, 409)

        c, j = L.rest("jobs", "POST", {"nom": nom, "etat": "en cours", "lignes": []},
                      prefer="return=representation")
        job_id = j[0]["id"] if c in (200, 201) and isinstance(j, list) and j else None
        if not job_id:
            return L.json_rep(self, {"erreur": f"job : {c} {j}"}, 500)

        # la reponse part tout de suite, le travail continue dans cette invocation
        L.json_rep(self, {"job": job_id, "nom": nom, "combien": combien})

        lignes = []

        def journal(ligne):
            lignes.append(str(ligne).rstrip())
            _maj(job_id, lignes=lignes)

        depart_horloge = time.time()
        try:
            racine = L.preparer_tmp()
            meta, depart = _preparer(nom, fiche, racine)
            if depart is None:
                raise RuntimeError("photo 1 introuvable dans le stockage")
            import carrousel
            ajoutees = carrousel.ajouter(nom, combien, journal=journal, depart=depart,
                                         avant=depart_horloge + BUDGET)
            if ajoutees:
                neuve = json.load(open(os.path.join(racine, "gen", nom, "meta.json"),
                                       encoding="utf-8"))
                L.televerser(nom, racine, neuve, journal, numeros=ajoutees, creation=False)
            L.rendre_registres(racine)
            _maj(job_id, etat="fini", lignes=lignes)
        except BaseException as e:
            lignes.append(f"ECHEC : {e}")
            _maj(job_id, etat="erreur", lignes=lignes,
                 erreur=str(e) + "\n" + traceback.format_exc()[-900:])
