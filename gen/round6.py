# -*- coding: utf-8 -*-
import sys, os, base64, json, time; sys.path.insert(0,'gen')
from runner import call, balance, first_image_url, download
from pipeline import finish

WH={"image_size":{"width":832,"height":1040},"output_format":"jpeg"}
os.makedirs("gen/round6",exist_ok=True); os.makedirs("gen/round6_final",exist_ok=True)
REF="gen/round4/slide1_hero.jpg"
uri="data:image/jpeg;base64,"+base64.b64encode(open(REF,'rb').read()).decode()

IDENT=("Same woman as the reference photo: identical face, bone structure, eyes, nose, mouth, freckles, mole, "
       "skin texture, hair colour and length, same age. ")
# regles communes, repetees a chaque slide
RULES=(" Her expression is calm and ordinary: a small closed-mouth smile or a neutral relaxed face, eyes looking "
 "straight at the lens. She is NOT laughing, NOT posing, NOT performing, no big emotion, no open mouth, no teeth. "
 "Absolutely no text, no writing, no letters, no numbers, no signs, no posters, no labels, no logos, no brand names "
 "anywhere in the image, including in the background. Ordinary boring everyday moment, nothing special happening. "
 "Slightly imperfect framing, flat unflattering light, low dynamic range, mild sensor noise, heavy JPEG compression, "
 "no bokeh, no studio light, no retouching. Plain amateur phone snapshot.")

SLIDES=[
 ("s1_canape",  "none",         -2.0, IDENT+"She is sitting on the sofa in her living room at home, wearing a plain "
   "black t-shirt, hair down and a bit flat, arm's length front-camera selfie held slightly above eye level. Behind "
   "her: a cushion, a beige wall, the corner of a curtain, a radiator. Dull grey daylight from a window off to the "
   "side."+RULES),
 ("s2_voiture", "none",          1.5, IDENT+"She is sitting in the driver's seat of a parked car, seatbelt across "
   "her chest, keys in the ignition, arm's length selfie held near the windscreen. Grey daylight, an empty car park "
   "and bare trees blurred behind the glass. Her face is slightly underexposed against the bright window."+RULES),
 ("s3_miroir",  "none",          2.0, IDENT+"Full-length mirror selfie in a bedroom, phone held at chest height and "
   "visible in her hand, wearing straight-leg jeans and a plain grey jumper, flat shoes, weight on one hip. Behind "
   "her: an unmade bed, a wardrobe door slightly open, a chair with clothes on it. One ceiling light on, warm dull "
   "indoor light."+RULES),
 ("s4_terrasse","vintage_chaud",-1.0, IDENT+"Photo taken by a friend across a small table on a café terrace: she is "
   "sitting with a coffee cup in front of her, one hand resting on the table, wearing a light denim jacket, looking "
   "at the camera. Behind her: an empty chair, a hedge, part of a parked car. Flat overcast afternoon light."+RULES),
 ("s5_exterieur","nb",           0.0, IDENT+"She is standing outside on a pavement in an ordinary residential street, "
   "photographed from about four metres away by someone else, full body slightly off-centre in the frame with a lot "
   "of empty pavement around her, wearing a black coat and jeans, hands in her pockets. Behind her: hedges, a "
   "driveway, a wheelie bin, parked cars. Grey flat winter daylight."+RULES),
]
res=[]
for lab,filt,tilt,prompt in SLIDES:
    b0=balance(); ok,body,dt=call("fal-ai/flux-2-pro/edit", dict(WH,prompt=prompt,image_urls=[uri]))
    time.sleep(7); b1=balance()
    rec={"label":lab,"filtre":filt,"ok":ok,"seconds":round(dt,1),"cost_usd":round(b0-b1,5) if b0 and b1 else None}
    if ok:
        u=first_image_url(body)
        if u:
            raw=f"gen/round6/{lab}.jpg"; download(u,raw)
            finish(raw, f"gen/round6_final/{lab}.jpg", filtre=filt, seed=hash(lab)%9999, tilt=tilt)
        else: rec["ok"]=False; rec["error"]=json.dumps(body)[:250]
    else: rec["error"]=json.dumps(body)[:300]
    res.append(rec); print(json.dumps(rec,ensure_ascii=False),flush=True)
json.dump(res,open("gen/round6/_results.json","w"),indent=1)
print("TOTAL:", round(sum(r.get('cost_usd') or 0 for r in res),4))
