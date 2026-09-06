# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,'gen')
from runner import run, balance
WH   = {"image_size": {"width": 832, "height": 1040}}
AR45 = {"aspect_ratio": "4:5"}
AR34 = {"aspect_ratio": "3:4"}

PROMPT = ("Amateur holiday snapshot taken by a friend on a phone: a 38-year-old ordinary French woman standing on a "
"seaside promenade in the south of France, wearing a floral summer dress, sunglasses pushed up into her hair, one "
"hand shading her eyes, mid-laugh, squinting a little in the harsh midday sun. Framed too wide and off-centre, she "
"occupies only the middle third of the frame, the horizon tilted a few degrees, a stranger walking past behind her, "
"parked scooters, palm trees, a beach bar. Blown-out white sky, harsh contrasty midday light, hard shadow under her "
"chin, slightly overexposed, chromatic aberration at the edges, a touch of camera shake, heavy JPEG compression. "
"Not a professional photograph, no retouching, no bokeh, ordinary tourist snapshot from a personal phone gallery.")

JOBS = [
 ("02_flux2_klein9b",    "fal-ai/flux-2/klein/9b",                   dict(WH, num_images=1, output_format="jpeg")),
 ("04_nanobanana2_lite", "google/nano-banana-2-lite",                dict(AR45, num_images=1, output_format="jpeg")),
 ("05_flux1_krea",       "fal-ai/flux/krea",                         dict(WH, num_images=1, output_format="jpeg")),
 ("07_qwen_2512",        "fal-ai/qwen-image-2512",                   dict(WH, num_images=1, output_format="jpeg")),
 ("08_flux2_dev",        "fal-ai/flux-2",                            dict(WH, num_images=1, output_format="jpeg")),
 ("09_krea2_medium",     "krea/v2/medium/text-to-image",             dict(AR45)),
 ("10_krea2_large",      "krea/v2/large/text-to-image",              dict(AR45)),
 ("11_seedream5_pro",    "bytedance/seedream/v5/pro/text-to-image",  dict(WH, num_images=1, output_format="jpeg")),
 ("12_nanobanana2",      "fal-ai/nano-banana-2",                     dict(AR45, num_images=1, output_format="jpeg", resolution="1K")),
 ("13_mai_image_25",     "microsoft/mai-image-2.5",                  dict(AR34, num_images=1, output_format="jpeg")),
 ("14_flux2_pro",        "fal-ai/flux-2-pro",                        dict(WH, output_format="jpeg")),
]
print("BALANCE START:", balance())
run(JOBS, "gen/round2", PROMPT)
print("BALANCE END:", balance())
