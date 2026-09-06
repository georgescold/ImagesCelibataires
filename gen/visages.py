# -*- coding: utf-8 -*-
"""
Generateur de visages singuliers.

Probleme resolu : sans contrainte, les modeles convergent vers un "visage moyen"
(symetrique, nez droit, machoire fine, peau lisse) qui se lit immediatement comme IA.
Ici on force des traits rares et on impose 2 signes particuliers par visage.
"""
import random

ORIGINES = [
 "white French from Normandy, pale skin that reddens easily",
 "French of Algerian descent, olive skin, very dark hair",
 "French of Portuguese descent, warm olive skin, thick dark hair",
 "French of Italian descent, tanned skin, strong features",
 "French from the Antilles, deep brown skin, tight dark curls",
 "white French from Brittany, very fair skin, light eyes",
 "French of Vietnamese descent, straight black hair, monolid eyes",
 "French of Spanish descent, golden skin, dark almond eyes",
 "French of Polish descent, broad pale face, ash blonde hair",
 "French of Moroccan descent, honey skin, thick eyebrows",
 "mixed French and West African, warm brown skin, freckles across the nose",
 "white French from the Auvergne, ruddy weathered complexion",
]

VISAGE = [
 "a long oval face with soft cheeks",
 "a wide face with high round cheekbones",
 "a square jaw and a short neck",
 "a small pointed chin and a high forehead",
 "a full face with plump cheeks",
 "a slightly asymmetric face, one side a little lower than the other",
 "a heart-shaped face, wide forehead and narrow chin",
 "an even oval face with a strong straight jaw",
]

NEZ = [
 "a large nose with a bump on the bridge",
 "a wide nose with broad nostrils",
 "a long straight nose",
 "a small upturned nose",
 "a rounded nose with a soft tip",
 "a fine narrow nose",
 "a neat button nose",
]

YEUX = [
 "small deep-set eyes with heavy lids",
 "large round eyes",
 "narrow eyes with crow's feet at the corners",
 "hooded eyes where the lid covers most of the crease",
 "wide-set eyes with faint under-eye shadows",
 "close-set eyes under a strong brow",
 "one eye slightly smaller than the other",
 "pale grey-blue eyes",
 "very dark brown eyes",
 "green eyes with a warm brown ring round the pupil",
 "hazel eyes that turn down slightly at the outer corners",
]

BOUCHE = [
 "thin lips that narrow when she smiles",
 "a full lower lip and a thinner upper lip",
 "a slight overbite",
 "a small gap between her two front teeth",
 "slightly crooked lower teeth",
 "a wide mouth",
 "full even lips",
 "one canine set a little forward",
]

SOURCILS = [
 "sparse over-plucked eyebrows filled in with pencil",
 "thick natural dark eyebrows",
 "thin arched eyebrows tattooed a shade too dark",
 "pale fine eyebrows",
 "one eyebrow slightly higher than the other",
 "straight even eyebrows, untouched",
]

PEAU = [
 "clear skin with fine lines at the corners of the eyes",
 "a light scatter of freckles across the nose",
 "healthy skin with visible pores and a slight shine on the forehead",
 "smooth skin with faint laughter lines",
 "lightly tanned skin with a few small sun spots on the cheekbones",
 "even skin with a faint blush high on the cheeks",
 "well-kept skin with soft lines on the forehead",
]

# maquillage : les femmes du compte source ont toutes fait un effort
MAQUILLAGE = [
 "Her makeup is done and clearly visible: mascara, a fine eyeliner flick slightly uneven between the two eyes, groomed brows, a natural lipstick.",
 "Her makeup is done: mascara, warm eyeshadow, defined brows and a soft rose lip, with the foundation stopping a shade too abruptly at the jaw.",
 "Her makeup is done: heavy mascara, a smoky eye a little smudged under one eye, nude lip, well-shaped brows.",
 "Her makeup is done: a bold red lipstick slightly outside the lip line on one side, mascara, groomed brows.",
 "Her makeup is done: mascara, blusher high on the cheeks, brows filled in with pencil, a glossy lip.",
 "Her makeup is minimal but deliberate: mascara, a touch of bronzer, brows brushed up, tinted lip balm.",
]

CHEVEUX = [
 "shoulder-length chestnut hair, freshly coloured",
 "a well-cut silver bob, deliberately grey and well kept",
 "long dark hair in soft layers",
 "thick wavy shoulder-length hair",
 "a warm blonde balayage, well maintained",
 "a blunt chin-length bob",
 "long dark hair pulled back into a neat ponytail",
 "short curly hair with volume",
 "shoulder-length honey blonde hair",
 "hair dyed auburn red, glossy",
 "dark hair with a few deliberate grey streaks at the temples",
 "light brown hair with a side fringe",
 "long hair with sun-lightened ends",
 "a shoulder-length cut with a soft curtain fringe",
]

# signes particuliers. Ceux prefixes "GDB:" sont des grains de beaute :
# le tirage n'en autorise qu'UN SEUL par visage (sinon le modele en seme partout).
SIGNES = [
 "GDB:a small beauty spot just above her upper lip on the left",
 "GDB:a single small mole high on one cheekbone",
 "a small dimple in her chin",
 "a nose piercing, a tiny stud",
 "a small delicate tattoo on her inner forearm, no lettering, just a shape",
 "a gap-toothed smile she does not hide",
 "one dimple that only shows on the left cheek",
 "a slightly uneven hairline",
 "ears pierced twice on one side, once on the other",
 "very long dark eyelashes",
 "a widow's peak",
 "one eyebrow slightly higher than the other",
 "a fine gold chain she never takes off",
 "a small silver ring on her right index finger",
 "a low husky-looking set to her mouth",
 "slightly hooded eyelids that make her look amused",
]

MORPHO = [
 "slim with a toned figure, she clearly exercises",
 "slender with narrow shoulders",
 "an athletic build with defined arms",
 "a curvy hourglass figure",
 "tall and slim",
 "petite and slim",
 "average build, well proportioned",
 "slim with long legs",
 "softly curvy, carrying a little weight but well proportioned",
 "lean and fit",
]

# niveau d'attrait : la majorite des femmes du compte source sont "ordinaires mais avenantes"
ATTRAIT = [
 "She is a beautiful woman, the kind who turns heads, but in a natural everyday way rather than a magazine way.",
 "She is very pretty, with warm attractive features that people comment on.",
 "She is a good-looking woman who has clearly kept herself in shape.",
 "She is strikingly attractive, with an open face and a warm smile.",
 "She is beautiful in a mature, self-assured way.",
]


def visage(seed=None, age=42, avec_signes=False):
    """Visage singulier ET attirant. L'attrait et le maquillage sont places en tete :
    flux-2-pro pondere beaucoup plus fortement les premiers tokens du prompt."""
    r = random.Random(seed)
    # un seul grain de beaute autorise par visage
    gdb = [x for x in SIGNES if x.startswith("GDB:")]
    autres = [x for x in SIGNES if not x.startswith("GDB:")]
    if r.random() < 0.35:
        signes = [r.choice(gdb).replace("GDB:", ""), r.choice(autres)]
        r.shuffle(signes)
    else:
        signes = r.sample(autres, 2)
    d = (f"A beautiful French woman of {age}. {r.choice(ATTRAIT)} {r.choice(MAQUILLAGE)} "
            f"She is {r.choice(MORPHO)}. She has {r.choice(CHEVEUX)}. "
            f"{r.choice(ORIGINES).capitalize()}. "
            f"Her face: {r.choice(VISAGE)}, {r.choice(NEZ)}, {r.choice(YEUX)}, "
            f"{r.choice(BOUCHE)}, {r.choice(SOURCILS)}. "
            f"Her skin shows {r.choice(PEAU)}, with real visible pores and no retouching. "
            f"Distinguishing features: {signes[0]}, and {signes[1]}. "
            "Apart from the two features listed above, her skin is clear: do NOT add any extra moles, "
            "beauty spots, skin tags or dark marks on her face, neck or chest. "
            "She is a specific real individual with her own particular face, not a generic symmetrical "
            "AI face, not airbrushed, not a fashion model. She is attractive but her face is slightly "
            f"asymmetric and human. She looks healthy and well groomed, and no older than {age}.")
    return (d, signes) if avec_signes else d


if __name__ == "__main__":
    import itertools
    total = 1
    for pool in (ORIGINES, VISAGE, NEZ, YEUX, BOUCHE, SOURCILS, PEAU, CHEVEUX, MORPHO, ATTRAIT, MAQUILLAGE):
        total *= len(pool)
    total *= len(SIGNES) * (len(SIGNES) - 1) // 2
    print(f"combinaisons de visages : {total:,}")
    for s in (1, 2, 3):
        print("\n---", s, "\n" + visage(seed=s, age=44))


# ===========================================================================
#                              VERSION MASCULINE
# ===========================================================================
# Meme principe que pour les femmes : des traits singuliers imposes, une
# beaute ordinaire plutot que magazine, et surtout pas de visage IA lisse.
# Ce qui remplace le maquillage ici, c'est la barbe et l'etat de la coupe.

ORIGINES_H = [
 "white French from Normandy, fair skin that reddens easily",
 "French of Algerian descent, olive skin, very dark hair",
 "French of Portuguese descent, warm olive skin, thick dark hair",
 "French of Italian descent, tanned skin, strong features",
 "French from the Antilles, deep brown skin, close-cut dark hair",
 "white French from Brittany, fair skin, light eyes",
 "French of Vietnamese descent, straight black hair",
 "French of Spanish descent, golden skin, dark eyes",
 "French of Polish descent, broad pale face, ash blond hair",
 "French of Moroccan descent, honey skin, thick eyebrows",
 "mixed French and West African, warm brown skin",
 "white French from the Auvergne, weathered outdoor complexion",
]

VISAGE_H = [
 "a long face with a strong straight jaw",
 "a wide face with high cheekbones",
 "a square heavy jaw and a thick neck",
 "a narrow face with a high forehead",
 "a rounded face with full cheeks",
 "a slightly asymmetric face, one side a little lower than the other",
 "an angular face with a defined jawline",
 "a broad face with a heavy brow ridge",
 "an oval face with soft features",
]

NEZ_H = [
 "a large nose with a bump on the bridge",
 "a wide nose with broad nostrils",
 "a long straight nose",
 "a rounded nose with a soft tip",
 "a fine narrow nose",
 "a nose that healed slightly crooked after a break",
 "a strong Roman nose",
]

YEUX_H = [
 "deep-set eyes under a heavy brow",
 "large round eyes",
 "narrow eyes with crow's feet at the corners",
 "hooded eyes",
 "wide-set eyes with faint shadows underneath",
 "one eye slightly smaller than the other",
 "pale grey-blue eyes",
 "very dark brown eyes",
 "green eyes with a warm ring round the pupil",
]

BOUCHE_H = [
 "thin lips",
 "a full lower lip",
 "a slight overbite",
 "a small gap between the two front teeth",
 "a wide mouth",
 "even lips and a slightly crooked smile",
]

# la barbe joue ici le role que le maquillage joue pour les femmes :
# c'est le detail d'entretien qui se lit immediatement
BARBES = [
 "He has a short well-kept beard with a few grey hairs in it.",
 "He has three-day stubble, deliberately kept.",
 "He is clean-shaven, with a faint shadow along the jaw.",
 "He has a full beard, trimmed but not sculpted.",
 "He has a moustache and light stubble on the cheeks.",
 "He has a close-trimmed beard that is greyer than his hair.",
 "He is clean-shaven with a small nick from the razor on his jaw.",
]

PEAU_H = [
 "clear skin with lines at the corners of the eyes",
 "a light scatter of freckles across the nose",
 "healthy skin with visible pores and a slight shine on the forehead",
 "weathered skin from working outdoors",
 "lightly tanned skin with sun lines on the forehead",
 "even skin with a faint flush on the cheeks",
 "skin with soft horizontal lines on the forehead",
]

CHEVEUX_H_V = [
 "short dark hair, freshly cut",
 "salt-and-pepper hair kept short",
 "thick brown hair pushed back",
 "hair receding at the temples, kept short",
 "a close buzz cut, mostly grey",
 "wavy hair grown just past the ears",
 "short blond hair with a side parting",
 "dark hair thinning at the crown, cut short",
 "a shaved head",
 "curly short hair with volume",
 "light brown hair with a bit of length on top",
]

SIGNES_H = [
 "GDB:a small beauty spot on one cheek",
 "GDB:a single mole near the jawline",
 "a small scar through one eyebrow",
 "a dimple in the chin",
 "a faded tattoo on the forearm, no lettering, just a shape",
 "a gap-toothed smile he does not hide",
 "a slightly uneven hairline",
 "a small silver ring on one hand",
 "a leather-strap watch he never takes off",
 "one ear that sticks out a little more than the other",
 "very dark thick eyebrows",
 "a widow's peak",
 "a broken nose that never quite set straight",
 "hands that show manual work",
 "a fine chain at the neck",
]

MORPHO_H = [
 "tall and lean",
 "broad-shouldered and solidly built",
 "of average height, well proportioned",
 "stocky with thick forearms",
 "tall with a slight stoop",
 "athletic, he clearly trains",
 "slim with narrow shoulders",
 "carrying a little weight but well proportioned",
 "short and compact, muscular",
 "long-limbed and wiry",
]

ATTRAIT_H = [
 "He is a good-looking man in an ordinary, approachable way, the kind women notice.",
 "He is handsome without being polished, with a warm open face.",
 "He is attractive in a rugged, lived-in way.",
 "He has an easy, reassuring face that people trust straight away.",
 "He is good-looking in a quiet, understated way.",
]


def visage_h(seed=None, age=45, avec_signes=False):
    """Visage masculin singulier ET avenant, meme logique que pour les femmes :
    l'attrait et l'entretien sont places en tete de prompt."""
    r = random.Random(seed)
    gdb = [x for x in SIGNES_H if x.startswith("GDB:")]
    autres = [x for x in SIGNES_H if not x.startswith("GDB:")]
    if r.random() < 0.30:
        signes = [r.choice(gdb).replace("GDB:", ""), r.choice(autres)]
        r.shuffle(signes)
    else:
        signes = r.sample(autres, 2)

    d = (f"A good-looking French man of {age}. {r.choice(ATTRAIT_H)} {r.choice(BARBES)} "
         f"He is {r.choice(MORPHO_H)}. He has {r.choice(CHEVEUX_H_V)}. "
         f"{r.choice(ORIGINES_H).capitalize()}. "
         f"His face: {r.choice(VISAGE_H)}, {r.choice(NEZ_H)}, {r.choice(YEUX_H)}, {r.choice(BOUCHE_H)}. "
         f"His skin shows {r.choice(PEAU_H)}, with real visible pores and no retouching. "
         f"Distinguishing features: {signes[0]}, and {signes[1]}. "
         "Apart from the two features listed above, do NOT add any extra moles, "
         "beauty spots or dark marks on his face or neck. "
         "He is a specific real individual with his own particular face, not a generic symmetrical "
         "AI face, not airbrushed, not a male model. He is attractive but his face is slightly "
         f"asymmetric and human. He looks healthy and well groomed, and no older than {age}.")
    return (d, signes) if avec_signes else d
