# -*- coding: utf-8 -*-
"""
Sauvegarde des carrousels vers Supabase : photos dans le bucket `carrousels`,
metadonnees dans les tables `carrousels` et `photos`.

Usage :
    python gen/sauvegarde.py            # envoie tout ce qui manque
    python gen/sauvegarde.py <nom>      # un seul carrousel
    python gen/sauvegarde.py --etat     # ce qui est deja en ligne

Idempotent : un carrousel deja envoye n'est pas renvoye, sauf si ses photos
ont change sur le disque.
"""
import json, os, sys, urllib.request, urllib.error

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
BUCKET = "carrousels"


def env():
    chemin = os.path.join(RACINE, ".env")
    if not os.path.exists(chemin):
        raise SystemExit("Fichier .env introuvable a la racine du projet.")
    d = {}
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.strip()
        if "=" in ligne and not ligne.startswith("#"):
            k, v = ligne.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    for requis in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if requis not in d:
            raise SystemExit(f"{requis} absent du .env")
    return d


E = env()
BASE = E["SUPABASE_URL"]
CLE = E["SUPABASE_SERVICE_KEY"]


def _appel(url, methode="GET", corps=None, ctype="application/json", entetes=None):
    h = {"Authorization": f"Bearer {CLE}", "apikey": CLE, "User-Agent": UA}
    if corps is not None:
        h["Content-Type"] = ctype
    h.update(entetes or {})
    donnees = corps if isinstance(corps, (bytes, type(None))) else json.dumps(corps).encode()
    req = urllib.request.Request(url, data=donnees, headers=h, method=methode)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        brut = r.read().decode("utf-8", "ignore")
        return r.status, (json.loads(brut) if brut.strip().startswith(("{", "[")) else brut)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:300]


def envoyer_photo(nom, numero, chemin):
    """Depose une photo dans le bucket. upsert = on ecrase si elle existe deja."""
    cible = f"{nom}/{numero}.jpg"
    code, rep = _appel(f"{BASE}/storage/v1/object/{BUCKET}/{cible}", "POST",
                       open(chemin, "rb").read(), "image/jpeg",
                       {"x-upsert": "true"})
    return code in (200, 201), cible, rep


def enregistrer(meta, statut):
    """Insere ou met a jour la fiche et ses 5 photos."""
    fiche = {
        "nom": meta["nom"], "genre": meta.get("genre", "f"),
        "prenom": meta.get("prenom"), "age": meta.get("age"),
        "metier": meta.get("metier"), "recherche": meta.get("recherche"),
        "persona": meta.get("persona"), "textes": meta.get("textes", []),
        "visage": meta.get("visage"), "signes": meta.get("signes"),
        "slides": meta.get("slides", []), "statut": statut,
    }
    code, rep = _appel(f"{BASE}/rest/v1/carrousels?on_conflict=nom", "POST", fiche,
                       entetes={"Prefer": "resolution=merge-duplicates,return=minimal"})
    if code not in (200, 201, 204):
        return False, f"fiche : {code} {rep}"

    lignes = []
    for i, ph in enumerate(meta["photos"], start=1):
        slide = next((s for s in meta.get("slides", []) if s.get("n") == i), {})
        lignes.append({
            "carrousel": meta["nom"], "numero": i,
            "chemin": f"{meta['nom']}/{i}.jpg",
            "texte": (meta.get("textes") or [None] * 5)[i - 1] if len(meta.get("textes") or []) >= i else None,
            "scene": slide.get("scene"), "lieu": slide.get("lieu"),
        })
    code, rep = _appel(f"{BASE}/rest/v1/photos?on_conflict=carrousel,numero", "POST", lignes,
                       entetes={"Prefer": "resolution=merge-duplicates,return=minimal"})
    if code not in (200, 201, 204):
        return False, f"photos : {code} {rep}"
    return True, "ok"


def deja_en_ligne():
    code, rep = _appel(f"{BASE}/rest/v1/carrousels?select=nom,statut")
    return {r["nom"]: r["statut"] for r in rep} if code == 200 and isinstance(rep, list) else {}


def sauvegarder(cibles=None, verbeux=True):
    sys.path.insert(0, os.path.join(RACINE, "gen"))
    import serveur

    lot = [(m, "a_poster") for m in serveur.dossiers()]
    lot += [(m, "archive") for m in serveur.dossiers(True)]
    if cibles:
        lot = [(m, s) for m, s in lot if m["nom"] in cibles]

    en_ligne = deja_en_ligne()
    envoyes = ignores = echecs = 0
    for meta, statut in lot:
        nom = meta["nom"]
        if nom in en_ligne and not cibles:
            ignores += 1
            continue
        rep = serveur.dossier_femme(nom)
        ok_photos = True
        for i, ph in enumerate(meta["photos"], start=1):
            ok, cible, rep_h = envoyer_photo(nom, i, os.path.join(rep, ph))
            if not ok:
                ok_photos = False
                if verbeux:
                    print(f"  ECHEC photo {cible} : {rep_h}")
                break
        if not ok_photos:
            echecs += 1
            continue
        ok, msg = enregistrer(meta, statut)
        if ok:
            envoyes += 1
            if verbeux:
                print(f"  ok  {nom}  ({meta.get('prenom')}, {meta.get('age')} ans, {len(meta['photos'])} photos)")
        else:
            echecs += 1
            if verbeux:
                print(f"  ECHEC {nom} : {msg}")
    return envoyes, ignores, echecs


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--etat" in sys.argv:
        d = deja_en_ligne()
        print(f"{len(d)} carrousel(s) en ligne")
        for nom, st in sorted(d.items()):
            print(f"  {nom:24} {st}")
    else:
        e, i, x = sauvegarder(args or None)
        print(f"\n{e} envoye(s), {i} deja en ligne, {x} echec(s)")
