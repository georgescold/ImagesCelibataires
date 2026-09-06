# -*- coding: utf-8 -*-
"""
Etalonnage doux, continu et infini.

Les anciens filtres etaient des presets marques (vert neon, violet, flash orange).
Ici on tire des parametres CONTINUS dans des plages volontairement etroites :
chaque photo a un rendu different, mais aucune ne crie "filtre".

Chaque persona ne fait que decaler le CENTRE de ces plages, elle ne change
jamais leur amplitude. Une femme aura donc une signature colorimetrique
reconnaissable sur ses 5 photos, sans que ce soit voyant.
"""
import random
from PIL import Image, ImageEnhance, ImageOps, ImageFilter, ImageDraw


def _courbe(im, gain_r, gain_v, gain_b, offset_r=0, offset_v=0, offset_b=0):
    r, v, b = im.split()
    return Image.merge('RGB', (
        r.point(lambda x: max(0, min(255, int(x * gain_r + offset_r)))),
        v.point(lambda x: max(0, min(255, int(x * gain_v + offset_v)))),
        b.point(lambda x: max(0, min(255, int(x * gain_b + offset_b)))),
    ))


def _vignette(im, force):
    if force <= 0.01:
        return im
    w, h = im.size
    masque = Image.new('L', (w, h), 0)
    ImageDraw.Draw(masque).ellipse((-w * 0.30, -h * 0.30, w * 1.30, h * 1.30), fill=255)
    masque = masque.filter(ImageFilter.GaussianBlur(min(w, h) * 0.22))
    return Image.composite(im, ImageEnhance.Brightness(im).enhance(1 - force), masque)


# Chaque persona = un decalage du centre des plages. Rien de plus.
# (temperature, densite, saturation, contraste, vignette, proba_nb)
PERSONAS = {
    "sportive_naturelle":    dict(temp=+0.00, lum=+0.02, sat=+0.03, con=+0.02, vig=0.04, p_nb=0.12),
    "quarantenaire_filtres": dict(temp=+0.03, lum=+0.04, sat=-0.02, con=-0.03, vig=0.06, p_nb=0.22),
    "bobo_voyage":           dict(temp=+0.04, lum=+0.01, sat=-0.03, con=-0.01, vig=0.08, p_nb=0.25),
    "fetarde":               dict(temp=+0.02, lum=+0.00, sat=+0.05, con=+0.04, vig=0.07, p_nb=0.10),
    "discrete_nature":       dict(temp=-0.02, lum=+0.00, sat=-0.01, con=+0.00, vig=0.03, p_nb=0.18),
}


def grade(im, persona="discrete_nature", rnd=None, force_nb=None):
    """Applique un etalonnage doux tire au hasard autour du centre de la persona."""
    rnd = rnd or random.Random()
    p = PERSONAS.get(persona, PERSONAS["discrete_nature"])

    # noir et blanc : occasionnel, et sans exces de contraste
    nb = rnd.random() < p["p_nb"] if force_nb is None else force_nb
    if nb:
        im = ImageOps.grayscale(im).convert('RGB')
        im = ImageEnhance.Contrast(im).enhance(rnd.uniform(1.02, 1.12))
        im = ImageEnhance.Brightness(im).enhance(rnd.uniform(0.98, 1.05))
        return _vignette(im, max(0.0, p["vig"] + rnd.uniform(-0.03, 0.04)))

    # temperature : chaud (+) ou froid (-), amplitude volontairement faible
    t = p["temp"] + rnd.uniform(-0.045, 0.045)
    im = _courbe(im, 1 + t * 0.9, 1 + t * 0.15, 1 - t * 0.9,
                 offset_r=int(t * 9), offset_b=int(-t * 7))

    # teinte magenta/vert tres legere, pour varier sans que ca se voie
    g = rnd.uniform(-0.022, 0.022)
    im = _courbe(im, 1 + g * 0.5, 1 - g, 1 + g * 0.5)

    im = ImageEnhance.Brightness(im).enhance(1 + p["lum"] + rnd.uniform(-0.045, 0.045))
    im = ImageEnhance.Color(im).enhance(1 + p["sat"] + rnd.uniform(-0.07, 0.07))
    im = ImageEnhance.Contrast(im).enhance(1 + p["con"] + rnd.uniform(-0.05, 0.05))

    # levee de noirs : typique d'un JPEG de telephone et d'un filtre d'appli discret
    leve = rnd.randint(0, 7)
    if leve:
        im = _courbe(im, 1, 1, 1, offset_r=leve, offset_v=leve, offset_b=leve + rnd.randint(0, 3))

    return _vignette(im, max(0.0, p["vig"] + rnd.uniform(-0.04, 0.05)))


if __name__ == "__main__":
    print("personas :", ", ".join(PERSONAS))
    r = random.Random(0)
    for nom, p in PERSONAS.items():
        ech = [round(p["temp"] + r.uniform(-0.045, 0.045), 3) for _ in range(5)]
        print(f"  {nom:24} temperature sur 5 photos -> {ech}  (N&B {int(p['p_nb']*100)}%)")
