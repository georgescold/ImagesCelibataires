# -*- coding: utf-8 -*-
"""
Passage du feminin au masculin.

Les banques de poses, cadrages et lumieres ont ete ecrites au feminin.
Plutot que de les dupliquer — et de devoir corriger chaque correctif a deux
endroits — on les convertit.

Le seul cas ambigu de l'anglais est "her", qui est tantot possessif
("her free hand" -> his) tantot complement ("behind her" -> him).
La regle qui tranche est ce qui SUIT le mot : suivi d'un mot, c'est un
possessif ; suivi d'une ponctuation ou d'une fin de phrase, c'est un
complement. Verifie sur les 114 occurrences de la banque.
"""
import re

_REGLES = [
    (r"\bshe\b", "he"),
    (r"\bShe\b", "He"),
    (r"\bherself\b", "himself"),
    (r"\bhers\b", "his"),
    # Un possessif ne peut etre suivi ni d'un determinant, ni d'une conjonction,
    # ni d'un adverbe : "show her a second time" et "of her anywhere" sont des
    # complements. Cette exception passe AVANT la regle du possessif, sinon on
    # obtient "show his a second time".
    (r"\b[Hh]er\b(?=\s+(?:a|an|the|any|some|this|that|these|those|again|anywhere|"
     r"here|there|too|once|twice|either|only|and|or|but|so|then|now|first|second)\b)", "him"),
    # "her" suivi d'un mot -> possessif
    (r"\bher\b(?=\s+[A-Za-z])", "his"),
    (r"\bHer\b(?=\s+[A-Za-z])", "His"),
    # "her" en fin de groupe -> complement
    (r"\bher\b", "him"),
    (r"\bHer\b", "Him"),
    (r"\bwoman\b", "man"),
    (r"\bWoman\b", "Man"),
    (r"\bwomen\b", "men"),
]


def au_masculin(t):
    for motif, remplacement in _REGLES:
        t = re.sub(motif, remplacement, t)
    return t


# --------------------------------------------------------------- vestiaire
TENUES_H = [
    "a plain black t-shirt", "a grey marl hoodie", "a denim shirt over a white tee",
    "a navy crew-neck jumper", "a black long-sleeve top and jeans", "a dark green polo shirt",
    "a striped navy and white t-shirt", "a beige overshirt over a tee", "a black puffer jacket",
    "a plain white t-shirt", "a charcoal sweatshirt", "a light blue oxford shirt",
    "a burgundy knitted jumper", "a black training top and shorts", "a khaki field jacket",
    "a faded band-free plain grey tee",
]

CHEVEUX_H = [
    "hair short and slightly messy", "hair cropped short at the sides",
    "hair pushed back off the forehead", "hair a bit flat from a cap",
    "hair damp and pushed back", "hair with a side parting",
    "hair grown out and untidy", "hair buzzed short", "hair thinning at the crown",
]

# accessoires plausibles selon la scene, version masculine
ACC_H_PAR_SCENE = {
    "salon":          ["", "", "", " He is wearing reading glasses.", " He has a blanket over his legs."],
    "cuisine":        ["", "", "", " He is holding a mug.", " He has a tea towel over his shoulder."],
    "salle_de_bain":  ["", "", "", " He has shaving foam on the basin behind him.", " He has a towel round his neck."],
    "chambre":        ["", "", "", " He is wearing reading glasses.", " He has socks on and no shoes."],
    "voiture":        ["", "", " He has sunglasses pushed up on his head.", " He is holding a set of car keys.",
                       " He has a takeaway cup in one hand."],
    "salle_de_sport": ["", "", "", " He has earphones in.", " He has a water bottle beside him."],
    "terrasse_cafe":  ["", "", " He is wearing sunglasses.", " He has a canvas bag on the chair beside him."],
    "rue":            ["", "", " He is wearing a beanie.", " He has a rucksack on one shoulder.", " He is wearing a scarf."],
    "parc":           ["", "", " He is wearing sunglasses.", " He has a cap on.", " He has a dog lead in one hand."],
    "balcon":         ["", "", "", " He is holding a mug.", " He has sunglasses pushed up on his head."],
    "vacances":       ["", " He is wearing sunglasses.", " He has a cap on.", " He has a small backpack on one shoulder."],
    "soiree":         ["", "", " He has his sleeves rolled up.", " He has a jacket over the back of his chair."],
    "jardin":         ["", "", " He is wearing gardening gloves.", " He has a cap on.", " He is wearing wellies."],
    "travail":        ["", "", "", " He is wearing reading glasses.", " He has a plain lanyard round his neck."],
    "animal":         ["", "", "", " He is wearing reading glasses."],
}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "gen")
    from poses import SCENES, CADRAGES, ANGLES, LUMIERES, PHYSIQUE
    tout = ([p for v in SCENES.values() for p in v[1]] + CADRAGES + LUMIERES
            + list(PHYSIQUE.values()) + [a for l in ANGLES.values() for a in l])
    reste = [t for t in map(au_masculin, tout) if re.search(r"\b(she|her|hers|herself|woman)\b", t)]
    print(f"{len(tout)} textes convertis, {len(reste)} feminins residuels")
    for t in reste:
        print("  RESTE :", t)
    print("\n--- echantillon ---")
    for t in tout[:3] + CADRAGES[:2] + [PHYSIQUE["miroir"]]:
        print("\n  F:", t[:118])
        print("  H:", au_masculin(t)[:118])
