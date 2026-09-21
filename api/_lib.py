# -*- coding: utf-8 -*-
"""
Socle commun aux fonctions Vercel.

Trois responsabilites :
  - parler a Supabase (base et stockage), qui remplace le disque local ;
  - poser et verifier le cookie de session (mot de passe unique) ;
  - repliquer dans /tmp l'arborescence attendue par le code de generation.

Sur Vercel le systeme de fichiers est en lecture seule sauf /tmp, et il est
efface entre deux invocations : rien de durable ne peut y etre ecrit.
"""
import hashlib, hmac, json, os, time, urllib.request, urllib.error
from contextlib import contextmanager

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
BUCKET = "carrousels"

BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
CLE = os.environ.get("SUPABASE_SERVICE_KEY", "")
MDP = os.environ.get("ATELIER_MDP", "")
SECRET = os.environ.get("SESSION_SECRET", "") or CLE[:48]

PERSONAS = ["discrete_nature", "sportive_naturelle", "quarantenaire_filtres",
            "bobo_voyage", "fetarde"]

# --- Registres d'etat -------------------------------------------------------
#
# En local ce sont des fichiers de gen/. En ligne, /tmp s'efface entre deux
# invocations : il leur faut un endroit durable. Ils ont longtemps ete ecrits
# dans le bucket de photos — qui n'accepte QUE du image/jpeg. Chaque envoi etait
# refuse (415 invalid_mime_type) sans que personne le sache, et chaque
# generation en ligne repartait de registres vides : la regle des 40 prenoms,
# la carence des lieux, l'exclusion des poses deja jouees, la rotation des
# variantes de cartes n'ont jamais fonctionne en ligne. Ils vivent desormais
# dans la table `registres`, ou le JSON est chez lui.
#
# Chaque flux ne relit et ne renvoie QUE les registres qu'il modifie, sous
# verrou, le temps du tirage : cf. `registres()`.
REGISTRES_TIRAGE = ["_poses_utilisees.json", "_lieux_utilises.json",
                    "_prenoms_utilises.json", "_prenoms_h_utilises.json"]
REGISTRE_CARTES = "_variantes_cartes.json"


# ------------------------------------------------------------------ Supabase
def sb(chemin, methode="GET", corps=None, ctype="application/json", entetes=None):
    h = {"Authorization": f"Bearer {CLE}", "apikey": CLE, "User-Agent": UA}
    if corps is not None:
        h["Content-Type"] = ctype
    h.update(entetes or {})
    donnees = corps if isinstance(corps, (bytes, type(None))) else json.dumps(corps).encode()
    req = urllib.request.Request(BASE + chemin, data=donnees, headers=h, method=methode)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        brut = r.read()
        if entetes and entetes.get("_brut"):
            return r.status, brut
        t = brut.decode("utf-8", "ignore")
        return r.status, (json.loads(t) if t.strip().startswith(("{", "[")) else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:400]


def rest(chemin, methode="GET", corps=None, prefer=None):
    ent = {"Prefer": prefer} if prefer else None
    return sb("/rest/v1/" + chemin, methode, corps, entetes=ent)


def lire_objet(cible):
    h = {"Authorization": f"Bearer {CLE}", "apikey": CLE, "User-Agent": UA}
    req = urllib.request.Request(f"{BASE}/storage/v1/object/{BUCKET}/{cible}", headers=h)
    try:
        return urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError:
        return None


# Une photo ne pouvait etre ecrite qu'une fois ; depuis qu'on sait en refaire
# une seule, son adresse ne change pas mais son contenu si, et le CDN de
# Supabase servait encore l'ancienne. Un parametre ajoute a l'URL ne le
# contourne pas — mesure faite, ?r=12345 rend un HIT sur la meme entree. On
# borne donc la duree de cache au lieu d'essayer de la tromper.
CACHE_PHOTO = "max-age=60"


def ecrire_objet(cible, donnees, ctype="image/jpeg", cache=CACHE_PHOTO):
    c, _ = sb(f"/storage/v1/object/{BUCKET}/{cible}", "POST", donnees, ctype,
              {"x-upsert": "true", "cache-control": cache})
    return c in (200, 201)


def urls_signees(cibles, secondes=7200):
    """Signe plusieurs chemins en UN appel.

    Les signer un par un demandait 165 requetes enchainees pour 33 carrousels,
    soit 24 secondes de bibliotheque. Supabase accepte une liste.
    """
    if not cibles:
        return {}
    c, d = sb(f"/storage/v1/object/sign/{BUCKET}", "POST",
              {"expiresIn": secondes, "paths": list(cibles)})
    if c != 200 or not isinstance(d, list):
        return {}
    out = {}
    for item in d:
        chemin = (item.get("path") or "").lstrip("/")
        signee = item.get("signedURL") or item.get("signedUrl")
        if chemin and signee:
            out[chemin] = BASE + "/storage/v1" + signee
    return out


def url_signee(cible, secondes=3600):
    c, d = sb(f"/storage/v1/object/sign/{BUCKET}/{cible}", "POST",
              {"expiresIn": secondes})
    if c == 200 and isinstance(d, dict) and d.get("signedURL"):
        return BASE + "/storage/v1" + d["signedURL"]
    return None


# ------------------------------------------------------------------- session
def _signer(valeur):
    return hmac.new(SECRET.encode(), valeur.encode(), hashlib.sha256).hexdigest()[:32]


def jeton(duree=30 * 24 * 3600):
    exp = str(int(time.time()) + duree)
    return f"{exp}.{_signer(exp)}"


def jeton_valide(j):
    try:
        exp, sig = (j or "").split(".", 1)
    except ValueError:
        return False
    return (hmac.compare_digest(sig, _signer(exp))
            and int(exp) > time.time())


def cookie_de(entetes):
    brut = entetes.get("Cookie") or ""
    for morceau in brut.split(";"):
        if "=" in morceau:
            k, v = morceau.strip().split("=", 1)
            if k == "atelier":
                return v
    return ""


def authentifie(entetes):
    if not MDP:                      # pas de mot de passe configure : tout est ferme
        return False
    return jeton_valide(cookie_de(entetes))


# ------------------------------------------- arborescence de travail dans /tmp
def preparer_tmp():
    """Recree l'arborescence attendue par le code de generation.

    carrousel.py travaille en chemins relatifs sous `gen/`. On reconstitue
    donc ce repertoire dans /tmp et on s'y place. Les modules eux-memes restent
    lus depuis le paquet deploye. Les registres, eux, ne sont PAS charges ici :
    ils le sont sous verrou, au moment du tirage (cf. `registres()`).
    """
    import sys
    racine = "/tmp/atelier"
    os.makedirs(os.path.join(racine, "gen"), exist_ok=True)
    paquet = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen")
    if paquet not in sys.path:
        sys.path.insert(0, paquet)
    os.chdir(racine)
    return racine


# --------------------------------------------------------------------- verrous
def _horodatage(decalage=0):
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=decalage)).isoformat()


def horodatage_url(decalage=0):
    """Pour un filtre d'URL : le « + » de « +00:00 » y deviendrait une espace."""
    from urllib.parse import quote
    return quote(_horodatage(decalage))


def prendre_verrou(nom, attente=25, perime=30):
    """Pose le verrou `nom` : une ligne de la table `verrous`, dont la cle
    primaire refuse un second preneur. Rend False si on n'a pas pu l'obtenir a
    temps — on continue alors sans lui plutot que de faire echouer une
    generation payee. Un verrou pose depuis plus de `perime` secondes est leve
    d'office : c'est celui d'une fonction tuee en plein tirage."""
    import random as _r
    fin = time.time() + attente
    while True:
        c, _ = rest("verrous", "POST", {"nom": nom}, prefer="return=minimal")
        if c in (200, 201, 204):
            return True
        rest(f"verrous?nom=eq.{nom}&pris=lt.{horodatage_url(-perime)}", "DELETE", prefer="return=minimal")
        if time.time() > fin:
            return False
        time.sleep(0.25 + _r.random() * 0.35)


def rendre_verrou(nom):
    rest(f"verrous?nom=eq.{nom}", "DELETE", prefer="return=minimal")


@contextmanager
def verrou(nom):
    """`with verrou("x"):` — rendu meme si le bloc leve une exception."""
    tenu = prendre_verrou(nom)
    try:
        yield tenu
    finally:
        if tenu:
            rendre_verrou(nom)


@contextmanager
def registres(racine, noms, nom_verrou):
    """Le tirage (prenom, poses, lieux, variante de carte) en lecture-modification-
    ecriture exclusive : on prend le verrou, on relit ces registres en base, on
    laisse le code de generation les modifier dans /tmp, on les renvoie aussitot,
    puis on rend le verrou. Une seconde ou deux, au lieu de la generation entiere.

    Sans cela, deux generations lancees ensemble lisaient le meme etat : meme
    prenom possible pour les deux, et le second envoi ecrasait le premier."""
    import json as _json
    with verrou(nom_verrou):
        liste = ",".join(f'"{n}"' for n in noms)
        c, lignes = rest(f"registres?nom=in.({liste})&select=nom,contenu")
        lu = c == 200 and isinstance(lignes, list)
        depot = {l["nom"]: l["contenu"] for l in lignes} if lu else {}
        for nom in noms:
            local = os.path.join(racine, "gen", nom)
            if nom in depot:
                with open(local, "w", encoding="utf-8") as f:
                    _json.dump(depot[nom], f, ensure_ascii=False)
            elif lu and os.path.exists(local):
                os.remove(local)       # reliquat d'une invocation precedente sur cette machine
        yield
        if not lu:
            # Relecture ratee : le tirage s'est fait sans l'historique. Le renvoyer
            # remplacerait en base quarante prenoms par un seul — on s'en abstient.
            return
        maj = []
        for nom in noms:
            local = os.path.join(racine, "gen", nom)
            if os.path.exists(local):
                maj.append({"nom": nom, "contenu": _json.load(open(local, encoding="utf-8")),
                            "maj": _horodatage()})
        if maj:
            c, r = rest("registres?on_conflict=nom", "POST", maj,
                        prefer="resolution=merge-duplicates,return=minimal")
            if c not in (200, 201, 204):
                raise RuntimeError(f"registres non enregistres : {c} {str(r)[:160]}")


# ------------------------------------------------ televersement d'un carrousel
def televerser(nom, racine, meta, journal, numeros=None, creation=True):
    """Photos, vignettes et metadonnees vers Supabase.

    `numeros` : ne monter que ces photos ; None les prend toutes.
    `creation` : a la creation on ecrit la fiche entiere ; a l'extension on ne
    corrige QUE `slides`. La difference n'est pas cosmetique — un upsert sur une
    fiche existante remet les colonnes absentes du corps a leur valeur par
    defaut, ce qui sortirait la femme des archives et lui retirerait son favori.
    """
    import io, re
    from PIL import Image
    dossier = os.path.join(racine, "gen", nom)
    photos = sorted((f for f in os.listdir(dossier) if re.fullmatch(r"\d+\.jpg", f)),
                    key=lambda f: int(f[:-4]))
    if numeros is not None:
        garder = {int(n) for n in numeros}
        photos = [f for f in photos if int(f[:-4]) in garder]

    rates = []
    for f in photos:
        n = f[:-4]
        brut = open(os.path.join(dossier, f), "rb").read()
        im = Image.open(io.BytesIO(brut)).convert("RGB")
        im.thumbnail((320, 400), Image.LANCZOS)
        tampon = io.BytesIO()
        im.save(tampon, "JPEG", quality=72, optimize=True)
        if not ecrire_objet(f"{nom}/{f}", brut):
            rates.append(f)
        elif not ecrire_objet(f"{nom}/vignettes/{n}.jpg", tampon.getvalue()):
            rates.append(f"vignette {n}")
    if rates:
        journal(f"  ECHEC du televersement de : {', '.join(rates)}")
    journal(f"  {len(photos) - len(rates)} photos et vignettes televersees")

    def ecrire(chemin, methode, corps, quoi):
        """Une ecriture ratee doit se voir. Sans ce garde-fou, une contrainte
        de la base rejette une ligne, la fonction rend « televersee » et la
        photo existe dans le bucket sans jamais apparaitre dans la librairie."""
        c, r = rest(chemin, methode, corps, prefer=("resolution=merge-duplicates,return=minimal"
                                                    if methode == "POST" else "return=minimal"))
        if c not in (200, 201, 204):
            journal(f"  ECHEC {quoi} : {c} {str(r)[:200]}")
        return c in (200, 201, 204)

    # la photo 1 AVANT post-traitement : c'est elle qui servira de reference si
    # on ajoute des photos plus tard. Sans elle, l'extension repartirait de
    # l'image floutee, bruitee et deux fois recompressee. Renvoyee aussi quand
    # c'est la photo 1 qu'on vient de refaire : sinon les lots suivants
    # repartaient de l'ancien visage, que la bibliotheque ne montre plus.
    brute = os.path.join(racine, "gen", nom + "_raw", "1.jpg")
    if (creation or 1 in {int(f[:-4]) for f in photos}) and os.path.exists(brute):
        ecrire_objet(f"{nom}/brut/1.jpg", open(brute, "rb").read())

    if creation:
        fiche = {k: meta.get(k) for k in
                 ("nom", "genre", "prenom", "age", "metier", "recherche", "persona",
                  "textes", "visage", "signes", "slides")}
        fiche["statut"] = "a_poster"
        ecrire("carrousels?on_conflict=nom", "POST", fiche, "fiche")
    else:
        # La fiche en base a pu changer depuis notre lancement : un autre lot, une
        # autre reprise sur la meme personne, peut-etre dans une autre instance.
        # On la relit et on n'y remplace QUE nos photos, sous verrou — renvoyer
        # la copie lue au depart effacerait ce que les autres y ont ajoute.
        faites = {int(f[:-4]) for f in photos}
        miennes = [s for s in meta.get("slides", []) if s.get("n") in faites]
        with verrou(f"fiche-{nom}"):
            c, f = rest(f"carrousels?nom=eq.{nom}&select=slides")
            if c == 200 and isinstance(f, list) and f:
                fusion = sorted([s for s in (f[0].get("slides") or []) if s.get("n") not in faites]
                                + miennes, key=lambda s: s.get("n") or 0)
                ecrire(f"carrousels?nom=eq.{nom}", "PATCH", {"slides": fusion}, "slides de la fiche")
            else:
                journal(f"  ECHEC relecture de la fiche : {c} {str(f)[:160]}")

    lignes = []
    for f in photos:
        i = int(f[:-4])
        slide = next((s for s in meta.get("slides", []) if s.get("n") == i), {})
        textes = meta.get("textes") or []
        # au-dela de la cinquieme photo les textes reprennent au debut : la
        # personne n'a qu'une identite, et un second lot de cinq se poste tel quel
        texte = slide.get("texte") or (textes[(i - 1) % len(textes)] if textes else None)
        lignes.append({"carrousel": nom, "numero": i, "chemin": f"{nom}/{f}",
                       "texte": texte, "scene": slide.get("scene"), "lieu": slide.get("lieu")})
    if lignes and not ecrire("photos?on_conflict=carrousel,numero", "POST", lignes,
                             "lignes de photos"):
        # les images sont dans le bucket mais invisibles sans leur ligne :
        # mieux vaut le dire que de rendre un compte rassurant
        return 0
    return len(photos)


# ----------------------------------------------------------------- reponses
def repondre(h, code, ctype, corps, entetes=None):
    if isinstance(corps, str):
        corps = corps.encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(corps)))
    for k, v in (entetes or {}).items():
        h.send_header(k, v)
    h.end_headers()
    h.wfile.write(corps)


def json_rep(h, obj, code=200, entetes=None):
    repondre(h, code, "application/json; charset=utf-8",
             json.dumps(obj, ensure_ascii=False), entetes)


def refuser(h):
    json_rep(h, {"erreur": "non authentifie"}, 401)


def corps_json(h):
    n = int(h.headers.get("Content-Length", 0) or 0)
    if not n:
        return {}
    try:
        return json.loads(h.rfile.read(n) or b"{}")
    except json.JSONDecodeError:
        return {}
