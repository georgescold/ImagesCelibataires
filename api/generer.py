# -*- coding: utf-8 -*-
"""
Generation d'un carrousel en ligne, et ajout de photos a un carrousel existant.

Le travail est fait dans une seule invocation : cinq appels a fal enchaines,
environ 80 secondes, sous la limite de 300 s declaree dans vercel.json.
L'avancement est ecrit au fur et a mesure dans la table `jobs`, ce qui permet
au navigateur de le suivre en interrogeant /api/job pendant que celle-ci
tourne encore.

Le code de generation n'est pas duplique : on recree dans /tmp l'arborescence
qu'il attend, on le laisse ecrire ses fichiers, puis on televerse le resultat.

Les deux travaux partagent cette fonction plutot que d'en avoir chacun une :
le plan Hobby de Vercel plafonne a douze fonctions par deploiement, et le
projet en compte deja douze. Ce n'est pas qu'un pis-aller — etendre un profil
est une generation comme une autre, meme duree, meme /tmp, meme televersement.
Le corps de la requete porte `etendre: true` pour demander la seconde.
"""
import json, os, re, time, traceback
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

LOT = 5

# Une fonction Vercel est tuee a 300 s. On n'entame plus de photo au-dela de
# cette marge : ce qui est deja fait doit avoir le temps d'etre televerse,
# sinon la depense est perdue.
BUDGET = 235


def _maj(job_id, **champs):
    L.rest(f"jobs?id=eq.{job_id}", "PATCH", champs, prefer="return=minimal")


def _nom_libre(base):
    c, d = L.rest("carrousels?select=nom")
    pris = {x["nom"] for x in d} if c == 200 and isinstance(d, list) else set()
    nom, i = base, 2
    while nom in pris:
        nom, i = f"{base}_{i}", i + 1
    return nom


def _preparer_extension(nom, fiche, racine):
    """Recree dans /tmp la fiche et la photo de reference, et rend le numero a
    partir duquel numeroter les nouvelles photos. Rend None si la photo 1 est
    introuvable dans le stockage."""
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
        return None
    open(os.path.join(brut, "1.jpg"), "wb").write(donnees)

    c, ph = L.rest(f"photos?carrousel=eq.{nom}&select=numero&order=numero.desc&limit=1")
    dernier = ph[0]["numero"] if c == 200 and isinstance(ph, list) and ph else 0
    return dernier + 1


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        d = L.corps_json(self)
        return self._etendre(d) if d.get("etendre") else self._creer(d)

    # ------------------------------------------------------------- nouveau profil
    def _creer(self, d):
        age = max(30, min(70, int(d.get("age") or 45)))
        genre = "h" if d.get("genre") == "h" else "f"
        persona = d.get("persona") if d.get("persona") in L.PERSONAS else "discrete_nature"
        base = re.sub(r"[^a-z0-9_]", "", (d.get("nom") or "").lower()) \
            or f"{'homme' if genre == 'h' else 'femme'}{age}"
        nom = _nom_libre(base)

        job_id = self._ouvrir_job(nom)
        if not job_id:
            return
        L.json_rep(self, {"job": job_id, "nom": nom})

        def faire(journal):
            racine = L.preparer_tmp()
            import carrousel
            carrousel.build(nom, persona, age, journal=journal, genre=genre)
            meta = json.load(open(os.path.join(racine, "gen", nom, "meta.json"),
                                  encoding="utf-8"))
            L.televerser(nom, racine, meta, journal)
            L.rendre_registres(racine)

        self._travailler(job_id, faire)

    # ------------------------------------------------------- photos en plus
    def _etendre(self, d):
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

        job_id = self._ouvrir_job(nom)
        if not job_id:
            return
        L.json_rep(self, {"job": job_id, "nom": nom, "combien": combien})

        def faire(journal):
            debut = time.time()
            racine = L.preparer_tmp()
            depart = _preparer_extension(nom, fiche, racine)
            if depart is None:
                raise RuntimeError("photo 1 introuvable dans le stockage")
            import carrousel
            ajoutees = carrousel.ajouter(nom, combien, journal=journal, depart=depart,
                                         avant=debut + BUDGET)
            if ajoutees:
                neuve = json.load(open(os.path.join(racine, "gen", nom, "meta.json"),
                                       encoding="utf-8"))
                L.televerser(nom, racine, neuve, journal, numeros=ajoutees, creation=False)
            L.rendre_registres(racine)

        self._travailler(job_id, faire)

    # ------------------------------------------------------------------ commun
    def _ouvrir_job(self, nom):
        c, j = L.rest("jobs", "POST", {"nom": nom, "etat": "en cours", "lignes": []},
                      prefer="return=representation")
        job_id = j[0]["id"] if c in (200, 201) and isinstance(j, list) and j else None
        if not job_id:
            L.json_rep(self, {"erreur": f"job : {c} {j}"}, 500)
        return job_id

    def _travailler(self, job_id, faire):
        """La reponse est deja partie : on travaille en ecrivant l'avancement
        dans la table `jobs`, que le navigateur interroge pendant ce temps."""
        lignes = []

        def journal(ligne):
            lignes.append(str(ligne).rstrip())
            _maj(job_id, lignes=lignes)

        try:
            faire(journal)
            _maj(job_id, etat="fini", lignes=lignes)
        except BaseException as e:
            lignes.append(f"ECHEC : {e}")
            _maj(job_id, etat="erreur", lignes=lignes,
                 erreur=str(e) + "\n" + traceback.format_exc()[-900:])
