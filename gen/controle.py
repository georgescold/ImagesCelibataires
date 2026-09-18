# -*- coding: utf-8 -*-
"""
Controle visuel automatique d'une photo generee.

Quatre defauts sont cherches :

  1. ce n'est plus la meme personne que sur la photo de reference ;
  2. le corps est faux — un membre en trop, ou une position qu'aucun etre
     humain ne peut tenir : bras qui contourne le torse, articulation a
     l'envers, main posee ou elle n'atteint pas ;
  3. un element impossible traine dans l'image (deuxieme telephone dans la main
     libre d'un selfie au miroir, personne dupliquee, objet flottant) ;
  4. plus souple : la personne fait-elle son age.

Le controle tourne sur l'image BRUTE, avant le post-traitement : le flou, le
bruit de capteur et la double compression de `pipeline.finish` sont ajoutes
expres, et un modele de vision les prendrait pour des artefacts. Ce n'est pas
theorique : sur la version degradee du triple bras, le juge ne le voit plus.

Le juge est un modele de vision appele par fal. Deux appels par photo, un
troisieme seulement quand un reproche porte sur le visage : ~0,001 $ et 5 s la
photo, soit 0,006 $ de plus par carrousel. Chaque relance declenchee, elle,
coute 0,045 $.

-------------------------------------------------------------------------------
Une question a la fois

Les trois appels ne sont pas une precaution, ils sont le resultat de mesures.
Chaque fois qu'une question a rejoint les autres dans le meme appel, la reponse
s'est degradee — et toujours en silence, en repondant « ok ».

  - la boite du visage, posee seule : 6 % pour un visage lointain ; posee avec
    les autres : 14 %, au-dessus du seuil, garde-fou neutralise ;
  - le denombrement des membres, pose seul et en trois lignes : trois bras
    detectes sur trois essais ; pose avec les autres questions, ou simplement
    accompagne de la liste de ce qu'il faut chercher : zero sur trois.

D'ou la regle suivie ici : une question par appel, aussi courte que possible,
et un denombrement plutot qu'un avis chaque fois que c'est possible.

"""
import base64, json, os, re

from runner import call

MODELE = "openrouter/router/vision"
VLM = "google/gemini-2.5-flash"

# Sous ce pourcentage, le visage ne porte plus assez d'information : on ne juge
# ni l'identite ni l'age. Le trou mesure entre les deux familles de photos va de
# 6 a 18 %, le seuil est pose au milieu.
SEUIL_VISAGE = 12

# Ecart d'age tolere entre l'age demande et l'age apparent juge par le modele.
# Asymetrique : le format repose sur des profils de 38 ans et plus (66 700 vues
# de moyenne contre 19 000 en dessous). Une femme de 52 ans qui en parait 38
# casse le format ; en paraitre 58 ne le casse pas. Le juge sous-estime par
# ailleurs de cinq ans environ, ce que la tolerance basse absorbe.
TROP_JEUNE = 9
TROP_VIEUX = 13

REGLES = (
    "Tu es controleur qualite pour des photos amateur prises au telephone.\n"
    "Ne signale QUE des defauts objectifs et visibles. Dans le doute, reponds \"ok\".\n"
    "Ces photos sont volontairement banales, mal cadrees, mal eclairees et prises de travers :"
    " ce n'est jamais un defaut. Un bras tendu vers l'objectif parait plus gros et plus long,"
    " c'est normal en selfie et ce n'est pas un defaut.\n"
)

# Chaque point est decrit une fois. La photo 1 n'a pas de reference a qui se
# comparer : on lui retire simplement le point « identite ».
POINTS = {
    "visage":   '  "visage": "net" | "cache",',
    "identite": '  "identite": "meme" | "differente" | "indeterminable",',
    "elements": '  "elements": "ok" | "<l\'element impossible en cinq mots>",',
    "age":      '  "age": <entier, age apparent de la personne>',
}

EXPLICATIONS = {
    "visage":
        "- \"visage\" : \"net\" si tu distingues les yeux, le nez et la bouche ; \"cache\" si le"
        " visage est de dos, coupe par le cadre, flou, ou masque par un objet, une main ou un"
        " telephone.",
    "identite":
        "- \"identite\" : compare la forme du visage, le nez, les yeux, la bouche, la machoire,"
        " la naissance des cheveux et leur couleur. La coiffure, la tenue, le maquillage, la"
        " lumiere et l'expression changent d'un jour a l'autre : ce ne sont PAS des indices.",
    "elements":
        "- \"elements\" : uniquement des choses qui ne peuvent pas exister — la personne tient"
        " DEUX telephones alors qu'elle prend un selfie, elle apparait deux fois dans l'image,"
        " un objet flotte sans support, un miroir renvoie une scene differente, un objet"
        " traverse un corps.",
    "age":
        "- \"age\" : l'age que tu donnerais a cette personne en la croisant dans la rue.",
}

FIN = "\n\nReponds UNIQUEMENT par l'objet JSON, sans texte autour, sans balises de code."


def _consigne(points):
    corps = "\n".join(POINTS[p] for p in points)
    detail = "\n".join(EXPLICATIONS[p] for p in points)
    return f"Reponds par ce JSON :\n{{\n{corps}\n}}\n\n{detail}{FIN}"


def _uri(chemin, cote=1024):
    """Image en data-URI, reduite si besoin : au-dela de 1024 px le juge ne voit
    rien de plus et l'appel coute plus cher."""
    donnees = open(chemin, "rb").read()
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(donnees))
        if max(im.size) > cote:
            im = im.convert("RGB")
            im.thumbnail((cote, cote), Image.LANCZOS)
            tampon = io.BytesIO()
            im.save(tampon, "JPEG", quality=90)
            donnees = tampon.getvalue()
    except Exception:
        pass                      # Pillow absent ou image illisible : on envoie tel quel
    return "data:image/jpeg;base64," + base64.b64encode(donnees).decode()


def _lire_json(texte):
    """Le modele repond normalement du JSON nu, parfois entoure de ``` ou d'une
    phrase. On recupere le premier objet, d'accolade a accolade."""
    m = re.search(r"\{.*\}", texte or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _hauteur_visage(boite):
    """Hauteur de la boite en pourcentage de la hauteur de l'image. None si le
    modele n'a pas rendu quatre nombres exploitables."""
    if not isinstance(boite, (list, tuple)) or len(boite) != 4:
        return None
    try:
        y0, _, y1, _ = [float(v) for v in boite]
    except (TypeError, ValueError):
        return None
    return round(abs(y1 - y0) / 10.0, 1)          # coordonnees sur 1000 -> pourcentage


def actif():
    """ATELIER_CONTROLE=0 desactive le controle, et donc les relances."""
    return os.environ.get("ATELIER_CONTROLE", "1").strip() not in ("0", "non", "off", "false")


def inspecter(chemin, reference=None, genre="f"):
    """Rapport du juge sur une photo. `reference` = la photo qui fait foi pour
    l'identite ; sans elle, l'identite n'est pas jugee (cas de la photo 1).

    Retourne toujours un dict, jamais d'exception : en cas de panne du juge,
    {"panne": "..."}.
    """
    qui = "l'homme" if genre == "h" else "la femme"
    if reference:
        entete = (f"L'image 1 est la photo de reference de {qui}. L'image 2 est une nouvelle"
                  " photo censee montrer LA MEME personne, un autre jour, dans un autre lieu"
                  " et une autre tenue.\nJuge UNIQUEMENT l'image 2.\n\n")
        points = ("visage", "identite", "elements", "age")
        images = [_uri(reference), _uri(chemin)]
    else:
        entete = f"Cette photo montre {qui}.\n\n"
        points = ("visage", "elements", "age")
        images = [_uri(chemin)]

    ok, corps, _ = call(MODELE, {
        "model": VLM,
        "system_prompt": REGLES,
        "prompt": entete + _consigne(points),
        "image_urls": images,
        "temperature": 0,
        "max_tokens": 300,
    }, timeout=180)
    if not ok:
        return {"panne": str(corps)[:200]}
    rapport = _lire_json(corps.get("output", ""))
    if rapport is None:
        return {"panne": "reponse illisible : " + str(corps.get("output"))[:160]}
    rapport["cout"] = (corps.get("usage") or {}).get("cost")
    return rapport


BOITE = ("Donne la boite englobante du visage de la personne principale, du menton au sommet du"
         " front et d'une oreille a l'autre, en coordonnees normalisees sur 1000.\n"
         "Reponds UNIQUEMENT par ce JSON : {\"boite\": [y0, x0, y1, x1]}\n"
         "S'il n'y a aucun visage visible, reponds {\"boite\": null}.")

# ---------------------------------------------------------------------- corps
#
# Le corps a sa propre question, et elle fait COMPTER plutot que juger.
#
# Pose au milieu des autres, la question « l'anatomie est-elle correcte ? »
# rendait « ok » sur un double biceps au miroir ou une TROISIEME main tient le
# telephone — le rate le plus voyant de la banque de poses, celui qui a fait
# bannir 23 poses sur 86. Isolee et tournee en denombrement, la meme question
# rend « bras : 3 ». Compter oblige a suivre chaque membre ; juger autorise a
# survoler.
#
# On agit ensuite sur les nombres, pas sur l'avis : plus de deux bras, de deux
# mains ou de deux jambes est une faute, moins ne l'est pas — un membre sort du
# cadre a chaque photo.
# Cette consigne est volontairement COURTE, et c'est mesure, pas esthetique.
# Une premiere version enumerait ce qu'il fallait chercher — bras partant d'un
# mauvais endroit, epaule ou coude hors d'atteinte, torse vrille, poignet
# retourne. Sur le double biceps a trois bras : 0 detection sur 3 essais. La
# version ci-dessous, qui ne dit que « suis chaque membre et compte » : 3 sur 3.
# Les deux repondent juste sur les photos correctes. L'enumeration fait
# comparer l'image a une liste ; son absence oblige a la regarder.
CORPS = (
    "Observe le corps de la personne principale sur cette photo.\n\n"
    "Suis les membres un par un depuis l'epaule ou la hanche jusqu'a leur extremite, et"
    " compte ce que tu vois vraiment, sans supposer ce qui devrait etre la.\n\n"
    "Reponds UNIQUEMENT par ce JSON :\n"
    "{\n"
    "  \"bras\": <nombre de bras visibles, meme partiellement>,\n"
    "  \"mains\": <nombre de mains visibles, meme partiellement>,\n"
    "  \"jambes\": <nombre de jambes visibles, meme partiellement>,\n"
    "  \"posture\": \"ok\" | \"<la position impossible, en cinq mots>\"\n"
    "}\n\n"
    "Une main tenant le telephone compte comme une main. Un bras coupe par le cadre compte"
    " s'il est visible.\n"
    "\"posture\" : reponds \"ok\" si une personne reelle peut tenir cette position. Sinon dis"
    " laquelle des articulations ou lequel des membres ne va pas."
)


def inspecter_corps(chemin):
    """Denombrement des membres et tenabilite de la position. Dict, jamais
    d'exception : {} si le juge ne repond pas."""
    ok, corps, _ = call(MODELE, {
        "model": VLM, "prompt": CORPS, "image_urls": [_uri(chemin)],
        "temperature": 0, "max_tokens": 220}, timeout=150)
    if not ok:
        return {}
    r = _lire_json(corps.get("output", "")) or {}
    r["cout"] = (corps.get("usage") or {}).get("cost")
    return r


# Au-dela de ces nombres le corps est faux ; en dessous il est simplement hors
# cadre, ce qui arrive a presque toutes les photos.
MAXIMA = {"bras": (2, "bras"), "mains": (2, "mains"), "jambes": (2, "jambes")}


def _fautes_du_corps(corps):
    soucis = []
    for champ, (maxi, mot) in MAXIMA.items():
        v = corps.get(champ)
        if isinstance(v, (int, float)) and v > maxi:
            soucis.append(f"anatomie : {int(v)} {mot} au lieu de {maxi}")
    p = corps.get("posture")
    if isinstance(p, str) and p.strip().lower() not in ("ok", "", "aucun", "non", "rien", "n/a"):
        soucis.append(f"posture : {p.strip()}")
    return soucis


def mesurer_visage(chemin):
    """Hauteur du visage en pourcentage de la hauteur de l'image, None si echec.

    Appel dedie, et c'est le point important : melangee aux autres questions, la
    boite devient approximative — mesure faite, 14 % rendus pour un visage qui en
    fait 6. Posee seule, la question est fiable.
    """
    ok, corps, _ = call(MODELE, {
        "model": VLM, "prompt": BOITE, "image_urls": [_uri(chemin)],
        "temperature": 0, "max_tokens": 120}, timeout=120)
    if not ok:
        return None
    return _hauteur_visage((_lire_json(corps.get("output", "")) or {}).get("boite"))


# Les deux reproches qui reposent sur la lecture du visage, et qu'une mesure
# doit donc confirmer avant qu'ils ne declenchent une relance a 0,045 $.
_SUR_LE_VISAGE = ("ce n'est pas la même", "paraît")


def verdict(rapport, age, chemin=None):
    """(ok, [problemes]). Les problemes sont ecrits pour etre lus dans le journal,
    et traduits en consignes pour la relance par `consigne_relance`.

    `chemin` : si un reproche porte sur le visage, on mesure celui-ci avant de
    le retenir — le juge accuse volontiers une silhouette au bout d'une rue.
    """
    if not rapport or rapport.get("panne"):
        return True, []           # juge muet : on laisse passer plutot que de bloquer

    soucis = []
    net = rapport.get("visage") != "cache"
    if net and rapport.get("identite") == "differente":
        soucis.append("ce n'est pas la même personne que sur la photo 1")

    # Corps et elements impossibles se voient a toutes les tailles : ni l'un ni
    # l'autre ne depend de la lisibilite du visage.
    soucis += _fautes_du_corps(rapport.get("corps") or {})
    v = rapport.get("elements")
    if isinstance(v, str) and v.strip().lower() not in ("ok", "", "aucun", "non", "rien", "n/a"):
        soucis.append(f"élément impossible : {v.strip()}")

    vu = rapport.get("age")
    if net and isinstance(vu, (int, float)) and age:
        ecart = age - vu
        if ecart > TROP_JEUNE or -ecart > TROP_VIEUX:
            soucis.append(f"paraît {int(vu)} ans au lieu de {age}")

    if chemin and any(s.startswith(_SUR_LE_VISAGE) for s in soucis):
        pct = mesurer_visage(chemin)
        rapport["visage_pct"] = pct
        if pct is not None and pct < SEUIL_VISAGE:
            soucis = [s for s in soucis if not s.startswith(_SUR_LE_VISAGE)]
    return not soucis, soucis


def controler(chemin, reference=None, age=None, genre="f"):
    """Le controle complet d'une photo : (ok, soucis, rapport).

    Deux appels au juge, parce que deux questions melangees se repondent mal :
    l'une sur la personne (meme visage, age, element impossible), l'autre sur
    son corps (denombrement des membres, tenabilite de la position). Un
    troisieme appel ne part que si un reproche porte sur le visage.
    """
    rapport = inspecter(chemin, reference=reference, genre=genre)
    if rapport.get("panne"):
        return True, [], rapport
    rapport["corps"] = inspecter_corps(chemin)
    ok, soucis = verdict(rapport, age, chemin=chemin)
    return ok, soucis, rapport


def consigne_relance(soucis, genre="f"):
    """Ce qu'on ajoute au prompt pour que la relance ne refasse pas la meme faute.
    En anglais : c'est la langue des prompts d'image."""
    elle, son = ("he", "his") if genre == "h" else ("she", "her")
    bouts = []
    for s in soucis:
        if s.startswith("ce n'est pas la même"):
            bouts.append(" It is critically important that this is EXACTLY the same face as the"
                         " reference photo: same bone structure, same nose, same eyes, same mouth,"
                         f" same jawline, same hairline, same natural hair colour. Do not change"
                         f" {son} features.")
        elif s.startswith("anatomie"):
            bouts.append(" Anatomy must be correct and complete: exactly two arms, two hands and"
                         " two legs, five fingers on each visible hand, every limb attached to the"
                         " body, no duplicated and no merged body part.")
        elif s.startswith("posture"):
            bouts.append(" The body must be in a position a real person can physically hold:"
                         " each arm grows from its own shoulder and follows a path a real arm can"
                         " follow, shoulders elbows wrists and knees stay within the range a human"
                         " joint allows, the torso is not twisted further than a back can turn,"
                         " and each hand rests somewhere it could actually reach.")
        elif s.startswith("élément"):
            bouts.append(f" The scene must be physically possible: {elle} holds ONE phone and"
                         f" nothing else, {elle} appears exactly once in the frame, no floating"
                         " object, no impossible reflection.")
        elif s.startswith("paraît"):
            bouts.append(f" {elle.capitalize()} must clearly look {son} real age: fine lines around"
                         f" the eyes and mouth, slightly loose skin on the neck and jaw, mature"
                         f" adult features. Do NOT make {son} look younger than {son} age.")
    return "".join(dict.fromkeys(bouts))          # sans doublon, ordre conserve


def resume(rapport):
    """Une ligne pour le journal quand la photo passe."""
    pct = rapport.get("visage_pct")
    if pct is not None and pct < SEUIL_VISAGE:
        return f"sujet loin, visage à {pct} % de l'image : non jugé"
    if rapport.get("visage") == "cache":
        return "visage masqué, non jugé"
    bouts = []
    if rapport.get("identite") == "meme":
        bouts.append("même visage")
    if isinstance(rapport.get("age"), (int, float)):
        bouts.append(f"paraît {int(rapport['age'])} ans")
    return ", ".join(bouts)
