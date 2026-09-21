# -*- coding: utf-8 -*-
"""
Genere un carrousel complet (5 photos, meme femme) pret a poster.

Usage :  python gen/carrousel.py <nom> [persona] [age] [f|h]
Ex    :  python gen/carrousel.py sandrine_47 quarantenaire_filtres 47

Personas : sportive_naturelle | quarantenaire_filtres | bobo_voyage | fetarde | discrete_nature

Les poses deja utilisees sont memorisees dans gen/_poses_utilisees.json :
deux carrousels ne rejouent jamais la meme pose tant que la banque n'est pas epuisee.

Chaque photo passe au controle (gen/controle.py) avant d'etre gardee : meme
visage que la photo 1, corps possible, rien d'impossible dans le cadre. Une
photo recalee est refaite, deux fois au plus, avec la faute constatee reinjectee
dans le prompt. L'age, lui, ne se controle pas apres coup : il se decrit a la
source, dans le visage (visages.py).

`ajouter()` reprend un carrousel deja genere et lui fabrique des photos
supplementaires a partir de son propre visage : meme personne, nouveaux lieux.
"""
import sys, os, base64, json, random, time
from contextlib import nullcontext
sys.path.insert(0, 'gen')
from runner import call, first_image_url, download
from pipeline import finish
from filters import PERSONAS
from poses import tirage
import lieux
import controle
from genre import au_masculin as au_masc
from visages import visage, visage_h
from identite import identite, identite_h

WH = {"image_size": {"width": 832, "height": 1040}, "output_format": "jpeg"}
T2I = "fal-ai/flux-2-pro"
EDIT = "fal-ai/flux-2-pro/edit"
ETAT = "gen/_poses_utilisees.json"

# Relances au maximum par photo quand le controle la recale. Au-dela on garde la
# derniere et on l'ecrit dans le journal : trois essais rates sur la meme scene
# veulent dire que c'est la scene qui coince, pas le tirage.
RELANCES = 2

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


# --------------------------------------------------------------------- controle
# Le seul reproche que le controle adresse a la photo 1 en propre : elle sert de
# reference aux quatre autres, donc son visage doit etre lisible.
VISAGE_LISIBLE = "visage de la photo 1 trop petit ou masqué : elle sert de référence"


def _controler(chemin, reference, genre, dire, exiger_visage=False):
    """Passe une photo au controle. Retourne (ok, soucis, rapport).

    `exiger_visage` : pour la photo 1 seulement. Elle sert de reference aux
    quatre autres, donc un visage masque ou minuscule y est disqualifiant meme
    si l'image est par ailleurs correcte — c'est ce qui fait deriver un
    carrousel entier (constate : une photo 1 en lunettes noires de nuit, et les
    quatre suivantes ont chacune leur propre visage).
    """
    if not controle.actif():
        return True, [], {}
    ok, soucis, rapport = controle.controler(chemin, reference=reference, genre=genre)
    if rapport.get("panne"):
        dire(f"    controle indisponible ({rapport['panne'][:70]}), photo gardee")
        return True, [], rapport
    if ok and exiger_visage:
        pct = rapport.get("visage_pct")
        if pct is None:
            pct = controle.mesurer_visage(chemin)
            rapport["visage_pct"] = pct
        if rapport.get("visage") == "cache" or (pct is not None and pct < controle.SEUIL_VISAGE):
            ok, soucis = False, [VISAGE_LISIBLE]
    return ok, soucis, rapport


def _renfort(soucis, genre):
    """Les consignes a rajouter au prompt de la relance."""
    if soucis == [VISAGE_LISIBLE]:
        elle, son = ("He", "his") if genre == "h" else ("She", "her")
        return (f" {elle} is facing the camera, close enough that {son} head fills a good part of"
                f" the frame. {son.capitalize()} face is plainly visible and unobstructed: no"
                " sunglasses, no hand, no phone and no object in front of the eyes, face not"
                " turned away from the lens.")
    return controle.consigne_relance(soucis, genre)


def _produire(faire, chemin_brut, reference, genre, dire, numero, exiger_visage=False,
              relances_jusqua=None):
    """Genere une photo, la controle, la refait si elle est recalee.

    `faire(renfort)` fait un essai et rend True si l'image est sur le disque ;
    c'est l'appelant qui sait s'il s'agit d'un text-to-image ou d'une edition.

    `relances_jusqua` : instant (time.time()) passe lequel on ne relance plus, on
    garde la photo telle quelle. En ligne, une fonction Vercel est tuee a 300 s ;
    une relance de trop, et tout le carrousel est perdu, deja paye et pas encore
    televerse. Une photo imparfaite vaut mieux que pas de carrousel du tout.

    Retourne (reussi, rapport_final, nb_relances).
    """
    renfort = ""
    dernier = {}
    for essai in range(RELANCES + 1):
        if not faire(renfort):
            return False, dernier, essai
        ok, soucis, dernier = _controler(chemin_brut, reference, genre, dire, exiger_visage)
        if ok:
            note = controle.resume(dernier)
            if note:
                dire(f"    contrôle {numero} : {note}")
            return True, dernier, essai
        if essai == RELANCES:
            dire(f"    {numero} gardée malgré : {' ; '.join(soucis)}")
            return True, dernier, essai
        if relances_jusqua and time.time() > relances_jusqua:
            dire(f"    {numero} gardée malgré : {' ; '.join(soucis)} (plus le temps de la refaire)")
            return True, dernier, essai
        dire(f"    {numero} recalée ({' ; '.join(soucis)}) — on refait")
        renfort = _renfort(soucis, genre)
    return True, dernier, RELANCES


# -------------------------------------------------------------------- generation
def build(nom, persona="discrete_nature", age=42, seed=None, journal=None, genre="f",
          avant=None, relances_jusqua=None, tirage_exclusif=nullcontext):
    """`journal` : fonction appelee pour chaque ligne d'avancement.
    Par defaut on ecrit sur la sortie standard ; le serveur, lui, fournit
    son propre collecteur — aucun etat global n'est modifie.

    `relances_jusqua` : plus aucune relance apres cet instant (cf. _produire).
    `avant` : plus aucune photo entamee apres cet instant. Les deux ne servent
    qu'en ligne, ou la fonction est tuee a 300 s et ou rien n'est televerse
    avant la fin : un carrousel de quatre photos vaut mieux que zero.

    `tirage_exclusif` : fabrique d'un contexte dans lequel se fait le tirage du
    prenom, des poses et des lieux. Plusieurs generations peuvent tourner en meme
    temps ; sans exclusion, elles liraient le meme etat des registres et
    pourraient tirer le meme prenom. En local c'est un verrou de fil d'execution,
    en ligne un verrou en base qui relit et renvoie aussi les registres."""
    dire = journal or (lambda m: print(m, flush=True))
    rnd = random.Random(seed)
    raw, fin = f"gen/{nom}_raw", f"gen/{nom}"
    os.makedirs(raw, exist_ok=True)
    os.makedirs(fin, exist_ok=True)

    homme = genre == "h"
    with tirage_exclusif():
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
    # l'identite, des maintenant : les autres appareils l'affichent dans les
    # generations en cours, bien avant la fin
    dire(f"  identité : {ident_civile['prenom']}, {age} ans, {ident_civile['metier']}")

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

    echec = []

    def essai_hero(renfort):
        ok, body, _ = call(T2I, dict(WH, prompt=hero + renfort))
        if not ok:
            dire(f"HERO FAIL {body}")
            echec.append(True)
            return False
        download(first_image_url(body), f"{raw}/1.jpg")
        return True

    fait, rap1, n1 = _produire(essai_hero, f"{raw}/1.jpg", None, genre, dire, 1,
                               exiger_visage=True, relances_jusqua=relances_jusqua)
    if echec or not fait:
        return
    finish(f"{raw}/1.jpg", f"{fin}/1.jpg", persona=persona, force_nb=(slide_nb == 1),
           seed=rnd.randint(0, 9999), tilt=rnd.choice([0, -2, 2, -3]))
    dire(f"  1 [{p0['scene']}] {p0['decor'][:52]}")
    controles = [{"n": 1, "relances": n1, "rapport": rap1}]

    # --- slides 2 a 5 : meme femme, en image-to-image ---
    ident = _description(tete, homme)
    for i, x in enumerate(plans[1:], start=2):
        if avant and time.time() > avant:
            dire(f"    temps imparti atteint : carrousel arrete a {i - 1} photo(s)")
            break
        rap, n = _slide(i, x, raw, fin, ident, rappel, persona, homme, genre,
                        rnd, slide_nb, dire, relances_jusqua=relances_jusqua)
        controles.append({"n": i, "relances": n, "rapport": rap})

    meta = {
        "nom": nom, "persona": persona, "age": age, "genre": genre,
        "prenom": ident_civile["prenom"], "metier": ident_civile["metier"],
        "recherche": ident_civile["recherche"], "textes": ident_civile["textes"],
        "visage": tete, "signes": signes,
        "slides": [{"n": i + 1, "scene": x["scene"], "lieu": x["decor"],
                    "pose": x["pose"], "prise": x["prise"],
                    "texte": ident_civile["textes"][i]} for i, x in enumerate(plans)],
        "controle": controles,
        "cree": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(meta, open(f"{fin}/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _bilan(controles, dire)
    dire(f"=> {fin}  ({ident_civile['prenom']}, {age} ans, {ident_civile['metier']})  ~$0.21")


def _description(tete, homme):
    return (f"Exactly the same {'man' if homme else 'woman'} as the reference photo, same specific face: " + tete +
            " Identical bone structure, nose, eyes, mouth, skin and hair as the reference. "
            "A different day and a different outfit. ")


def _slide(i, x, raw, fin, ident, rappel, persona, homme, genre, rnd, slide_nb, dire,
           reference=None, relances_jusqua=None):
    """Une photo en image-to-image depuis la photo de reference, controlee et
    relancee si besoin. Retourne (rapport, nb_relances)."""
    ref = reference or f"{raw}/1.jpg"
    uri = "data:image/jpeg;base64," + base64.b64encode(open(ref, "rb").read()).decode()
    regles = au_masc(RULES) if homme else RULES

    def essai(renfort):
        prompt = ident + bloc(x) + rappel + regles + renfort
        ok, body, _ = call(EDIT, dict(WH, prompt=prompt, image_urls=[uri]))
        if not ok and "content_policy" in json.dumps(body):
            # faux positif du filtre : on retente sans la description detaillee du visage
            court = f"Exactly the same {'man' if homme else 'woman'} as the reference photo, same face, hair and age. A different day. "
            ok, body, _ = call(EDIT, dict(WH, prompt=court + bloc(x) + rappel + regles + renfort,
                                          image_urls=[uri]))
            if ok:
                dire("    (relance apres filtre de contenu)")
        if not ok:
            dire(f"  FAIL {x['scene']} {str(body)[:160]}")
            return False
        download(first_image_url(body), f"{raw}/{i}.jpg")
        return True

    fait, rap, n = _produire(essai, f"{raw}/{i}.jpg", ref, genre, dire, i,
                             relances_jusqua=relances_jusqua)
    if not fait:
        return {}, n
    finish(f"{raw}/{i}.jpg", f"{fin}/{i}.jpg", persona=persona, force_nb=(slide_nb == i),
           seed=rnd.randint(0, 9999), tilt=rnd.choice([0, 0, -2, 2, -1.5, 3]))
    dire(f"  {i} [{x['scene']}] {x['decor'][:52]}")
    return rap, n


def _bilan(controles, dire):
    relances = sum(c["relances"] for c in controles)
    if not controle.actif():
        return
    if relances:
        dire(f"  contrôle : {relances} photo(s) refaite(s), +{relances * 0.045:.2f} $")
    else:
        dire("  contrôle : les photos passent toutes du premier coup")


# --------------------------------------------------- photos supplementaires
def ajouter(nom, combien=5, journal=None, seed=None, avant=None, depart=None,
            relances_jusqua=None, tirage_exclusif=nullcontext):
    """Ajoute des photos a un carrousel deja genere, a partir de SON visage.

    On ne regenere pas la personne : sa description de visage, ses signes
    particuliers et sa photo 1 sont deja dans le dossier. Les nouvelles photos
    reprennent les cinq memes textes en boucle, si bien qu'un second lot de
    cinq se poste tel quel comme un deuxieme carrousel de la meme femme.

    `avant` : instant (time.time()) au-dela duquel on s'arrete meme s'il reste
    des photos a faire. En ligne, une fonction Vercel est tuee a 300 s et tout
    ce qu'elle n'a pas encore televerse serait perdu ; mieux vaut rendre trois
    photos que zero.
    """
    dire = journal or (lambda m: print(m, flush=True))
    fin, raw = f"gen/{nom}", f"gen/{nom}_raw"
    chemin_meta = f"{fin}/meta.json"
    if not os.path.exists(chemin_meta):
        raise SystemExit(f"{chemin_meta} introuvable : ce carrousel n'a pas de fiche a reprendre.")
    meta = json.load(open(chemin_meta, encoding="utf-8"))
    if not meta.get("visage"):
        raise SystemExit("La fiche ne contient pas la description du visage : "
                         "ce carrousel est trop ancien pour etre etendu.")

    os.makedirs(raw, exist_ok=True)
    rnd = random.Random(seed)
    age = meta.get("age", 45)
    genre = meta.get("genre", "f")
    homme = genre == "h"
    persona = meta.get("persona") if meta.get("persona") in PERSONAS else "discrete_nature"
    textes = meta.get("textes") or []

    # la reference est l'image BRUTE de la photo 1 : le post-traitement lui a
    # ajoute flou, bruit et double compression, dont le modele d'edition se
    # servirait pour dessiner un visage plus flou a chaque generation
    reference = f"{raw}/1.jpg" if os.path.exists(f"{raw}/1.jpg") else f"{fin}/1.jpg"
    if not os.path.exists(reference):
        raise SystemExit("La photo 1 est introuvable : rien a partir de quoi etendre.")

    if depart is None:
        # en local le dossier fait foi ; en ligne il n'y a dans /tmp que la photo
        # de reference, et c'est l'appelant qui connait la vraie numerotation
        existantes = sorted(int(f[:-4]) for f in os.listdir(fin)
                            if f.endswith(".jpg") and f[:-4].isdigit())
        depart = (max(existantes) + 1) if existantes else 1

    with tirage_exclusif():                       # cf. build()
        deja = charger_etat()
        gen, registre = lieux.charger()
        scenes = lieux.scenes_disponibles(combien, gen, registre, rnd)
        plans, deja = tirage(combien, seed=seed, deja=deja, scenes=scenes, genre=genre)
        for x in plans:
            lieu, libre = lieux.choisir(x["scene"], gen, registre, rnd)
            x["decor"] = au_masc(lieu) if homme else lieu
            registre[lieu] = gen
            if not libre:
                dire(f"    (banque de lieux epuisee pour {x['scene']}, repli sur le plus ancien)")
        lieux.sauver(gen + 1, registre)
        sauver_etat(deja)

    signes = meta.get("signes") or []
    rappel = ""
    if len(signes) >= 2:
        rappel = ((" He" if homme else " She") + " still has exactly the same two distinguishing"
                  " features as in the reference photo: " + signes[0] + ", and " + signes[1] +
                  ". Both must be present and identical here.")
    ident = _description(meta["visage"], homme)
    slide_nb = 0                      # le noir et blanc appartient au lot d'origine

    dire(f"  {meta.get('prenom', nom)} : {combien} photo(s) de plus, "
         f"a partir de la photo 1 du carrousel")
    nouvelles, controles = [], []
    for k, x in enumerate(plans):
        i = depart + k
        if avant and time.time() > avant:
            dire(f"    temps imparti atteint : {len(nouvelles)} photo(s) sur {combien}")
            break
        rap, n = _slide(i, x, raw, fin, ident, rappel, persona, homme, genre,
                        rnd, slide_nb, dire, reference=reference, relances_jusqua=relances_jusqua)
        if not os.path.exists(f"{fin}/{i}.jpg"):
            continue
        nouvelles.append({"n": i, "scene": x["scene"], "lieu": x["decor"],
                          "pose": x["pose"], "prise": x["prise"],
                          "texte": textes[(i - 1) % len(textes)] if textes else None})
        controles.append({"n": i, "relances": n, "rapport": rap})

    meta["slides"] = (meta.get("slides") or []) + nouvelles
    meta["controle"] = (meta.get("controle") or []) + controles
    meta["etendu"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    json.dump(meta, open(chemin_meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _bilan(controles, dire)
    dire(f"=> {len(nouvelles)} photo(s) ajoutée(s) à {fin}  "
         f"~${0.045 * len(nouvelles):.2f}")
    return [s["n"] for s in nouvelles]


# --------------------------------------------------- refaire une seule photo
def refaire(nom, numero, journal=None, seed=None, relances_jusqua=None,
            tirage_exclusif=nullcontext):
    """Refait la photo `numero` d'un carrousel, a la place de l'ancienne.

    La scene et son lieu sont conserves : ils sont deja consommes dans les
    registres, et c'est le decor qui donne sa place a la photo dans le
    carrousel. En revanche la pose, le cadrage, l'angle, la lumiere, la tenue et
    l'accessoire sont retires — si c'est la pose qui a rate, la rejouer a
    l'identique la raterait encore.

    La photo 1 se refait depuis elle-meme : c'est elle qui porte le visage de
    reference des autres, et la repasser en text-to-image donnerait un autre
    visage, qui ne collerait plus aux quatre suivantes.
    """
    dire = journal or (lambda m: print(m, flush=True))
    fin, raw = f"gen/{nom}", f"gen/{nom}_raw"
    chemin_meta = f"{fin}/meta.json"
    if not os.path.exists(chemin_meta):
        raise SystemExit(f"{chemin_meta} introuvable : ce carrousel n'a pas de fiche a reprendre.")
    meta = json.load(open(chemin_meta, encoding="utf-8"))
    if not meta.get("visage"):
        raise SystemExit("La fiche ne contient pas la description du visage : "
                         "ce carrousel est trop ancien pour etre refait photo par photo.")

    slides = meta.get("slides") or []
    ancien = next((s for s in slides if s.get("n") == numero), None)
    if not ancien or not ancien.get("scene"):
        raise SystemExit(f"La photo {numero} n'est pas decrite dans la fiche.")

    rnd = random.Random(seed)
    age = meta.get("age", 45)
    genre = meta.get("genre", "f")
    homme = genre == "h"
    persona = meta.get("persona") if meta.get("persona") in PERSONAS else "discrete_nature"

    # la reference reste la photo 1, sauf quand c'est elle qu'on refait
    base = 1 if numero != 1 else numero
    reference = next((p for p in (f"{raw}/{base}.jpg", f"{fin}/{base}.jpg") if os.path.exists(p)), None)
    if not reference:
        raise SystemExit(f"La photo {base} est introuvable : rien a partir de quoi refaire.")

    with tirage_exclusif():                       # cf. build()
        deja = charger_etat()
        deja.add((ancien["scene"], ancien.get("pose", "")))     # ne pas rejouer la pose ratee
        plans, deja = tirage(1, seed=seed, deja=deja, scenes=[ancien["scene"]], genre=genre)
        sauver_etat(deja)
    x = plans[0]
    x["decor"] = ancien["lieu"]                             # meme decor, deja consomme

    signes = meta.get("signes") or []
    rappel = ""
    if len(signes) >= 2:
        rappel = ((" He" if homme else " She") + " still has exactly the same two distinguishing"
                  " features as in the reference photo: " + signes[0] + ", and " + signes[1] +
                  ". Both must be present and identical here.")

    dire(f"  {meta.get('prenom', nom)} : on refait la photo {numero} [{ancien['scene']}]")
    os.makedirs(raw, exist_ok=True)
    rap, n = _slide(numero, x, raw, fin, _description(meta["visage"], homme), rappel,
                    persona, homme, genre, rnd, 0, dire, reference=reference,
                    relances_jusqua=relances_jusqua)
    if not os.path.exists(f"{fin}/{numero}.jpg"):
        raise SystemExit(f"La photo {numero} n'a pas pu etre refaite.")

    ancien.update({"pose": x["pose"], "prise": x["prise"]})
    meta["controle"] = [c for c in (meta.get("controle") or []) if c.get("n") != numero] + \
                       [{"n": numero, "relances": n, "rapport": rap}]
    meta["refait"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    json.dump(meta, open(chemin_meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _bilan([{"n": numero, "relances": n}], dire)
    dire(f"=> photo {numero} refaite  ~${0.045 * (1 + n):.2f}")
    return numero


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "=":
        # python gen/carrousel.py = <nom> <numero>
        refaire(sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) > 2 and sys.argv[1] == "+":
        # python gen/carrousel.py + <nom> [combien]
        ajouter(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    else:
        nom = sys.argv[1] if len(sys.argv) > 1 else "carrousel"
        pers = sys.argv[2] if len(sys.argv) > 2 else "discrete_nature"
        age = int(sys.argv[3]) if len(sys.argv) > 3 else 42
        genre = sys.argv[4] if len(sys.argv) > 4 else "f"
        build(nom, pers, age, seed=None, genre=genre)
