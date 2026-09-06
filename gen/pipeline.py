# -*- coding: utf-8 -*-
"""Photo IA brute -> photo qui sort d'un vrai telephone, reposte sur TikTok."""
import sys; sys.path.insert(0,'gen')
from PIL import Image, ImageFilter, ImageEnhance
import random, io
from filters import grade

def finish(src, dst, persona="discrete_nature", seed=None, w=640, h=800, tilt=0.0, force_nb=None):
    if seed is not None: random.seed(seed)
    im = Image.open(src).convert('RGB')
    if tilt:                                          # horizon de travers
        im = im.rotate(tilt, resample=Image.BICUBIC, expand=False)
        cw, ch = int(im.width*0.94), int(im.height*0.94)
        im = im.crop(((im.width-cw)//2,(im.height-ch)//2,(im.width-cw)//2+cw,(im.height-ch)//2+ch))
    tw, th = im.size; target = w/h
    if tw/th > target: nw=int(th*target); im=im.crop(((tw-nw)//2,0,(tw-nw)//2+nw,th))
    else:              nh=int(tw/target); im=im.crop((0,(th-nh)//2,tw,(th-nh)//2+nh))
    im = im.resize((w,h), Image.LANCZOS)
    im = grade(im, persona, random.Random(seed), force_nb=force_nb)  # <- etalonnage doux continu
    im = im.filter(ImageFilter.GaussianBlur(random.uniform(0.3,0.6)))
    px = im.load()
    for _ in range(int(w*h*0.30)):
        x,y = random.randrange(w), random.randrange(h); n = random.randint(-16,16)
        r,g,b = px[x,y]; px[x,y]=(max(0,min(255,r+n)),max(0,min(255,g+n)),max(0,min(255,b+n)))
    im = ImageEnhance.Contrast(im).enhance(random.uniform(0.93,1.05))
    buf=io.BytesIO(); im.save(buf,'JPEG',quality=random.randint(55,68)); buf.seek(0)
    Image.open(buf).convert('RGB').save(dst,'JPEG',quality=random.randint(74,84))
    return dst
