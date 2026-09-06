# -*- coding: utf-8 -*-
import sys, time, json, base64; sys.path.insert(0,'gen')
from runner import call, balance
WH={"image_size":{"width":832,"height":1040},"output_format":"jpeg"}
AR={"aspect_ratio":"4:5"}
P="a woman standing in a kitchen, casual phone photo"
REF="gen/round4/slide1_hero.jpg"
uri="data:image/jpeg;base64,"+base64.b64encode(open(REF,'rb').read()).decode()

M=[("flux-2-pro",            "fal-ai/flux-2-pro",                       dict(WH,prompt=P)),
   ("flux-2-pro/edit",       "fal-ai/flux-2-pro/edit",                  dict(WH,prompt=P,image_urls=[uri])),
   ("flux-2 [dev]",          "fal-ai/flux-2",                           dict(WH,prompt=P,num_images=1)),
   ("flux-2 klein 9B",       "fal-ai/flux-2/klein/9b",                  dict(WH,prompt=P,num_images=1)),
   ("flux-2-max",            "fal-ai/flux-2-max",                       dict(WH,prompt=P)),
   ("FLUX.1 Krea [dev]",     "fal-ai/flux/krea",                        dict(WH,prompt=P,num_images=1)),
   ("flux-1 schnell",        "fal-ai/flux-1/schnell",                   dict(WH,prompt=P,num_images=1,num_inference_steps=4)),
   ("seedream v5 pro",       "bytedance/seedream/v5/pro/text-to-image",  dict(WH,prompt=P,num_images=1)),
   ("seedream v5 lite",      "bytedance/seedream/v5/lite/text-to-image", dict(WH,prompt=P,num_images=1)),
   ("nano-banana-2",         "fal-ai/nano-banana-2",                    dict(AR,prompt=P,num_images=1,output_format="jpeg",resolution="1K")),
   ("nano-banana-2-lite",    "google/nano-banana-2-lite",               dict(AR,prompt=P,num_images=1,output_format="jpeg")),
   ("mai-image-2.5",         "microsoft/mai-image-2.5",                 dict(prompt=P,aspect_ratio="3:4",num_images=1,output_format="jpeg")),
   ("krea 2 medium",         "krea/v2/medium/text-to-image",            dict(AR,prompt=P)),
   ("krea 2 large",          "krea/v2/large/text-to-image",             dict(AR,prompt=P)),
   ("qwen-image-2512",       "fal-ai/qwen-image-2512",                  dict(WH,prompt=P,num_images=1)),
   ("rundiffusion photo-flux","rundiffusion-fal/rundiffusion-photo-flux",dict(WH,prompt=P,num_images=1)),
  ]
N=2; out=[]
time.sleep(15)
for name, mid, pl in M:
    b0=balance(); okc=0; tt=0
    for _ in range(N):
        ok,_b,dt=call(mid,pl); okc+=1 if ok else 0; tt+=dt
    time.sleep(16); b1=balance()
    per = round((b0-b1)/max(okc,1), 4) if okc else None
    rec={"modele":name,"endpoint":mid,"ok":f"{okc}/{N}","prix_img_usd":per,"sec_moy":round(tt/N,1)}
    out.append(rec); print(json.dumps(rec,ensure_ascii=False),flush=True)
json.dump(out,open("gen/prices.json","w"),indent=1)
print("BALANCE FIN:", balance())
