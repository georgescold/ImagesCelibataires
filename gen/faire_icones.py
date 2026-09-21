# -*- coding: utf-8 -*-
"""
Fabrique les icones de l'app installable (PWA) dans web/icones/.

    python gen/faire_icones.py

Le dessin : trois photos au format 4:5 en eventail — un carrousel — sur le fond
sombre de l'atelier, la photo de devant dans le degrade rose des boutons
principaux, avec une silhouette de portrait. Il doit se lire a 48 px sur un
ecran d'accueil : pas de texte, trois aplats, un contraste franc.

Quatre fichiers, parce que chaque systeme a ses exigences :

  icone-192.png, icone-512.png   « any » : coins arrondis, angles transparents ;
                                 c'est ce que montrent les boites d'installation
  icone-masque-512.png           « maskable » : carre plein. Android y decoupe la
                                 forme de son choix (cercle, goutte...) ; le
                                 dessin reste dans le cercle central de 80 %
                                 que la norme garantit visible
  apple-touch-icon.png           180 px, carre plein et SANS transparence : iOS
                                 arrondit lui-meme les angles, et remplirait de
                                 noir ce qui est transparent
  favicon-32.png                 l'onglet du navigateur

Tout est dessine a 2048 px puis reduit : Pillow ne lisse pas les bords des
rectangles arrondis, la reduction s'en charge.
"""
import os
from PIL import Image, ImageDraw, ImageFilter

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "web", "icones")

T = 2048                      # taille de travail
FOND = (14, 12, 17)           # --fond
LUEUR = (48, 22, 34)          # la lueur rosee du haut de l'atelier
ROSE_CLAIR = (255, 107, 140)  # --accent-clair
ROSE = (229, 56, 95)          # --accent
ROSE_SOURD = (143, 39, 64)    # --accent-sourd
ROSE_NUIT = (84, 25, 42)
ENCRE = (43, 6, 15)           # le texte des boutons roses


def fond():
    """Fond sombre avec, en haut, la lueur rosee de l'interface."""
    im = Image.new("RGB", (T, T), FOND)
    halo = Image.new("L", (T, T), 0)
    ImageDraw.Draw(halo).ellipse((T * 0.05, -T * 0.35, T * 0.95, T * 0.55), fill=255)
    halo = halo.filter(ImageFilter.GaussianBlur(T * 0.12))
    im.paste(Image.new("RGB", (T, T), LUEUR), (0, 0), halo)
    return im


def photo(largeur, couleur_haut, couleur_bas, silhouette=False):
    """Une photo 4:5 aux coins arrondis, degrade vertical, sur calque transparent."""
    hauteur = int(largeur * 5 / 4)
    marge = int(largeur * 0.2)                 # de la place pour la rotation
    L, H = largeur + 2 * marge, hauteur + 2 * marge
    degrade = Image.new("RGB", (1, hauteur))
    for y in range(hauteur):
        t = y / max(1, hauteur - 1)
        degrade.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(couleur_haut, couleur_bas)))
    degrade = degrade.resize((largeur, hauteur))
    masque = Image.new("L", (largeur, hauteur), 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, largeur - 1, hauteur - 1),
                                             radius=int(largeur * 0.13), fill=255)
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    calque.paste(degrade, (marge, marge), masque)
    if silhouette:
        d = ImageDraw.Draw(calque)
        cx = L // 2
        r = int(largeur * 0.16)                                  # la tete
        cy = marge + int(hauteur * 0.40)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ENCRE + (235,))
        ep = int(largeur * 0.33)                                 # les epaules
        haut = cy + int(r * 1.35)
        d.ellipse((cx - ep, haut, cx + ep, haut + int(ep * 1.3)), fill=ENCRE + (235,))
        # la photo coupe le buste, comme un vrai portrait
        calque.paste((0, 0, 0, 0), (0, marge + hauteur, L, H))
        bord = Image.new("L", (L, H), 0)
        ImageDraw.Draw(bord).rounded_rectangle((marge, marge, marge + largeur - 1, marge + hauteur - 1),
                                               radius=int(largeur * 0.13), fill=255)
        calque.putalpha(Image.composite(calque.getchannel("A"), Image.new("L", (L, H), 0), bord))
    return calque


def ombre(calque, flou):
    o = Image.new("RGBA", calque.size, (0, 0, 0, 0))
    o.putalpha(calque.getchannel("A").point(lambda a: int(a * 0.55)))
    return o.filter(ImageFilter.GaussianBlur(flou))


def eventail():
    """Les trois photos, sur fond transparent, centrees."""
    toile = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    largeur = int(T * 0.30)
    cartes = [
        (photo(largeur, ROSE_SOURD, ROSE_NUIT), -15, -0.115, 0.015),
        (photo(largeur, ROSE, ROSE_SOURD), 15, 0.115, 0.015),
        (photo(largeur, ROSE_CLAIR, ROSE, silhouette=True), 0, 0.0, -0.01),
    ]
    for calque, angle, dx, dy in cartes:
        tourne = calque.rotate(angle, resample=Image.BICUBIC, expand=True)
        x = int(T / 2 + dx * T - tourne.width / 2)
        y = int(T / 2 + dy * T - tourne.height / 2)
        sh = ombre(tourne, T * 0.012)
        toile.alpha_composite(sh, (x + int(T * 0.006), y + int(T * 0.014)))
        toile.alpha_composite(tourne, (x, y))
    return toile


def carre_plein():
    im = fond().convert("RGBA")
    im.alpha_composite(eventail())
    return im


def arrondi(im, rayon):
    masque = Image.new("L", im.size, 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, im.width - 1, im.height - 1),
                                             radius=rayon, fill=255)
    sortie = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sortie.paste(im, (0, 0), masque)
    return sortie


def reduire(im, cote):
    return im.resize((cote, cote), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    plein = carre_plein()
    rond = arrondi(plein, int(T * 0.225))
    fichiers = {
        "icone-192.png": reduire(rond, 192),
        "icone-512.png": reduire(rond, 512),
        "icone-masque-512.png": reduire(plein, 512),
        "apple-touch-icon.png": reduire(plein, 180).convert("RGB"),   # iOS : pas d'alpha
        "favicon-32.png": reduire(rond, 32),
    }
    for nom, im in fichiers.items():
        im.save(os.path.join(SORTIE, nom), optimize=True)
        print(f"  {nom:24} {im.size[0]}x{im.size[1]}  "
              f"{os.path.getsize(os.path.join(SORTIE, nom)) // 1024} Ko")
