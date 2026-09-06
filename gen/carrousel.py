# -*- coding: utf-8 -*-
"""
Genere un carrousel complet (5 photos, meme femme) pret a poster.

Usage :  python gen/carrousel.py <nom> [persona] [age] [f|h]
Ex    :  python gen/carrousel.py sandrine_47 quarantenaire_filtres 47

Personas : sportive_naturelle | quarantenaire_filtres | bobo_voyage | fetarde | discrete_nature

Les poses deja utilisees sont memorisees dans gen/_poses_utilisees.json :
deux carrousels ne rejouent jamais la meme pose tant que la banque n'est pas epuisee.
"""
import sys, os, base64, json, random
sys.path.insert(0, 'gen')
from runner import call, first_image_url, download
from pipeline import finish
from filters import PERSONAS
from poses import tirage
import lieux
from genre import au_masculin as au_masc
from visages import visage, visage_h
from identite import identite, identite_h

WH = {"image_size": {"width": 832, "height": 1040}, "output_format": "jpeg"}
T2I = "fal-ai/flux-2-pro"
EDIT = "fal-ai/flux-2-pro/edit"
ETAT = "gen/_poses_utilisees.json"

# --- Regles non negociables, deduites du compte source ---
RULES = (
 " Her expression is calm and ordinary: a small closed-mouth smile, or a neutral relaxed face, or caught mid-word."
 " She is NOT laughing, NOT posing like a model, NOT performing. No big emotion, no wide open mouth, no bared teeth,"
 " no hand in her hair, no pout."
 " Absolutely no text, no writing, no letters, no numbers, no signs, no posters, no labels, no logos, no brand names"
 " anywhere in the image, including in the background."
 " An ordinary boring everyday moment, nothing special happening. Her head is tilted, her shoulders are uneven."
 " Flat unflattering light, low dynamic range, mild sensor noise, heavy JPEG compression, no bokeh, no studio light,"
 " no retouching. Plain amateur phone snapshot."
)


def charger_etat():
    if os.path.exists(ETAT):
        return {tuple(x) for x in json.load(open(ETAT, encoding='utf-8'))}
    return set()


def sauver_etat(deja):
    json.dump([list(x) for x in deja], open(ETAT, 'w', encoding='utf-8'), indent=0)


def bloc(x):
    """Assemble un plan de prise de vue en un fragment de prompt."""
    return (f"She is wearing {x['tenue']}.{x['accessoire']} "
            f"She is {x['decor']}, {x['pose']}. "
            f"{x['cadrage']} {x['angle']} {x['lumiere']}{x['physique']}")


def build(nom, persona="discrete_nature", age=42, seed=None, journal=None, genre="f"):
    """`journal` : fonction appelee pour chaque ligne d'avancement.
    Par defaut on ecrit sur la sortie standard ; le serveur, lui, fournit
    son propre collecteur — aucun etat global n'est modifie."""
    dire = journal or (lambda m: print(m, flush=True))
    rnd = random.Random(seed)
    raw, fin = f"gen/{nom}_raw", f"gen/{nom}"
    os.makedirs(raw, exist_ok=True)
    os.makedirs(fin, exist_ok=True)

    homme = genre == "h"
    ident_civile = (identite_h if homme else identite)(age, rnd)
    deja = charger_etat()
    # --- lieux : un fond ne peut pas revenir avant 30 generations de femmes ---
    gen, registre = lieux.charger()
    scenes = lieux.scenes_disponibles(5, gen, registre, rnd)
    plans, deja = tirage(5, seed=seed, deja=deja, scenes=scenes, genre=genre)
    for x in plans:
        lieu, libre = lieux.choisir(x["scene"], gen, registre, rnd)
        # les fonds sont ecrits au feminin ("in her living room") : ils passent
        # par la meme conversion que les poses
        x["decor"] = au_masc(lieu) if genre == "h" else lieu
        registre[lieu] = gen
        if not libre:
            dire(f"    (banque de lieux epuisee pour {x['scene']}, repli sur le plus ancien)")
    lieux.sauver(gen + 1, registre)
    sauver_etat(deja)

    # --- slide 1 : le hero, en text-to-image ---
    p0 = plans[0]
    tete, signes = (visage_h if homme else visage)(seed=rnd.randint(0, 10**9), age=age, avec_signes=True)
    # les signes particuliers doivent se voir sur TOUTES les photos
    rappel = ((" He" if homme else " She") + " still has exactly the same two distinguishing features as in the reference photo: "
              + signes[0] + ", and " + signes[1] + ". Both must be present and identical here.")
    # un seul noir et blanc par carrousel, au plus
    slide_nb = rnd.randint(1, 5) if rnd.random() < PERSONAS[persona]["p_nb"] * 2.2 else 0
    dire("  visage : " + tete[:110].split(". ")[1][:100] + "...")
    hero = ("Amateur phone snapshot. " + tete + " " + bloc(p0) + (au_masc(RULES) if homme else RULES))
    ok, body, _ = call(T2I, dict(WH, prompt=hero))
    if not ok:
        dire(f"HERO FAIL {body}")
        return
    download(first_image_url(body), f"{raw}/1.jpg")
    finish(f"{raw}/1.jpg", f"{fin}/1.jpg", persona=persona, force_nb=(slide_nb == 1),
           seed=rnd.randint(0, 9999), tilt=rnd.choice([0, -2, 2, -3]))
    dire(f"  1 [{p0['scene']}] {p0['decor'][:52]}")

    # --- slides 2 a 5 : meme femme, en image-to-image ---
    uri = "data:image/jpeg;base64," + base64.b64encode(open(f"{raw}/1.jpg", "rb").read()).decode()
    ident = (f"Exactly the same {'man' if homme else 'woman'} as the reference photo, same specific face: " + tete +
             " Identical bone structure, nose, eyes, mouth, skin and hair as the reference. "
             "A different day and a different outfit. ")
    for i, x in enumerate(plans[1:], start=2):
        ok, body, _ = call(EDIT, dict(WH, prompt=ident + bloc(x) + rappel + (au_masc(RULES) if homme else RULES), image_urls=[uri]))
        if not ok and "content_policy" in json.dumps(body):
            # faux positif du filtre : on retente sans la description detaillee du visage
            court = f"Exactly the same {'man' if homme else 'woman'} as the reference photo, same face, hair and age. A different day. "
            ok, body, _ = call(EDIT, dict(WH, prompt=court + bloc(x) + rappel + (au_masc(RULES) if homme else RULES), image_urls=[uri]))
            if ok:
                dire("    (relance apres filtre de contenu)")
        if not ok:
            dire(f"  FAIL {x['scene']} {str(body)[:160]}")
            continue
        download(first_image_url(body), f"{raw}/{i}.jpg")
        finish(f"{raw}/{i}.jpg", f"{fin}/{i}.jpg", persona=persona, force_nb=(slide_nb == i),
               seed=rnd.randint(0, 9999), tilt=rnd.choice([0, 0, -2, 2, -1.5, 3]))
        dire(f"  {i} [{x['scene']}] {x['decor'][:52]}")

    meta = {
        "nom": nom, "persona": persona, "age": age, "genre": genre,
        "prenom": ident_civile["prenom"], "metier": ident_civile["metier"],
        "recherche": ident_civile["recherche"], "textes": ident_civile["textes"],
        "visage": tete, "signes": signes,
        "slides": [{"n": i + 1, "scene": x["scene"], "lieu": x["decor"],
                    "pose": x["pose"], "prise": x["prise"],
                    "texte": ident_civile["textes"][i]} for i, x in enumerate(plans)],
        "cree": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(meta, open(f"{fin}/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dire(f"=> {fin}  ({ident_civile['prenom']}, {age} ans, {ident_civile['metier']})  ~$0.21")


if __name__ == "__main__":
    nom = sys.argv[1] if len(sys.argv) > 1 else "carrousel"
    pers = sys.argv[2] if len(sys.argv) > 2 else "discrete_nature"
    age = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    genre = sys.argv[4] if len(sys.argv) > 4 else "f"
    build(nom, pers, age, seed=None, genre=genre)
