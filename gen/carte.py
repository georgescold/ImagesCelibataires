# -*- coding: utf-8 -*-
"""
Generateur de cartes de personnalite, au format des vraies cartes Compaatible.

Usage :  python gen/carte.py <type-id> --prenom X [--sortie chemin.jpg]
Ex    :  python gen/carte.py reveur-romantique --prenom Céline

Sans --sortie, l'image est ecrite dans gen/_cartes/<prenom>-<type>.jpg.
`python gen/carte.py --types` liste les 16 identifiants.

--- Independant des carrousels ---------------------------------------------------

⚠️ Cette carte N'EST PAS branchee sur les carrousels, et c'est voulu (Loys,
14/09/2026 : elle sert a un autre projet). Une premiere version l'ajoutait en
6e image de chaque carrousel ; elle a ete retiree. Ne pas la rebrancher sans le
redemander : une carte posee a cote de photos generees d'une « celibataire » ne
se lit plus comme une illustration.

--- D'ou viennent les donnees ---------------------------------------------------

Tout vient du dossier `cartes/`, GENERE par Compaatible
(`node scripts/exporter-cartes-atelier.mjs`) : les 16 types, les segments de
chaque trait, les familles, les avatars et les polices. Rien n'est recopie ici.

--- La carte est celle de l'app ------------------------------------------------

Loys, 14/09/2026 : « bien mettre les memes stats + que ce soit visuellement
propre comme sur les vraies cartes ». La mise en page reprend, mesure pour
mesure, `apps/admin/src/components/studio/PersonalityCards.tsx`, replique
fidele de `PersonalityFront` dans l'app : base 240 px, ratio 1,83, chaque
dimension multipliee par le meme facteur `k`.
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
CARTES = os.path.join(ICI, "..", "cartes")
SORTIES = os.path.join(ICI, "_cartes")

W, H = 1080, 1350          # format 4:5, celui des publications TikTok en photo


def donnees():
    chemin = os.path.join(CARTES, "personnalites.json")
    if not os.path.exists(chemin):
        raise SystemExit("cartes/personnalites.json absent : lancer "
                         "`node scripts/exporter-cartes-atelier.mjs` depuis Compaatible")
    return json.load(open(chemin, encoding="utf-8"))


def police(fichier, taille):
    return ImageFont.truetype(os.path.join(CARTES, "polices", fichier), max(1, round(taille)))


def hexa(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)


def teinte(c, part, fond="#FFFFFF"):
    """La couleur `c` a `part` (0..1) sur `fond`, OPAQUE.

    ⚠️ ImageDraw ne melange pas l'alpha : il ECRIT le pixel semi-transparent,
    qui ressort plein en JPEG. Premier rendu : des rails censes etre pales
    apparaissaient pleins. On calcule donc la couleur finale nous-memes."""
    a, b = hexa(c), hexa(fond)
    return tuple(round(a[i] * part + b[i] * (1 - part)) for i in range(3)) + (255,)


def texte_espace(draw, x, y, texte, fonte, couleur, interlettre):
    """letter-spacing CSS : Pillow n'en a pas, on pose lettre par lettre."""
    for ch in texte:
        draw.text((x, y), ch, font=fonte, fill=couleur, anchor="ls")
        x += draw.textlength(ch, font=fonte) + interlettre


def dessiner_carte(t, fam, traits, prenom, largeur):
    """La carte seule, sur fond transparent. Mesures de PersonalityCards.tsx."""
    Wc = largeur
    k = Wc / 240
    px = lambda v: v * k
    Hc = round(Wc * 1.83)
    coul = fam["couleur"]

    carte = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    masque = Image.new("L", (Wc, Hc), 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, Wc - 1, Hc - 1), round(px(26)), fill=255)

    fond = Image.new("RGBA", (Wc, Hc), (255, 255, 255, 255))
    # damier de losanges : motif de 40 px pour une carte de 320 px, opacite 3 %
    pas = Wc / 8
    df = ImageDraw.Draw(fond)
    losange = teinte(coul, 0.03)
    y = 0.0
    while y < Hc:
        x = 0.0
        while x < Wc:
            df.polygon([(x + pas / 2, y), (x + pas, y + pas / 2), (x + pas / 2, y + pas), (x, y + pas / 2)], fill=losange)
            x += pas
        y += pas
    carte.paste(fond, (0, 0), masque)

    d = ImageDraw.Draw(carte)
    d.rounded_rectangle((0, 0, Wc - 1, Hc - 1), round(px(26)), outline=hexa("#EDE3D8"), width=max(2, round(k / 1.5)))

    # --- en-tete : blason de famille seul, a droite (hauteur 40.5) ---
    r = px(27) / 2
    cx = Wc - px(14.5) - r
    cy = px(16.5) + (px(40.5) - px(16.5) - px(2)) / 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hexa(fam["fond"]), outline=teinte(coul, 0.25), width=max(1, round(k / 2)))
    logo = Image.open(os.path.join(CARTES, "familles", f"{t['famille']}.png")).convert("RGBA")
    cote = round(px(17.5) * fam.get("echelleLogo", 1))
    logo = logo.resize((cote, cote), Image.LANCZOS)
    carte.alpha_composite(logo, (round(cx - cote / 2), round(cy - cote / 2)))

    # --- avatar + nom + code ---
    y = px(40.5) + px(5)
    cote_av = round(Wc * 0.55)
    av = Image.open(os.path.join(CARTES, "avatars", f"{t['id']}.png")).convert("RGBA").resize((cote_av, cote_av), Image.LANCZOS)
    carte.alpha_composite(av, (round((Wc - cote_av) / 2), round(y)))
    y += cote_av + px(5)

    taille_nom = px(18.5)
    f_nom = police("PlayfairDisplay_700Bold.ttf", taille_nom)
    while d.textlength(t["nom"], font=f_nom) > Wc - 2 * px(13) and taille_nom > px(14):
        taille_nom -= k * 0.5
        f_nom = police("PlayfairDisplay_700Bold.ttf", taille_nom)
    ligne_nom = taille_nom * 1.15
    d.text((Wc / 2, y + ligne_nom / 2), t["nom"], font=f_nom, fill=hexa("#1A1A1A"), anchor="mm")
    y += ligne_nom + px(1)

    f_code = police("Inter_500Medium.ttf", px(9.75))
    esp = px(1.2)
    larg = sum(d.textlength(ch, font=f_code) for ch in t["code"]) + esp * (len(t["code"]) - 1)
    ligne_code = px(9.75) * 1.21
    texte_espace(d, Wc / 2 - larg / 2, y + ligne_code * 0.8, t["code"], f_code, teinte(coul, 0.667), esp)
    y += ligne_code + px(4)
    fin_haut = y

    # --- bloc Big Five : sa hauteur est calculee pour reproduire les deux
    #     ressorts flexibles de la carte (0.25 au-dessus, 1 en dessous) ---
    ligne_titre = px(8.8) * 1.21
    ligne_rang = px(11) * 1.21
    bloc = px(6.5) + ligne_titre + px(2) + 5 * ligne_rang + 5 * px(5) + px(13)
    libre = Hc - fin_haut - bloc
    y = fin_haut + max(0, libre) * 0.25 / 1.25 + px(6.5)

    f_titre = police("Inter_700Bold.ttf", px(8.8))
    texte_espace(d, px(14.5), y + ligne_titre * 0.8, "PROFIL BIG FIVE", f_titre, hexa("#94A3B8"), px(1.4))
    y += ligne_titre + px(2) + px(5)

    f_lib = police("Inter_500Medium.ttf", px(11))
    dot_w = round(px(11))
    dot_h = max(3, round(px(4)))
    dot_gap = max(2, round(px(3)))
    x_dots = Wc - px(14.5) - (dot_w * 5 + dot_gap * 4)
    for tr in traits:
        allumes = t["segments"][tr["cle"]]
        milieu = y + ligne_rang / 2
        d.text((px(14.5), milieu), tr["libelle"], font=f_lib, fill=hexa("#5A5A5A"), anchor="lm")
        for i in range(5):
            x0 = x_dots + i * (dot_w + dot_gap)
            couleur = hexa(coul) if i < allumes else teinte("#CBD5E1", 0.25)
            d.rounded_rectangle((x0, milieu - dot_h / 2, x0 + dot_w, milieu + dot_h / 2), dot_h / 2, fill=couleur)
        y += ligne_rang + px(5)

    # --- pied : « CARTE DE <prenom> », en bas a gauche ---
    f_pied = police("Inter_700Bold.ttf", px(10))
    f_prenom = police("PlayfairDisplay_700Bold.ttf", px(16))
    base_prenom = Hc - px(14) - px(16) * 0.3
    d.text((px(16), base_prenom), prenom, font=f_prenom, fill=hexa("#1A1A1A"), anchor="ls")
    texte_espace(d, px(16), base_prenom - px(16) * 1.05 - px(2), "CARTE DE", f_pied, hexa("#CBD5E1"), px(1.4))

    return carte, masque


def rendre(type_id, prenom, dst):
    """Ecrit la carte, centree sur la teinte pale de sa famille, en 1080 x 1350."""
    data = donnees()
    t = next((x for x in data["types"] if x["id"] == type_id), None)
    if not t:
        raise SystemExit(f"Type inconnu : {type_id}  (voir --types)")
    fam = data["familles"][t["famille"]]

    img = Image.new("RGBA", (W, H), hexa(fam["fond"]))
    carte, masque = dessiner_carte(t, fam, data["traits"], prenom, largeur=660)
    x0 = (W - carte.width) // 2
    y0 = (H - carte.height) // 2

    ombre = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ombre.paste(Image.new("RGBA", carte.size, (70, 40, 50, 40)), (x0, y0 + 16), masque)
    img.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(26)))
    img.alpha_composite(carte, (x0, y0))

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    img.convert("RGB").save(dst, "JPEG", quality=94)
    return t


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--types" in args:
        for t in donnees()["types"]:
            print(f"  {t['id']:<26} {t['nom']}")
        sys.exit(0)
    opts = {}
    for cle in ("--prenom", "--sortie"):
        if cle in args:
            i = args.index(cle)
            opts[cle[2:]] = args[i + 1]
            del args[i:i + 2]
    if not args or not opts.get("prenom"):
        raise SystemExit(__doc__)
    type_id, prenom = args[0], opts["prenom"]
    nom_fichier = re.sub(r"[^\w-]+", "-", f"{prenom}-{type_id}").strip("-").lower()
    sortie = opts.get("sortie") or os.path.join(SORTIES, f"{nom_fichier}.jpg")
    t = rendre(type_id, prenom, sortie)
    print(f"=> {sortie}  ({t['nom']})")
