# -*- coding: utf-8 -*-
"""
Generation d'un carrousel en ligne.

Le travail est fait dans une seule invocation : cinq appels a fal enchaines,
environ 80 secondes, sous la limite de 300 s declaree dans vercel.json.
L'avancement est ecrit au fur et a mesure dans la table `jobs`, ce qui permet
au navigateur de le suivre en interrogeant /api/job pendant que celle-ci
tourne encore.

Le code de generation n'est pas duplique : on recree dans /tmp l'arborescence
qu'il attend, on le laisse ecrire ses fichiers, puis on televerse le resultat.
"""
import io, json, os, re, traceback
from http.server import BaseHTTPRequestHandler
import _lib as L


def _maj(job_id, **champs):
    L.rest(f"jobs?id=eq.{job_id}", "PATCH", champs, prefer="return=minimal")


def _nom_libre(base):
    c, d = L.rest("carrousels?select=nom")
    pris = {x["nom"] for x in d} if c == 200 and isinstance(d, list) else set()
    nom, i = base, 2
    while nom in pris:
        nom, i = f"{base}_{i}", i + 1
    return nom


def _televerser(nom, racine, meta, journal):
    """Photos, vignettes et metadonnees vers Supabase."""
    from PIL import Image
    dossier = os.path.join(racine, "gen", nom)
    photos = sorted(f for f in os.listdir(dossier) if re.fullmatch(r"\d+\.jpg", f))

    for f in photos:
        n = f[:-4]
        brut = open(os.path.join(dossier, f), "rb").read()
        L.ecrire_objet(f"{nom}/{f}", brut)
        im = Image.open(io.BytesIO(brut)).convert("RGB")
        im.thumbnail((320, 400), Image.LANCZOS)
        tampon = io.BytesIO()
        im.save(tampon, "JPEG", quality=72, optimize=True)
        L.ecrire_objet(f"{nom}/vignettes/{n}.jpg", tampon.getvalue())
    journal(f"  {len(photos)} photos et vignettes televersees")

    fiche = {k: meta.get(k) for k in
             ("nom", "genre", "prenom", "age", "metier", "recherche", "persona",
              "textes", "visage", "signes", "slides")}
    fiche["statut"] = "a_poster"
    L.rest("carrousels?on_conflict=nom", "POST", fiche,
           prefer="resolution=merge-duplicates,return=minimal")

    lignes = []
    for f in photos:
        i = int(f[:-4])
        slide = next((s for s in meta.get("slides", []) if s.get("n") == i), {})
        textes = meta.get("textes") or []
        lignes.append({"carrousel": nom, "numero": i, "chemin": f"{nom}/{f}",
                       "texte": textes[i - 1] if len(textes) >= i else None,
                       "scene": slide.get("scene"), "lieu": slide.get("lieu")})
    L.rest("photos?on_conflict=carrousel,numero", "POST", lignes,
           prefer="resolution=merge-duplicates,return=minimal")
    return len(photos)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)

        d = L.corps_json(self)
        age = max(30, min(70, int(d.get("age") or 45)))
        genre = "h" if d.get("genre") == "h" else "f"
        persona = d.get("persona") if d.get("persona") in L.PERSONAS else "discrete_nature"
        base = re.sub(r"[^a-z0-9_]", "", (d.get("nom") or "").lower()) \
            or f"{'homme' if genre == 'h' else 'femme'}{age}"
        nom = _nom_libre(base)

        c, j = L.rest("jobs", "POST", {"nom": nom, "etat": "en cours", "lignes": []},
                      prefer="return=representation")
        job_id = j[0]["id"] if c in (200, 201) and isinstance(j, list) and j else None
        if not job_id:
            return L.json_rep(self, {"erreur": f"job : {c} {j}"}, 500)

        # la reponse part tout de suite : le navigateur suit l'avancement
        # par /api/job pendant que cette invocation continue de tourner
        L.json_rep(self, {"job": job_id, "nom": nom})

        lignes = []

        def journal(ligne):
            lignes.append(str(ligne).rstrip())
            _maj(job_id, lignes=lignes)

        try:
            racine = L.preparer_tmp()
            import carrousel
            carrousel.build(nom, persona, age, journal=journal, genre=genre)
            meta = json.load(open(os.path.join(racine, "gen", nom, "meta.json"),
                                  encoding="utf-8"))
            n = _televerser(nom, racine, meta, journal)
            L.rendre_registres(racine)
            _maj(job_id, etat="fini", lignes=lignes)
        except Exception as e:
            lignes.append(f"ECHEC : {e}")
            _maj(job_id, etat="erreur", lignes=lignes,
                 erreur=str(e) + "\n" + traceback.format_exc()[-900:])
