# -*- coding: utf-8 -*-
"""Appels a l'API fal.

La cle n'est PAS dans le code : elle est lue depuis la variable
d'environnement FAL_KEY, ou a defaut depuis un fichier .env a la racine
du projet (non versionne). Voir .env.example pour le format attendu.
"""
import json, os, sys, time, urllib.request, urllib.error

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cle():
    """FAL_KEY depuis l'environnement, sinon depuis le .env local."""
    cle = os.environ.get("FAL_KEY", "").strip()
    if cle:
        return cle
    env = os.path.join(RACINE, ".env")
    if os.path.exists(env):
        for ligne in open(env, encoding="utf-8"):
            ligne = ligne.strip()
            if ligne.startswith("FAL_KEY="):
                return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "Cle fal introuvable.\n"
        "Cree un fichier .env a la racine du projet contenant :\n"
        "    FAL_KEY=xxxxxxxx:yyyyyyyy\n"
        "(copie .env.example et mets ta cle dedans)"
    )


FAL_KEY = _cle()
H = {"Authorization": "Key " + FAL_KEY, "Content-Type": "application/json"}

def balance():
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://rest.alpha.fal.ai/billing/user_balance",
            headers={"Authorization": "Key " + FAL_KEY}), timeout=30)
        return float(r.read().decode().strip())
    except Exception as e:
        return None

def call(model, payload, timeout=600):
    req = urllib.request.Request("https://fal.run/" + model,
                                 data=json.dumps(payload).encode(), headers=H, method="POST")
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        body = json.loads(r.read().decode())
        return True, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return False, {"http": e.code, "body": e.read().decode()[:600]}, time.time() - t0
    except Exception as e:
        return False, {"err": str(e)}, time.time() - t0

def first_image_url(body):
    for k in ("images", "image"):
        v = body.get(k)
        if isinstance(v, list) and v:
            return v[0].get("url") if isinstance(v[0], dict) else v[0]
        if isinstance(v, dict):
            return v.get("url")
    return None

def download(url, path):
    d = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=180).read()
    open(path, "wb").write(d)
    return len(d)

def run(jobs, outdir, prompt):
    os.makedirs(outdir, exist_ok=True)
    results = []
    for label, model, extra in jobs:
        b0 = balance()
        payload = {"prompt": prompt}
        payload.update(extra)
        ok, body, dt = call(model, payload)
        time.sleep(7.0)
        b1 = balance()
        cost = round(b0 - b1, 5) if (b0 is not None and b1 is not None) else None
        rec = {"label": label, "model": model, "ok": ok, "seconds": round(dt, 1), "cost_usd": cost}
        if ok:
            u = first_image_url(body)
            if u:
                p = os.path.join(outdir, label + ".jpg")
                try:
                    rec["bytes"] = download(u, p); rec["file"] = p
                except Exception as e:
                    rec["ok"] = False; rec["error"] = "dl:" + str(e)
            else:
                rec["ok"] = False; rec["error"] = "no image: " + json.dumps(body)[:300]
        else:
            rec["error"] = json.dumps(body)[:400]
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    json.dump(results, open(os.path.join(outdir, "_results.json"), "w"), indent=1)
    return results
