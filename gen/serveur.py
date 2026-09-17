# -*- coding: utf-8 -*-
"""
Interface locale : generation + librairie des femmes generees.

Lancer :  python gen/serveur.py
Puis ouvrir http://localhost:8420

Serveur en bibliotheque standard uniquement (rien a installer).
La cle fal ne quitte jamais la machine : elle reste dans runner.py.
"""
import json, os, re, sys, threading, traceback, uuid, io, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RACINE)
sys.path.insert(0, os.path.join(RACINE, "gen"))

PORT = 8420
JOBS = {}          # id -> {"etat":..., "lignes":[...], "nom":..., "erreur":...}
VERROU = threading.Lock()
PERSONAS = ["discrete_nature", "sportive_naturelle", "quarantenaire_filtres", "bobo_voyage", "fetarde"]
ARCHIVES = os.path.join("gen", "_archives")
CORBEILLE = os.path.join("gen", "_corbeille")
CARTES_SORTIE = os.path.join("gen", "_cartes")   # cartes de personnalite generees
FAVORIS = os.path.join("gen", "_favoris.json")   # simple liste de noms

# Photos ajoutees en une fois par le bouton « Plus de photos ». Cinq, parce que
# les cinq textes a incruster tournent en boucle : un lot de cinq se poste tel
# quel comme un deuxieme carrousel de la meme personne.
LOT_SUPPLEMENTAIRE = 5

# Le nom de dossier arrive du navigateur. Sans ce garde-fou, un nom comme
# "../../.." sortirait de l'arborescence : on n'accepte que des noms simples.
NOM_VALIDE = re.compile(r"[A-Za-z0-9_-]{1,80}")


def dossier_femme(nom):
    """Chemin du carrousel, qu'il soit actif ou archive. None si le nom est refuse."""
    if not NOM_VALIDE.fullmatch(nom or ""):
        return None
    for base in ("gen", ARCHIVES):
        rep = os.path.join(base, nom)
        if os.path.isdir(rep):
            return rep
    return None


# ----------------------------------------------------------------- favoris
def charger_favoris():
    """Les favoris vivent dans leur propre fichier, pas dans les meta.json :
    un carrousel genere avant l'interface n'a pas de meta.json, et on veut
    pouvoir le mettre en favori quand meme."""
    if os.path.exists(FAVORIS):
        try:
            return set(json.load(open(FAVORIS, encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def sauver_favoris(noms):
    json.dump(sorted(noms), open(FAVORIS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


# --------------------------------------------------------------- librairie
def dossiers(archivees=False):
    """Carrousels du disque, du plus recent au plus ancien.
    `archivees` bascule entre le dossier de travail et gen/_archives."""
    base = ARCHIVES if archivees else "gen"
    aimes = charger_favoris()
    out = []
    if not os.path.isdir(base):
        return out
    for nom in os.listdir(base):
        rep = os.path.join(base, nom)
        if not os.path.isdir(rep) or nom.endswith("_raw") or nom.startswith("_") or nom in ("__pycache__", ".vignettes"):
            continue
        photos = sorted(f for f in os.listdir(rep) if re.fullmatch(r"\d+\.jpg", f))
        if not photos:
            continue
        meta_p = os.path.join(rep, "meta.json")
        if os.path.exists(meta_p):
            meta = json.load(open(meta_p, encoding="utf-8"))
        else:
            meta = retro_meta(nom, len(photos))
        meta["nom"] = nom
        meta["photos"] = photos
        meta["mtime"] = os.path.getmtime(rep)
        meta["archivee"] = archivees
        meta["favori"] = nom in aimes
        # un carrousel sans description de visage ne peut pas etre etendu :
        # le bouton doit le savoir avant de proposer une depense
        meta["extensible"] = bool(meta.get("visage"))
        out.append(meta)
    out.sort(key=lambda m: m["mtime"], reverse=True)
    return out


def dossiers_favoris():
    """Les favoris, a poster et archives confondus : c'est une categorie a part,
    pas un filtre de l'onglet courant."""
    aimes = charger_favoris()
    out = [f for f in dossiers() + dossiers(True) if f["nom"] in aimes]
    out.sort(key=lambda m: m["mtime"], reverse=True)
    return out


def retro_meta(nom, n):
    """Metadonnees reconstituees pour les carrousels generes avant l'interface."""
    import random
    from identite import identite
    m = re.search(r"(\d{2})$", nom)
    age = int(m.group(1)) if m and 30 <= int(m.group(1)) <= 70 else 45
    ident = identite(age, random.Random(nom), memoriser=False)   # deterministe, sans effet de bord
    return {"age": age, "persona": "?", "prenom": ident["prenom"], "metier": ident["metier"],
            "recherche": ident["recherche"], "textes": ident["textes"], "slides": [], "cree": "",
            "retro": True}


# --------------------------------------------------------------- vignettes
def vignette(nom, fichier):
    """Chemin d'une vignette 320 px, fabriquee une seule fois puis relue du disque.
    La librairie affichait 162 photos pleine resolution, soit ~14 Mo par
    ouverture de page : le navigateur mettait dix secondes a devenir utilisable."""
    rep = dossier_femme(nom)
    if not rep:
        return None
    src = os.path.join(rep, fichier)
    if not os.path.exists(src):
        return None
    cache = os.path.join(rep, ".vignettes")
    dst = os.path.join(cache, fichier)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return dst
    os.makedirs(cache, exist_ok=True)
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.thumbnail((320, 400), Image.LANCZOS)
    im.save(dst, "JPEG", quality=72, optimize=True)
    return dst


# --------------------------------------------------------------- generation
def lancer(job_id, travail):
    """Execute `travail(noter)` dans un thread. Le journal passe par un canal
    explicite : on ne touche jamais a sys.stdout, qui est global au processus et
    donc partage avec le serveur HTTP."""
    j = JOBS[job_id]

    def noter(ligne):
        with VERROU:
            j["lignes"].append(str(ligne).rstrip())

    try:
        travail(noter)
        j["etat"] = "fini"
    except BaseException as e:      # SystemExit compris : carrousel.py s'en sert
        noter(f"ECHEC : {e}")
        j["etat"] = "erreur"
        j["erreur"] = str(e) + chr(10) + traceback.format_exc()[-900:]


def en_tache(nom, travail):
    """Cree le job et demarre le thread. Retourne l'identifiant a suivre."""
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {"etat": "en cours", "lignes": [], "nom": nom, "erreur": None}
    threading.Thread(target=lancer, args=(job_id, travail), daemon=True).start()
    return job_id


# --------------------------------------------------------------- HTTP
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envoyer(self, code, ctype, corps, entetes=None):
        if isinstance(corps, str):
            corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corps)))
        for k, v in (entetes or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corps)

    def _json(self, obj, code=200):
        self._envoyer(code, "application/json; charset=utf-8",
                      json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        chemin = unquote(urlparse(self.path).path)

        if chemin == "/":
            return self._envoyer(200, "text/html; charset=utf-8", page())

        if chemin == "/api/librairie":
            q = urlparse(self.path).query
            if q == "favoris=1":
                femmes = dossiers_favoris()
            else:
                femmes = dossiers(q == "archives=1")
            return self._json({"femmes": femmes, "personas": PERSONAS,
                               "nb_actives": len(dossiers()), "nb_archivees": len(dossiers(True)),
                               "nb_favoris": len(charger_favoris()), "lot": LOT_SUPPLEMENTAIRE})

        if chemin == "/api/solde":
            try:
                import runner
                return self._json({"solde": runner.balance()})
            except Exception as e:
                return self._json({"erreur": str(e)[:120]}, 502)

        if chemin == "/api/types":
            # Les 16 types de personnalite, pour le bloc « Carte de personnalite ».
            try:
                import carte
                return self._json({"types": [{"id": t["id"], "nom": t["nom"]} for t in carte.donnees()["types"]]})
            except BaseException as e:  # SystemExit compris : cartes/ absent
                return self._json({"erreur": str(e)[:200]}, 500)

        m = re.fullmatch(r"/(carte|carte-dl)/([A-Za-z0-9_-]{1,120}\.jpg)", chemin)
        if m:
            mode, fichier = m.groups()
            p = os.path.join(CARTES_SORTIE, fichier)
            if not os.path.exists(p):
                return self._envoyer(404, "text/plain", "introuvable")
            ent = {"Cache-Control": "no-store"}
            if mode == "carte-dl":
                ent["Content-Disposition"] = f'attachment; filename="{fichier}"'
            return self._envoyer(200, "image/jpeg", open(p, "rb").read(), ent)

        if chemin.startswith("/api/job/"):
            j = JOBS.get(chemin.rsplit("/", 1)[1])
            return self._json(j or {"etat": "inconnu"})

        m = re.fullmatch(r"/vignette/([^/]+)/(\d+\.jpg)", chemin)
        if m:
            p = vignette(*m.groups())
            if not p:
                return self._envoyer(404, "text/plain", "introuvable")
            return self._envoyer(200, "image/jpeg", open(p, "rb").read(),
                                 {"Cache-Control": "max-age=86400"})

        m = re.fullmatch(r"/(photo|dl)/([^/]+)/(\d+\.jpg)", chemin)
        if m:
            mode, nom, fichier = m.groups()
            rep = dossier_femme(nom)
            p = os.path.join(rep, fichier) if rep else ""
            if not p or not os.path.exists(p):
                return self._envoyer(404, "text/plain", "introuvable")
            ent = {}
            if mode == "dl":
                ent["Content-Disposition"] = f'attachment; filename="{nom}_{fichier}"'
            return self._envoyer(200, "image/jpeg", open(p, "rb").read(), ent)

        m = re.fullmatch(r"/zip/([^/]+)", chemin)
        if m:
            nom = m.group(1)
            rep = dossier_femme(nom)
            if not rep:
                return self._envoyer(404, "text/plain", "introuvable")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for f in sorted(os.listdir(rep)):
                    if re.fullmatch(r"\d+\.jpg", f) or f == "meta.json":
                        z.write(os.path.join(rep, f), f"{nom}/{f}")
                fem = next((x for x in dossiers() + dossiers(True) if x["nom"] == nom), None)
                if fem and fem["textes"]:
                    # au-dela de la cinquieme photo les textes reprennent au debut :
                    # un carrousel etendu a dix photos se poste en deux lots de cinq
                    t = fem["textes"]
                    z.writestr(f"{nom}/textes.txt", "\n".join(
                        f"Photo {int(p[:-4])} : {t[(int(p[:-4]) - 1) % len(t)]}"
                        for p in sorted(fem["photos"], key=lambda p: int(p[:-4]))))
            return self._envoyer(200, "application/zip", buf.getvalue(),
                                 {"Content-Disposition": f'attachment; filename="{nom}.zip"'})

        return self._envoyer(404, "text/plain", "404")

    def do_POST(self):
        route = urlparse(self.path).path

        if route == "/api/carte":
            # Carte de personnalite, dessinee localement : gratuite et instantanee.
            # ⚠️ Independante des carrousels (cf. gen/carte.py) : elle s'ecrit dans
            # gen/_cartes/, jamais dans le dossier d'un carrousel.
            n = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(n) or b"{}") or {}
            prenom = str(d.get("prenom") or "").strip()[:40]
            if not prenom:
                return self._json({"erreur": "Indique un prénom."}, 400)
            try:
                import carte
                ids = {t["id"] for t in carte.donnees()["types"]}
                type_id = d.get("type")
                if type_id not in ids:
                    return self._json({"erreur": "Type de personnalité inconnu."}, 400)
                base = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{prenom}-{type_id}").strip("-").lower() or "carte"
                fichier = f"{base}.jpg"
                os.makedirs(CARTES_SORTIE, exist_ok=True)
                t = carte.rendre(type_id, prenom, os.path.join(CARTES_SORTIE, fichier))
                return self._json({"ok": True, "fichier": fichier, "nom": t["nom"],
                                   "variante": t["variante"], "variantes": t["variantes"]})
            except BaseException as e:
                return self._json({"erreur": str(e)[:300]}, 500)

        if route == "/api/favori":
            n = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(n) or b"{}") or {}
            nom = d.get("nom", "")
            if not dossier_femme(nom):
                return self._json({"erreur": "introuvable"}, 404)
            aimes = charger_favoris()
            if d.get("favori"):
                aimes.add(nom)
            else:
                aimes.discard(nom)
            sauver_favoris(aimes)
            return self._json({"ok": True, "nom": nom, "favori": nom in aimes,
                               "nb_favoris": len(aimes)})

        if route == "/api/etendre":
            # Photos de plus pour une personne deja generee : on repart de sa
            # photo 1 et de la description de visage rangee dans son meta.json.
            n = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(n) or b"{}") or {}
            nom = d.get("nom", "")
            if not NOM_VALIDE.fullmatch(nom or "") or not os.path.isdir(os.path.join("gen", nom)):
                # une femme archivee doit d'abord etre restauree : le generateur
                # ecrit dans gen/<nom>, pas dans gen/_archives/<nom>
                return self._json({"erreur": "carrousel introuvable dans gen/ "
                                             "(restaure-le s'il est archivé)"}, 404)
            combien = max(1, min(10, int(d.get("combien") or LOT_SUPPLEMENTAIRE)))
            import carrousel
            job = en_tache(nom, lambda noter: carrousel.ajouter(nom, combien, journal=noter))
            return self._json({"job": job, "nom": nom, "combien": combien})

        if route == "/api/supprimer":
            n = int(self.headers.get("Content-Length", 0))
            nom = (json.loads(self.rfile.read(n) or b"{}") or {}).get("nom", "")
            rep = dossier_femme(nom)
            if not rep:
                return self._json({"erreur": "introuvable"}, 404)
            import shutil
            os.makedirs(CORBEILLE, exist_ok=True)
            cible = os.path.join(CORBEILLE, nom)
            k = 2
            while os.path.exists(cible):
                cible = os.path.join(CORBEILLE, f"{nom}_{k}")
                k += 1
            shutil.move(rep, cible)
            aimes = charger_favoris()
            if nom in aimes:
                aimes.discard(nom)
                sauver_favoris(aimes)
            brut = rep + "_raw"
            if os.path.isdir(brut):
                shutil.move(brut, cible + "_raw")
            return self._json({"ok": True, "nom": nom, "corbeille": cible})

        if route in ("/api/archiver", "/api/restaurer"):
            n = int(self.headers.get("Content-Length", 0))
            nom = (json.loads(self.rfile.read(n) or b"{}") or {}).get("nom", "")
            if not NOM_VALIDE.fullmatch(nom or ""):
                return self._json({"erreur": "nom refuse"}, 400)
            vers_archives = route == "/api/archiver"
            depuis = os.path.join("gen" if vers_archives else ARCHIVES, nom)
            vers = os.path.join(ARCHIVES if vers_archives else "gen", nom)
            if not os.path.isdir(depuis):
                return self._json({"erreur": "introuvable"}, 404)
            if os.path.exists(vers):
                return self._json({"erreur": "un dossier de ce nom existe deja a destination"}, 409)
            os.makedirs(ARCHIVES, exist_ok=True)
            import shutil
            shutil.move(depuis, vers)
            # le dossier _raw (images avant degradation) suit le meme chemin
            brut_d, brut_v = depuis + "_raw", vers + "_raw"
            if os.path.isdir(brut_d) and not os.path.exists(brut_v):
                shutil.move(brut_d, brut_v)
            return self._json({"ok": True, "nom": nom, "archivee": vers_archives})

        if route != "/api/generer":
            return self._envoyer(404, "text/plain", "404")
        n = int(self.headers.get("Content-Length", 0))
        d = json.loads(self.rfile.read(n) or b"{}")
        age = max(30, min(70, int(d.get("age", 45))))
        persona = d.get("persona") if d.get("persona") in PERSONAS else "discrete_nature"
        genre = "h" if d.get("genre") == "h" else "f"
        base = re.sub(r"[^a-z0-9_]", "", (d.get("nom") or "").lower()) or f"{'homme' if genre == 'h' else 'femme'}{age}"
        nom = base
        i = 2
        while os.path.exists(os.path.join("gen", nom)):
            nom = f"{base}_{i}"
            i += 1
        import carrousel
        job_id = en_tache(nom, lambda noter: carrousel.build(nom, persona, age,
                                                             journal=noter, genre=genre))
        return self._json({"job": job_id, "nom": nom})


PAGE_FICHIER = os.path.join(RACINE, "gen", "interface.html")


def page():
    """Relue a chaque requete : modifier interface.html ne demande pas de redemarrage."""
    return open(PAGE_FICHIER, encoding="utf-8").read()


if __name__ == "__main__":
    import socket
    import webbrowser

    # 127.0.0.1 et NON localhost : sous Windows "localhost" se resout d'abord en
    # ::1 (IPv6), le serveur n'ecoute qu'en IPv4, et chaque requete attend deux
    # secondes avant de retomber sur IPv4. Mesure : 2051 ms contre 2 ms.
    URL = f"http://127.0.0.1:{PORT}"

    def ouvrir():
        """os.startfile d'abord : webbrowser sonde les navigateurs installes,
        ce qui est lent au premier appel. On garde webbrowser en secours."""
        for tentative in (lambda: os.startfile(URL), lambda: webbrowser.open(URL)):
            try:
                tentative()
                return True
            except Exception:
                continue
        return False

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    except OSError:
        with socket.socket() as t:
            occupe_par_nous = t.connect_ex(("127.0.0.1", PORT)) == 0
        if occupe_par_nous:
            print(f"L'interface tourne deja  ->  {URL}")
            if "--ouvrir" in sys.argv:
                ouvrir()
        else:
            print(f"Le port {PORT} est occupe par un autre programme.")
        sys.exit(0)

    # le port ecoute des maintenant (bind + listen faits par le constructeur),
    # donc la requete du navigateur est mise en file et servie aussitot apres
    def prechauffe():
        for f in dossiers():
            for ph in f["photos"]:
                try:
                    vignette(f["nom"], ph)
                except Exception:
                    pass
    threading.Thread(target=prechauffe, daemon=True).start()

    print(f"Interface prete  ->  {URL}")
    if "--ouvrir" in sys.argv:
        if not ouvrir():
            print("Le navigateur ne s'est pas ouvert : copie l'adresse ci-dessus.")
    print("Laisse cette fenetre ouverte. Ctrl+C pour arreter.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
