# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,'gen')
from runner import run, balance

WH   = {"image_size": {"width": 832, "height": 1040}}   # 4:5
AR45 = {"aspect_ratio": "4:5"}
AR34 = {"aspect_ratio": "3:4"}

PROMPT = ("Casual amateur front-camera phone selfie of a 38-year-old ordinary French woman. "
"Natural everyday face, visible skin texture and pores, a couple of small blemishes, faint under-eye shadows, "
"a few fine lines, almost no makeup. Shoulder-length wavy dark-blonde hair, slightly messy, visible darker roots. "
"Plain grey marl sweater. She is sitting on a beige fabric sofa in an ordinary cluttered French flat: a radiator, "
"a monstera plant, a cheap floor lamp, a folded blanket, a half-empty mug on a low table. Flat overcast daylight "
"from a window on the left mixed with dull yellowish indoor light. Phone held at arm's length slightly above eye "
"level, framing a bit off-centre and slightly tilted, her forearm clipping the bottom corner of the frame, top of "
"her head close to the edge. Slightly soft focus, low dynamic range, visible sensor noise in the shadows, heavy "
"JPEG compression. No bokeh, no studio lighting, no retouching, unglamorous, candid snapshot from a personal phone "
"gallery, 2019 mid-range smartphone photo.")

JOBS = [
 ("01_flux1_schnell",     "fal-ai/flux-1/schnell",                        dict(WH, num_inference_steps=4, num_images=1, output_format="jpeg")),
 ("02_flux2_klein9b",     "fal-ai/flux-2/klein/9b",                       dict(WH, num_images=1, output_format="jpeg")),
 ("03_seedream5_lite",    "bytedance/seedream/v5/lite/text-to-image",     dict(WH, num_images=1)),
 ("04_nanobanana2_lite",  "google/nano-banana-2-lite",                    dict(AR45, num_images=1, output_format="jpeg")),
 ("05_flux1_krea",        "fal-ai/flux/krea",                             dict(WH, num_images=1, output_format="jpeg")),
 ("06_photo_flux",        "rundiffusion-fal/rundiffusion-photo-flux",     dict(WH, num_images=1, output_format="jpeg")),
 ("07_qwen_2512",         "fal-ai/qwen-image-2512",                       dict(WH, num_images=1, output_format="jpeg")),
 ("08_flux2_dev",         "fal-ai/flux-2",                                dict(WH, num_images=1, output_format="jpeg")),
 ("09_krea2_medium",      "krea/v2/medium/text-to-image",                 dict(AR45)),
 ("10_krea2_large",       "krea/v2/large/text-to-image",                  dict(AR45)),
 ("11_seedream5_pro",     "bytedance/seedream/v5/pro/text-to-image",      dict(WH, num_images=1, output_format="jpeg")),
 ("12_nanobanana2",       "fal-ai/nano-banana-2",                         dict(AR45, num_images=1, output_format="jpeg", resolution="1K")),
 ("13_mai_image_25",      "microsoft/mai-image-2.5",                      dict(AR34, num_images=1, output_format="jpeg")),
 ("14_flux2_pro",         "fal-ai/flux-2-pro",                            dict(WH, output_format="jpeg")),
]
print("BALANCE START:", balance())
run(JOBS, "gen/round1", PROMPT)
print("BALANCE END:", balance())
