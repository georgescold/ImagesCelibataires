# -*- coding: utf-8 -*-
"""Filtre 'vraie photo de telephone reposte sur TikTok'."""
from PIL import Image, ImageFilter, ImageEnhance
import random, io, os, sys

def degrade(src, dst, seed=None, w=640, h=800):
    if seed is not None: random.seed(seed)
    im = Image.open(src).convert('RGB')
    # 1. recadrage 4:5 + downscale au format TikTok reel
    tw, th = im.size
    tr, target = tw/th, w/h
    if tr > target: nw = int(th*target); im = im.crop(((tw-nw)//2, 0, (tw-nw)//2+nw, th))
    else:           nh = int(tw/target); im = im.crop((0, (th-nh)//2, tw, (th-nh)//2+nh))
    im = im.resize((w, h), Image.LANCZOS)
    # 2. legere perte de nettete (optique de tel + reencodage)
    im = im.filter(ImageFilter.GaussianBlur(random.uniform(0.3, 0.6)))
    # 3. bruit capteur
    px = im.load()
    for _ in range(int(w*h*0.30)):
        x, y = random.randrange(w), random.randrange(h)
        n = random.randint(-16, 16)
        r, g, b = px[x, y]
        px[x, y] = (max(0,min(255,r+n)), max(0,min(255,g+n)), max(0,min(255,b+n)))
    # 4. contraste/saturation un peu ecrases (dynamique faible du JPEG de tel)
    im = ImageEnhance.Contrast(im).enhance(random.uniform(0.93, 1.05))
    im = ImageEnhance.Color(im).enhance(random.uniform(0.90, 1.08))
    # 5. double compression JPEG (tel -> upload TikTok)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=random.randint(55, 68)); buf.seek(0)
    Image.open(buf).convert('RGB').save(dst, 'JPEG', quality=random.randint(74, 84))
    return dst

if __name__ == "__main__":
    src_dir, dst_dir = sys.argv[1], sys.argv[2]
    os.makedirs(dst_dir, exist_ok=True)
    for i, f in enumerate(sorted(os.listdir(src_dir))):
        if f.endswith('.jpg') and not f.startswith('_'):
            degrade(os.path.join(src_dir, f), os.path.join(dst_dir, f), seed=i)
            print('  ->', f)
