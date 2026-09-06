# -*- coding: utf-8 -*-
import sys, os, base64, json, time; sys.path.insert(0,'gen')
from runner import call, balance, first_image_url, download
from pipeline import finish

WH={"image_size":{"width":832,"height":1040},"output_format":"jpeg"}
os.makedirs("gen/round5",exist_ok=True); os.makedirs("gen/round5_final",exist_ok=True)
REF="gen/round4/slide1_hero.jpg"
uri="data:image/jpeg;base64,"+base64.b64encode(open(REF,'rb').read()).decode()
IDENT=("Keep exactly the same woman as the reference photo: identical face, bone structure, eyes, nose, mouth, "
       "freckles, mole, skin texture, hair colour and length, same age. ")

# 5 angles radicalement differents, comme dans une vraie galerie photo
SLIDES=[
 ("s1_contreplongee", "vintage_chaud", -3.0,
  IDENT+"Extreme low-angle close selfie held below her chin and pointing up: her jaw and the underside of her chin "
  "dominate the frame, nostrils slightly visible, ceiling and a bare light bulb behind her head, unflattering "
  "perspective that makes her neck look long. She is at home in the evening, wearing a black v-neck top, hair down, "
  "looking down into the lens with a small smirk. Warm yellow tungsten light from above, deep shadows in the eye "
  "sockets, face slightly overexposed, orange colour cast, sensor noise, heavy JPEG compression, no retouching."),
 ("s2_deloin",        "none",           2.5,
  IDENT+"Photo taken by someone else from far away with a phone: she is a small figure in the lower third of the "
  "frame, standing on a stone staircase in an old French village, wearing jeans and a beige linen shirt, one hand on "
  "the railing, looking away to the side and not at the camera. Most of the frame is wall, sky and empty steps. Flat "
  "midday light, dull colours, subject slightly out of focus because the phone focused on the wall, tilted horizon, "
  "heavy JPEG compression, badly framed amateur snapshot."),
 ("s3_miroir",        "nb",             1.5,
  IDENT+"Full-length bathroom mirror selfie, phone held at chest height and clearly visible, her face partly hidden "
  "behind it, wearing a grey sports bra and black leggings, hair in a high ponytail, hip pushed out, other hand on "
  "her waist. Fingerprints and toothpaste specks on the mirror, towels, a laundry basket, a bathroom scale on the "
  "tiles. Harsh overhead ceiling light, hard shadows, greenish white balance, sensor noise, heavy JPEG compression."),
 ("s4_troisquart",    "none",          -1.5,
  IDENT+"Candid three-quarter shot from behind and to the side, she has turned her head back over her shoulder "
  "towards the camera and is caught mid-blink with her mouth slightly open, hair whipping across her face in the "
  "wind. She is on a windy coastal path in Brittany wearing a red windbreaker, grey sea and rocks behind. Overcast "
  "flat light, motion blur on her hair, slightly out of focus, dull desaturated colours, crooked framing, heavy "
  "JPEG compression, accidental-looking snapshot."),
 ("s5_allongee",      "clarendon",      0.0,
  IDENT+"Overhead shot looking straight down at her lying on her back on a picnic blanket in a park in summer, hair "
  "fanned out around her head on the tartan fabric, sunglasses on, one arm raised shading her face, laughing with "
  "her mouth open. Dappled harsh sunlight through leaves creating blotchy highlights on her face, blown-out patches, "
  "grass and a paper cup at the edge of the frame, phone held slightly crooked above her, heavy JPEG compression."),
]
res=[]
for lab, filt, tilt, prompt in SLIDES:
    b0=balance(); ok, body, dt = call("fal-ai/flux-2-pro/edit", dict(WH, prompt=prompt, image_urls=[uri]))
    time.sleep(7); b1=balance()
    rec={"label":lab,"filtre":filt,"ok":ok,"seconds":round(dt,1),"cost_usd":round(b0-b1,5) if b0 and b1 else None}
    if ok:
        u=first_image_url(body)
        if u:
            raw=f"gen/round5/{lab}.jpg"; rec["bytes"]=download(u,raw)
            finish(raw, f"gen/round5_final/{lab}.jpg", filtre=filt, seed=hash(lab)%9999, tilt=tilt)
        else: rec["ok"]=False; rec["error"]=json.dumps(body)[:250]
    else: rec["error"]=json.dumps(body)[:300]
    res.append(rec); print(json.dumps(rec,ensure_ascii=False),flush=True)
json.dump(res,open("gen/round5/_results.json","w"),indent=1)
print("TOTAL:", round(sum(r.get('cost_usd') or 0 for r in res),4))
