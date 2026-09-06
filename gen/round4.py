# -*- coding: utf-8 -*-
import sys, os, base64, json, time; sys.path.insert(0,'gen')
from runner import call, balance, first_image_url, download

WH = {"image_size": {"width": 832, "height": 1040}, "output_format": "jpeg"}
os.makedirs("gen/round4", exist_ok=True)
res=[]

def do(model, payload, out):
    b0=balance(); ok, body, dt = call(model, payload); time.sleep(7); b1=balance()
    rec={"label":os.path.basename(out)[:-4],"model":model,"ok":ok,"seconds":round(dt,1),
         "cost_usd":round(b0-b1,5) if b0 and b1 else None}
    if ok:
        u=first_image_url(body)
        if u: rec["bytes"]=download(u,out); rec["file"]=out
        else: rec["ok"]=False; rec["error"]=json.dumps(body)[:250]
    else: rec["error"]=json.dumps(body)[:300]
    res.append(rec); print(json.dumps(rec,ensure_ascii=False), flush=True)
    return rec["ok"]

# ---------- SLIDE 1 : le hook (visage) ----------
HERO = ("Amateur phone selfie of an ordinary French woman of 36, girl-next-door pretty but not a model: slightly "
"asymmetric face, real skin with visible pores, a few freckles across the nose, faint smile lines, one small mole "
"on the cheek, light natural makeup that is a bit uneven. Long wavy chestnut hair with sun-lightened ends, a few "
"strands stuck to her cheek. Wearing a plain white ribbed tank top and a thin gold chain. She is on a small "
"apartment balcony in Marseille in late afternoon, warm low sun raking across her face from the right, half her "
"face in shadow, laundry drying on a rack behind her, a plastic chair, geraniums in a pot, ochre buildings out of "
"focus below. Arm's length front camera, slightly low angle looking up at her, framing off-centre with her head "
"near the top edge and a lot of empty sky on the left, horizon tilted 4 degrees. Overexposed highlights on her "
"forehead, warm colour cast, low dynamic range, mild sensor noise, heavy JPEG compression, no bokeh, no studio "
"lighting, no retouching. Ordinary candid snapshot from a personal phone gallery.")
do("fal-ai/flux-2-pro", dict(WH, prompt=HERO), "gen/round4/slide1_hero.jpg")

# ---------- SLIDES 2-5 : meme femme, autres scenes ----------
REF = "gen/round4/slide1_hero.jpg"
if os.path.exists(REF):
    uri = "data:image/jpeg;base64," + base64.b64encode(open(REF,'rb').read()).decode()
    IDENT = ("Keep exactly the same woman as in the reference photo: identical face, bone structure, eyes, nose, "
             "mouth, freckles, mole, skin texture, hair colour and length, same age. ")
    SLIDES = {
     "slide2_age": IDENT + "Different day, different photo. She is indoors at home in winter, sitting cross-legged on a "
        "worn sofa under a blanket, wearing an oversized grey hoodie, hair in a loose messy bun, no makeup, holding a mug "
        "with both hands, giving a small tired closed-mouth smile. Dull grey daylight from a window behind her so her face "
        "is slightly underexposed and backlit. Cluttered flat: bookshelf, drying rack, TV remote and crumbs on the sofa. "
        "Framing crooked, taken at arm's length, top of the frame cut off. Muddy shadows, noisy, heavy JPEG compression, "
        "no retouching, ordinary phone snapshot.",
     "slide3_metier": IDENT + "Different day, different photo. Full-body shot taken by a colleague on a phone: she is "
        "standing in the doorway of a small French hair salon wearing a black apron over jeans and white trainers, arms "
        "loosely crossed, laughing at something off-camera and not looking at the lens. She occupies only the middle of a "
        "too-wide frame, plenty of empty pavement below her, a parked car and a bakery sign behind. Flat grey overcast "
        "light, mixed shop lighting, slight camera shake, dull colours, heavy JPEG compression, no retouching, ordinary "
        "phone snapshot.",
     "slide4_vie":   IDENT + "Different day, different photo. She is walking a scruffy medium-sized brown dog on a muddy "
        "path beside a lake in autumn, wearing a navy raincoat and jeans tucked into wellies, hood down, hair wind-blown "
        "across her face, mouth open mid-sentence. Grey flat light, drizzle, bare trees, a bench in the background. Photo "
        "taken from too far away, subject small and off-centre, horizon tilted, slight motion blur, low contrast, dull "
        "colours, heavy JPEG compression, no retouching, ordinary phone snapshot taken by a friend.",
     "slide5_cta":   IDENT + "Different day, different photo. Bathroom mirror selfie in an ordinary French flat: phone "
        "clearly visible in her raised hand covering part of her chin, wearing a black long-sleeve top and jeans, hair "
        "down and slightly damp, hip cocked, small confident half-smile. Toothbrush pot, a towel on the radiator, "
        "toiletries on the shelf, water spots and fingerprints on the mirror, harsh yellow ceiling bulb overhead casting "
        "shadows under her eyes. Framing slightly tilted, mirror reflection, greenish-yellow white balance, sensor noise, "
        "heavy JPEG compression, no retouching, ordinary phone snapshot.",
    }
    for lab, p in SLIDES.items():
        do("fal-ai/flux-2-pro/edit", dict(WH, prompt=p, image_urls=[uri]), f"gen/round4/{lab}.jpg")

json.dump(res, open("gen/round4/_results.json","w"), indent=1)
print("TOTAL cost:", round(sum(r.get('cost_usd') or 0 for r in res),4))
