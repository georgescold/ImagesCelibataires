# -*- coding: utf-8 -*-
import sys, time, json, base64; sys.path.insert(0,'gen')
from runner import call, balance
WH={"image_size":{"width":832,"height":1040},"output_format":"jpeg"}
AR={"aspect_ratio":"4:5"}
P="a woman standing in a kitchen, casual phone photo"
uri="data:image/jpeg;base64,"+base64.b64encode(open("gen/round4/slide1_hero.jpg","rb").read()).decode()
M=[("flux-2-pro",       "fal-ai/flux-2-pro",                      dict(WH,prompt=P)),
   ("flux-2-pro/edit",  "fal-ai/flux-2-pro/edit",                 dict(WH,prompt=P,image_urls=[uri])),
   ("flux-2 [dev]",     "fal-ai/flux-2",                          dict(WH,prompt=P,num_images=1)),
   ("flux-2 klein 9B",  "fal-ai/flux-2/klein/9b",                 dict(WH,prompt=P,num_images=1)),
   ("FLUX.1 Krea [dev]","fal-ai/flux/krea",                       dict(WH,prompt=P,num_images=1)),
   ("nano-banana-2",    "fal-ai/nano-banana-2",                   dict(AR,prompt=P,num_images=1,output_format="jpeg",resolution="1K")),
   ("seedream v5 pro",  "bytedance/seedream/v5/pro/text-to-image",dict(WH,prompt=P,num_images=1)),
   ("mai-image-2.5",    "microsoft/mai-image-2.5",                dict(prompt=P,aspect_ratio="3:4",num_images=1,output_format="jpeg")),
  ]
N=3; out=[]
for name,mid,pl in M:
    time.sleep(25); b0=balance(); okc=0
    for _ in range(N):
        ok,_b,_d=call(mid,pl); okc+=1 if ok else 0
    time.sleep(25); b1=balance()
    rec={"modele":name,"ok":f"{okc}/{N}","prix_img_usd":round((b0-b1)/max(okc,1),4)}
    out.append(rec); print(json.dumps(rec,ensure_ascii=False),flush=True)
json.dump(out,open("gen/prices_final.json","w"),indent=1)
print("BALANCE:",balance())
