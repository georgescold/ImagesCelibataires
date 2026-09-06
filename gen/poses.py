# -*- coding: utf-8 -*-
"""
Banque de scenes + poses, deduite des profils qui ont le mieux performe
(Celine 40 / 144k, Aurelie 38 / 111k, Nathalie 54 / 109k).

Regles tirees de l'analyse :
 - le visage est rarement centre
 - la tete est presque toujours inclinee, epaules de travers
 - un accessoire sert de pretexte a la photo
 - au moins une photo ou elle est minuscule dans le cadre
 - au moins une photo ou elle ne regarde pas l'objectif
 - jamais de pose de mannequin

Regle de securite : AUCUNE pose acrobatique, grimacante ou a membres complexes.
Les poses a risque sont bannies plutot que corrigees, parce que le modele les
rate (troisieme bras, main desincarnee, articulation impossible). Uniquement des
positions stables et banales, avec UNE seule main libre en selfie et en miroir.
"""
import random

# ---------------------------------------------------------------- SCENES
# cle : (decor, [poses], qui_prend_la_photo)

SCENES = {

"salon": ("in her living room at home, a cushion, a plain wall, the edge of a curtain and a radiator behind her", [
  "sitting back on the sofa with her head resting against the cushion, chin slightly up",
  "sitting sideways with her legs folded under her, one shoulder higher than the other, head tilted onto it",
  "leaning forward with her free elbow on her knee, face closer to the lens",
  "sitting cross-legged holding a mug in her free hand near her chest, head tilted",
  "settled under a blanket pulled up to her chest, only her head and one hand out",
  "sitting on the floor with her back against the sofa, head tipped back",
  "sitting with a cat asleep on her lap, glancing down at it",
], "selfie"),

"cuisine": ("in her small kitchen, a kettle, a draining rack, tiles and a fridge behind her", [
  "leaning her hip against the worktop, her free arm hanging down, head tilted",
  "holding a mug up near her chin in her free hand, shoulders slightly raised",
  "turned round towards the camera with a tea towel over her shoulder",
  "standing a little too close to the lens so her face fills the frame",
  "leaning back against the fridge with her free hand behind her",
  "sitting at the kitchen table with her chin resting on her free hand",
], "selfie"),

"salle_de_bain": ("in an ordinary bathroom, a towel on the radiator, toothbrushes, water spots on the mirror", [
  "mirror selfie with the phone held up beside her jaw, head tilted",
  "mirror selfie with the phone held low near her waist, angled up",
  "mirror selfie with her free hand resting on the edge of the basin",
  "mirror selfie standing square to the mirror, weight on one hip",
  "mirror selfie with a towel wrapped round her hair, free hand adjusting it",
  "mirror selfie taken slightly side-on so the reflection is at an angle",
], "miroir"),

"chambre": ("in a bedroom, an unmade bed, a wardrobe door ajar, a chair with clothes piled on it", [
  "full-length mirror selfie with one knee slightly bent, weight on one hip, phone at chest height",
  "full-length mirror selfie standing straight on, free arm hanging at her side",
  "full-length mirror selfie with her free hand in her back pocket",
  "sitting on the edge of the bed facing the mirror, free elbow on her knee",
  "full-length mirror selfie turned three quarters so her shoulder leads",
  "mirror selfie sitting on the floor at the foot of the wardrobe mirror, knees up",
], "miroir"),

"voiture": ("in the driver or passenger seat of a parked ordinary car, a dull car park through the glass", [
  "turned in the passenger seat with her back against the door, one shoulder against the headrest",
  "holding a takeaway cup in her free hand near her chin, head back against the headrest",
  "sitting still in the seat, seatbelt on, head turned slightly towards the lens",
  "resting her head sideways against the headrest, phone held low",
  "sitting with her free hand on the steering wheel, looking across at the camera",
  "sitting low in the seat so the roof lining takes up the top of the frame",
], "selfie"),

"salle_de_sport": ("in a small ordinary gym, a dumbbell rack, a bench, flat fluorescent ceiling light", [
  "mirror selfie taken from about four metres back inside a squat rack, small and half hidden by the frame",
  "mirror selfie standing square to the mirror, free hand on her hip",
  "mirror selfie sat sideways on a weight bench, one foot up on it, phone resting on her raised knee",
  "mirror selfie standing side-on with her free arm hanging, checking her posture",
  "mirror selfie standing close to the mirror, head turned slightly, free hand hanging",
  "mirror selfie sat on a bench with a water bottle beside her, free hand on her thigh",
], "miroir"),

"terrasse_cafe": ("on a small cafe terrace, an empty chair, a hedge, part of a parked car behind", [
  "sat with her chin propped on one hand, elbow on the table",
  "holding a cup halfway up, looking over it at the camera",
  "leaning back in the chair with one arm hanging down, head tilted",
  "turned to talk to someone off-camera, only her cheek towards the lens",
  "shading her eyes from the sun with one flat hand",
  "sat with both forearms on the table, leaning slightly forward",
], "tiers"),

"rue": ("on the pavement of an ordinary residential street, hedges, a driveway and parked cars behind", [
  "standing small and off-centre with a lot of empty pavement around her, arms at her sides",
  "walking slowly towards the camera, caught between steps",
  "stopped and turned back over her shoulder, body still facing away",
  "standing with her hands in her coat pockets, shoulders slightly hunched",
  "carrying a shopping bag in one hand, hair blown across her face",
  "standing beside a parked car with one hand resting on the roof",
], "tiers"),

"parc": ("in a park, grass, trees, a bench and a bin in the background", [
  "sat on a bench with her legs crossed and one arm along the backrest, head turned away",
  "standing with her hands on her hips, looking straight at the camera",
  "leaning her shoulder against a tree, looking down at her feet",
  "sat on the grass with her legs to one side, leaning on one hand",
  "walking along the path, photographed from a few metres ahead",
  "sat on a bench leaning forward with her forearms on her knees",
], "tiers"),

"balcon": ("on a narrow apartment balcony, a drying rack, a plastic chair, blurred rooftops below", [
  "phone held low so the angle looks up at her chin and the sky, half her face in shadow",
  "leaning her free forearm on the railing, looking out sideways",
  "sat on the plastic chair with the phone held above her knees",
  "standing against the railing with the wind lifting her hair",
  "standing with her back to the view, free hand on the railing behind her",
], "selfie"),

"vacances": ("on holiday, a seafront promenade or an old village street, tourists and scooters around", [
  "small in the bottom third of the frame with the view taking up most of the picture",
  "stood with one hand on a railing, weight on one leg, sunglasses on",
  "photographed from behind walking away, head turned back over her shoulder",
  "sat on a stone step, small in a wide frame full of wall and sky",
  "standing in the middle of a narrow street, arms at her sides",
  "leaning against a wall in the shade, one foot flat against it",
], "tiers"),

"soiree": ("at a restaurant table at night, direct phone flash, a cluttered table, a blurred shoulder beside her", [
  "leaning in from the side so part of her face is cut off by the edge, flash on her forehead",
  "holding a glass in her free hand near her chin, head tipped towards the person beside her",
  "turned three quarters away talking, the side of her face lit by the flash",
  "sitting back in her chair, free hand resting on the table",
  "leaning forward on the table so the flash falls off behind her",
], "selfie"),

"jardin": ("in a small back garden, a fence, a lawn, a folded parasol", [
  "sat on a plastic chair leaning back, one arm over the armrest",
  "kneeling by a flowerbed with gloves on, looking round at the camera",
  "standing with a watering can in one hand, the other arm hanging",
  "sat on the back step with a mug beside her",
  "standing on the lawn a few metres from the camera, hands at her sides",
], "tiers"),

"travail": ("in an ordinary workplace, a plain wall, a desk edge or shelving, flat overhead light", [
  "sat at a desk with her chin on her free hand, elbow on the desk",
  "leaning back against a wall, free hand in her pocket, head tilted",
  "sat low so the camera looks down at her, phone held above",
  "standing beside a shelf with her free hand resting on it",
  "sat sideways on an office chair, one arm over the backrest",
], "selfie"),

"animal": ("at home with a scruffy pet, an ordinary cluttered room behind", [
  "holding a cat against her chest with her free arm, chin tucked beside its head",
  "sat on the floor with a dog leaning against her side",
  "sat with a dog resting its head in her lap, looking down at it",
  "kneeling beside a dog with her free hand on its back",
  "sat on the sofa with a cat stretched out next to her",
], "selfie"),
}

# ------------------------------------------------ CADRAGE / ANGLE / LUMIERE
CADRAGES = [
 "Her face is well off-centre, pushed into the left of the frame with empty space on the right.",
 "Her face is pushed into the bottom of the frame with a lot of ceiling or sky above her head.",
 "The top of her head is close to the edge of the frame.",
 "She is small in the frame with a lot of empty background around her.",
 "The frame is tilted a few degrees so the horizon or the wall line runs at an angle.",
 "Her shoulder takes up most of one side of the frame, crowding her face into a corner.",
 "The camera focused on the background instead of her, so she is slightly soft.",
 "She is partly hidden behind a piece of furniture or an object in the foreground.",
]

# angles compatibles avec chaque type de prise de vue (sinon incoherences)
ANGLES = {
 "selfie": [
   "Shot at arm's length from a low angle looking up at her chin.",
   "Shot at arm's length from above, held high, so her forehead is large in the frame.",
   "Shot at arm's length just off her own eye level.",
   "Shot with the phone held close so the wide lens slightly distorts her face.",
   "Shot with the arm barely extended so she fills almost the whole frame.",
 ],
 "miroir": [
   "Mirror shot with the phone at chest height, her face partly behind it.",
   "Mirror shot with the phone held low at hip height, angled up.",
   "Mirror shot with the phone held slightly above her head, angled down.",
   "Mirror shot taken side-on so the reflection is at an angle.",
   "Mirror shot from a few steps back so the whole room is in the reflection.",
 ],
 "tiers": [
   "Shot by someone else from a few metres away at hip height.",
   "Shot by someone else from about four metres back, standing.",
   "Shot by someone else sat across a table, at eye level.",
   "Shot by someone else from slightly above, looking down at her.",
   "Shot by someone else in a hurry, crooked and not quite level.",
 ],
}

LUMIERES = [
 "Flat grey overcast daylight, dull colours.",
 "Warm yellow ceiling bulb, mixed white balance, shadows under her eyes.",
 "Direct sunlight, bright highlights on her forehead, a shadow under her chin.",
 "Backlit by a window so her face is a little underexposed and the window is white.",
 "Greenish fluorescent strip light overhead.",
 "Late afternoon low sun from one side, half her face in shadow.",
 "Direct on-camera flash at night, harsh falloff, dark background.",
]

TENUES = [
 "a plain black t-shirt", "an oversized grey hoodie", "a light denim shirt over a white top",
 "a burgundy knitted jumper", "a black long-sleeve top and jeans", "a dark green fitted top",
 "a striped navy and white t-shirt", "a beige cardigan over a vest", "a black puffer coat",
 "a plain white t-shirt", "a grey marl sweatshirt", "a navy blouse", "a mustard yellow jumper",
 "a black vest top and leggings", "a khaki shirt dress", "a pale pink t-shirt",
]

CHEVEUX = [
 "hair loose and slightly flat", "hair in a loose bun", "hair tucked behind one ear",
 "hair in a low ponytail", "hair clipped up at the back with strands escaping", "hair damp and pushed back",
 "hair loose with a middle parting", "hair with a bit of volume", "hair in a high ponytail",
]

# accessoires plausibles selon la scene ("" = aucun, volontairement frequent)
ACC_PAR_SCENE = {
 "salon":         ["", "", "", " She is wearing reading glasses.", " She has a blanket over her shoulders."],
 "cuisine":       ["", "", "", " She is holding a mug.", " She has a tea towel over her shoulder."],
 "salle_de_bain": ["", "", "", " She has a towel wrapped round her hair.", " She is wearing a hair clip."],
 "chambre":       ["", "", "", " She is wearing reading glasses.", " She has socks on and no shoes."],
 "voiture":       ["", "", " She has sunglasses pushed up on her head.", " She is holding a set of car keys.", " She has a takeaway cup in one hand."],
 "salle_de_sport":["", "", "", " She has earphones in.", " She has a water bottle beside her."],
 "terrasse_cafe": ["", "", " She is wearing sunglasses.", " She has a canvas tote bag on the chair beside her."],
 "rue":           ["", "", " She is wearing a woolly hat.", " She has a canvas tote bag on her shoulder.", " She is wearing a scarf."],
 "parc":          ["", "", " She is wearing sunglasses.", " She has a straw hat on.", " She has a dog lead in one hand."],
 "balcon":        ["", "", "", " She is holding a mug.", " She has sunglasses pushed up on her head."],
 "vacances":      ["", " She is wearing sunglasses.", " She has a straw hat on.", " She has a small backpack on one shoulder."],
 "soiree":        ["", "", " She is wearing hoop earrings.", " She has a jacket over the back of her chair."],
 "jardin":        ["", "", " She is wearing gardening gloves.", " She has a straw hat on.", " She is wearing wellies."],
 "travail":       ["", "", "", " She is wearing reading glasses.", " She has a plain lanyard round her neck."],
 "animal":        ["", "", "", " She is wearing reading glasses."],
}

# --- physique de la prise de vue : ce qui est possible ou non ---
ANAT = (" Correct human anatomy: exactly two arms and two hands, never three."
        " Natural relaxed posture, no acrobatics, no contorted limbs, no grimace."
        " The subject appears exactly ONCE in the image: never duplicate the same person,"
        " never show both the person and a reflection of them, never add a second version"
        " of them in a background mirror or window.")

PHYSIQUE = {
 "selfie": (" This is a front-camera selfie taken by her: the phone is NOT visible anywhere in the picture,"
            " because the phone IS the camera taking this photo. Do not draw a phone in her hand."
            " One arm is out of shot holding the camera, or visible only as a foreshortened arm reaching"
            " towards the viewer, so she has only ONE free hand in the frame." + ANAT),
 "miroir": (" THE WHOLE PICTURE IS A MIRROR REFLECTION. The camera is pointed at a mirror, so every single"
            " thing visible in this frame is the reflected image, seen through the mirror. There is exactly ONE"
            " person in the picture and she is the reflection. Do NOT show her a second time outside the mirror,"
            " do NOT show her back or shoulder in the foreground, do NOT show a second mirror or a second"
            " reflection of her anywhere. In the reflection she holds a phone up in one hand, pointed back at"
            " the mirror, partly covering her face or chest; that hand is occupied, so only her OTHER hand"
            " is free." + ANAT),
 "tiers":  (" Someone else is holding the camera and taking this photo of her. She is not holding a phone and no"
            " phone is visible anywhere in the frame. Both of her hands are free." + ANAT),
}

# --- regard : une pose ou on ne voit pas bien son visage est "ailleurs" ---
_AILLEURS = ("not looking at the lens", "not looking at the camera", "looking down at her feet",
             "turned away", "turned to talk", "only her cheek", "photographed from behind",
             "and the reflection of her face", "looking out sideways", "head turned away",
             "looking down at it", "three quarters away", "back to the view")


def regard(pose):
    return "ailleurs" if any(k in pose for k in _AILLEURS) else "camera"


def tirage(n=5, seed=None, deja=None, scenes=None, genre="f"):
    """n combinaisons toutes differentes. `deja` = set de (scene, pose) deja utilises."""
    rnd = random.Random(seed)
    deja = set(deja or ())
    scenes = scenes or rnd.sample(list(SCENES), min(n, len(SCENES)))
    homme = genre == "h"
    if homme:
        from genre import au_masculin, TENUES_H, CHEVEUX_H, ACC_H_PAR_SCENE
        vest, coif, accs = TENUES_H, CHEVEUX_H, ACC_H_PAR_SCENE
    else:
        au_masculin = lambda t: t
        vest, coif, accs = TENUES, CHEVEUX, ACC_PAR_SCENE
    out = []
    used = {"c": set(), "a": set(), "l": set(), "t": set(), "h": set(), "x": set()}

    def pick(pool, key):
        libre = [x for x in pool if x not in used[key]] or list(pool)
        v = rnd.choice(libre)
        used[key].add(v)
        return v

    n_ailleurs = 0
    for idx, sc in enumerate(scenes):
        decor, poses, prise = SCENES[sc]
        libres = [p for p in poses if (sc, p) not in deja] or poses
        # slide 1 : elle doit regarder l'objectif (c'est le hook du carrousel)
        # ensuite : 2 poses "regard ailleurs" au maximum sur les 5
        if idx == 0 or n_ailleurs >= 2:
            cam = [p for p in libres if regard(p) == "camera"]
            if cam:
                libres = cam
        pose = rnd.choice(libres)
        if regard(pose) == "ailleurs":
            n_ailleurs += 1
        deja.add((sc, pose))
        pose_txt = pose.replace("phone", "camera") if prise == "selfie" else pose
        out.append(dict(scene=sc, regard=regard(pose), physique=au_masculin(PHYSIQUE[prise]),
                        decor=decor, pose=au_masculin(pose_txt), prise=prise,
                        cadrage=au_masculin(pick(CADRAGES, "c")), angle=au_masculin(pick(ANGLES[prise], "a")),
                        lumiere=pick(LUMIERES, "l"), tenue=pick(vest, "t"),
                        cheveux=pick(coif, "h"), accessoire=pick(accs[sc], "x")))
    return out, deja


if __name__ == "__main__":
    n_poses = sum(len(v[1]) for v in SCENES.values())
    combis = n_poses * len(CADRAGES) * 5 * len(LUMIERES)
    print(f"{len(SCENES)} scenes, {n_poses} poses distinctes")
    print(f"combinaisons scene+pose+cadrage+angle+lumiere = {combis:,}")
    lot, _ = tirage(5, seed=1)
    for x in lot:
        print(f"\n[{x['scene']}] ({x['prise']}, regard {x['regard']})\n  {x['pose']}")
