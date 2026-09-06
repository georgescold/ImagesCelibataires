# -*- coding: utf-8 -*-
import sys, os, base64, json; sys.path.insert(0,'gen')
from runner import call, balance, first_image_url, download
import time

REF = "gen/round1/12_nanobanana2.jpg"
b64 = base64.b64encode(open(REF,'rb').read()).decode()
DATA_URI = "data:image/jpeg;base64," + b64
print("ref bytes:", len(b64))

IDENT = ("Keep exactly the same woman from the reference photo: same face, same bone structure, same eyes, "
         "same nose, same mouth, same skin texture and freckles, same hair colour and length, same age. ")

SCENES = {
 "A_gym":   IDENT + "Now she is taking an amateur mirror selfie in a small ordinary gym, phone clearly visible in her hand in front of her chest, wearing black leggings and a plain sports top, hair tied in a messy bun, no makeup, slightly flushed. Cluttered background: dumbbell rack, a bench, cheap fluorescent ceiling lighting, smudges and fingerprints on the mirror. Framing slightly tilted and off-centre. Harsh flat overhead light, greenish white balance, sensor noise, heavy JPEG compression, no retouching, ordinary phone snapshot.",
 "B_car":   IDENT + "Now she is sitting in the driver's seat of an ordinary small car, seatbelt on, holding a takeaway coffee cup, smiling with her mouth slightly open as if talking, shot at arm's length from the passenger side. Grey daylight through the windscreen, dashboard and a supermarket car park visible behind. Underexposed face, mixed white balance, slight motion blur, sensor noise, heavy JPEG compression, no retouching, ordinary phone snapshot.",
 "C_ski":   IDENT + "Now she is on a ski slope in the Alps, wearing a white ski jacket, a helmet and mirrored ski goggles pushed up on her forehead, laughing with her cheeks red from the cold, holding her poles. Bright overexposed snow, blown-out highlights, harsh contrast, other skiers far behind, chairlift and pine trees. Slightly crooked framing, glove partially covering a corner of the lens, lens flare, heavy JPEG compression, ordinary phone snapshot taken by a friend.",
 "D_night": IDENT + "Now she is at a restaurant table at night with friends, direct on-camera phone flash lighting her face, wearing a dark green satin blouse and hoop earrings, holding a glass of wine, mid-laugh with her eyes half closed. Harsh flash falloff, red-eye tint, blown-out forehead, dark background with an out-of-focus friend's shoulder and cluttered table with plates and glasses. Off-centre framing, slight motion blur, heavy JPEG compression, ordinary phone snapshot.",
}

MODELS = [
 ("nanobanana2edit", "fal-ai/nano-banana-2/edit",        lambda u,p: dict(prompt=p, image_urls=[u], aspect_ratio="4:5", num_images=1, output_format="jpeg", resolution="1K")),
 ("seedream5proedit","bytedance/seedream/v5/pro/edit",   lambda u,p: dict(prompt=p, image_urls=[u], image_size={"width":832,"height":1040}, num_images=1, output_format="jpeg")),
 ("flux2proedit",    "fal-ai/flux-2-pro/edit",           lambda u,p: dict(prompt=p, image_urls=[u], image_size={"width":832,"height":1040}, output_format="jpeg")),
]

os.makedirs("gen/round3", exist_ok=True)
res=[]
print("BALANCE START:", balance())
for mlab, model, mk in MODELS:
    for slab, prompt in SCENES.items():
        b0=balance()
        ok, body, dt = call(model, mk(DATA_URI, prompt))
        time.sleep(7)
        b1=balance()
        rec={"label":f"{mlab}__{slab}","model":model,"ok":ok,"seconds":round(dt,1),
             "cost_usd": round(b0-b1,5) if b0 and b1 else None}
        if ok:
            u=first_image_url(body)
            if u:
                p=f"gen/round3/{mlab}__{slab}.jpg"
                try: rec["bytes"]=download(u,p); rec["file"]=p
                except Exception as e: rec["ok"]=False; rec["error"]="dl:"+str(e)
            else: rec["ok"]=False; rec["error"]=json.dumps(body)[:250]
        else: rec["error"]=json.dumps(body)[:300]
        res.append(rec); print(json.dumps(rec,ensure_ascii=False), flush=True)
json.dump(res, open("gen/round3/_results.json","w"), indent=1)
print("BALANCE END:", balance())
