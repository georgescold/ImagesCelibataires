# -*- coding: utf-8 -*-
import sys, glob, os, json
from PIL import Image, ImageDraw, ImageFont
d=sys.argv[1]; out=sys.argv[2]; cols=int(sys.argv[3]) if len(sys.argv)>3 else 4
res={r['label']:r for r in json.load(open(os.path.join(d,'_results.json')))}
fs=sorted(glob.glob(os.path.join(d,'*.jpg')))
try: F=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
except: F=ImageFont.load_default()
CW,CH=520,650
rows=(len(fs)+cols-1)//cols
sh=Image.new('RGB',(CW*cols,(CH+40)*rows),(15,15,15)); dr=ImageDraw.Draw(sh)
for i,f in enumerate(fs):
    r,c=divmod(i,cols)
    im=Image.open(f).convert('RGB'); im.thumbnail((CW-8,CH-8))
    sh.paste(im,(c*CW+4+(CW-8-im.size[0])//2, r*(CH+40)+44))
    lab=os.path.basename(f)[:-4]; m=res.get(lab,{})
    dr.text((c*CW+8, r*(CH+40)+6), f"{lab}  {m.get('seconds')}s", fill=(255,215,60), font=F)
sh.save(out,quality=90); print(out, sh.size)
