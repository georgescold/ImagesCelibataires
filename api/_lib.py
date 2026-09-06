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

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
BUCKET = "carrousels"

BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
CLE = os.environ.get("SUPABASE_SERVICE_KEY", "")
MDP = os.environ.get("ATELIER_MDP", "")
SECRET = os.environ.get("SESSION_SECRET", "") or CLE[:48]

PERSONAS = ["discrete_nature", "sportive_naturelle", "quarantenaire_filtres",
            "bobo_voyage", "fetarde"]

# les registres d'etat vivaient dans des fichiers ; en ligne ils sont
# dans le stockage, sinon ils disparaitraient a chaque invocation
REGISTRES = ["_poses_utilisees.json", "_lieux_utilises.json",
             "_prenoms_utilises.json", "_prenoms_h_utilises.json"]


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


def ecrire_objet(cible, donnees, ctype="image/jpeg"):
    c, _ = sb(f"/storage/v1/object/{BUCKET}/{cible}", "POST", donnees, ctype,
              {"x-upsert": "true"})
    return c in (200, 201)


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
    donc ce repertoire dans /tmp, on y depose les registres telecharges
    depuis le stockage, et on s'y place. Les modules eux-memes restent lus
    depuis le paquet deploye.
    """
    import shutil, sys
    racine = "/tmp/atelier"
    os.makedirs(os.path.join(racine, "gen"), exist_ok=True)
    paquet = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen")
    if paquet not in sys.path:
        sys.path.insert(0, paquet)
    for nom in REGISTRES:
        contenu = lire_objet(f"_registres/{nom}")
        if contenu:
            open(os.path.join(racine, "gen", nom), "wb").write(contenu)
    os.chdir(racine)
    return racine


def rendre_registres(racine):
    """Renvoie les registres au stockage : sans cela, deux generations
    successives rejoueraient les memes poses et les memes lieux."""
    for nom in REGISTRES:
        p = os.path.join(racine, "gen", nom)
        if os.path.exists(p):
            ecrire_objet(f"_registres/{nom}", open(p, "rb").read(), "application/json")


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
