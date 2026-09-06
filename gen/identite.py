# -*- coding: utf-8 -*-
"""
Identite civile de la femme + texte a incruster sur chaque photo.

Le texte reprend exactement le gabarit du compte source, qui est
la vraie mecanique du format : chaque slide ne livre qu'un seul
morceau d'information, ce qui force le swipe jusqu'au bout.

  1  Prenom : X
  2  Age : X ans
  3  Profession : X
  4  Recherche : X
  5  Si tu aimes son profil presente toi en commentaire
"""
import json, os, random

REGISTRE = "gen/_prenoms_utilises.json"

# Prenoms credibles par tranche d'age (generation reelle correspondante)
PRENOMS = {
 "38_45": ["Sandrine", "Céline", "Aurélie", "Stéphanie", "Virginie", "Karine", "Delphine",
           "Émilie", "Julie", "Audrey", "Laetitia", "Sophie", "Magali", "Elodie", "Vanessa",
           "Séverine", "Christelle", "Sabrina", "Amélie", "Gaëlle", "Mélanie", "Cindy",
           "Jessica", "Marion", "Charlotte", "Anne-Sophie", "Ludivine", "Estelle"],
 "46_55": ["Nathalie", "Isabelle", "Sylvie", "Corinne", "Valérie", "Véronique", "Patricia",
           "Christine", "Catherine", "Brigitte", "Pascale", "Florence", "Laurence", "Fabienne",
           "Carole", "Muriel", "Sandrine", "Agnès", "Béatrice", "Hélène", "Dominique",
           "Evelyne", "Chantal", "Martine", "Geneviève"],
 "56_65": ["Martine", "Monique", "Françoise", "Danielle", "Jocelyne", "Annie", "Marie-Claude",
           "Josiane", "Nicole", "Chantal", "Michèle", "Colette", "Bernadette", "Odile"],
}

# Metiers repris du compte source, elargis a des metiers feminins courants en France
METIERS = [
 "Infirmière", "Aide-soignante", "Coiffeuse", "Secrétaire", "Assistante maternelle",
 "Vendeuse", "Enseignante", "Professeur des écoles", "Auxiliaire de vie sociale",
 "Agente immobilière", "Conseillère clientèle", "Comptable", "Esthéticienne",
 "Serveuse", "Assistante de direction", "Aide à domicile", "Préparatrice en pharmacie",
 "Éducatrice spécialisée", "Responsable de rayon", "Fleuriste", "Sage-femme",
 "Assistante sociale", "Orthophoniste", "Vétérinaire", "Directrice des ressources humaines",
 "Gestionnaire de paie", "Agent administratif", "Puéricultrice", "Kinésithérapeute",
 "Chargée de clientèle", "Auxiliaire de puériculture", "Technicienne de laboratoire",
]

RECHERCHES = [
 "Relation sérieuse",
 "Relation sans prise de tête",
 "Relation sérieuse sans prise de tête",
 "Quelqu'un d'actif",
 "Quelqu'un de sincère",
 "Une belle histoire",
 "Une relation durable",
 "Quelqu'un qui la fasse rire",
]

CTA = [
 "Si tu aimes son profil présente toi en commentaire \U0001F447\U0001F60A",
 "Si tu aimes son profil clique sur le lien en bio \U0001F447\U0001F60A",
 "Présente toi en commentaire si elle te plaît \U0001F447\U0001F60A",
]


def _tranche(age):
    if age <= 45:
        return "38_45"
    if age <= 55:
        return "46_55"
    return "56_65"


def _charger():
    if os.path.exists(REGISTRE):
        try:
            return json.load(open(REGISTRE, encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return []          # registre illisible : on repart proprement
    return []


def _sauver(l):
    json.dump(l[-60:], open(REGISTRE, 'w', encoding='utf-8'), indent=0)


def identite(age, rnd=None, memoriser=True):
    """Prenom (non reutilise recemment), metier, recherche, et les 5 textes a incruster."""
    rnd = rnd or random.Random()
    recents = _charger()
    pool = PRENOMS[_tranche(age)]
    libres = [p for p in pool if p not in recents[-25:]] or pool
    prenom = rnd.choice(libres)
    if memoriser:                # la simple lecture de la librairie ne consomme pas de prenom
        _sauver(recents + [prenom])

    metier = rnd.choice(METIERS)
    recherche = rnd.choice(RECHERCHES)
    cta = rnd.choice(CTA)
    return {
        "prenom": prenom,
        "age": age,
        "metier": metier,
        "recherche": recherche,
        "textes": [
            f"Prénom : {prenom}",
            f"Âge : {age} ans",
            f"Profession : {metier}",
            f"Recherche : {recherche}",
            cta,
        ],
    }


if __name__ == "__main__":
    r = random.Random()
    for age in (41, 49, 58):
        i = identite(age, r)
        print(f"\n--- {age} ans")
        for t in i["textes"]:
            print("   ", t)


# ===========================================================================
#                              VERSION MASCULINE
# ===========================================================================

PRENOMS_H = {
 "38_45": ["Sébastien", "Nicolas", "Julien", "Cédric", "Fabien", "Guillaume", "Vincent",
           "Mathieu", "Romain", "Jérôme", "Damien", "Ludovic", "Grégory", "Anthony",
           "Alexandre", "Benoît", "Emmanuel", "Yannick", "Sylvain", "David", "Arnaud",
           "Maxime", "Olivier", "Franck", "Jonathan", "Aurélien"],
 "46_55": ["Laurent", "Christophe", "Stéphane", "Frédéric", "Thierry", "Éric", "Pascal",
           "Bruno", "Philippe", "Hervé", "Didier", "Patrice", "Gilles", "Xavier",
           "Emmanuel", "Franck", "Denis", "Jean-Marc", "Marc", "Fabrice", "Antoine",
           "Régis", "Serge", "Alain"],
 "56_65": ["Alain", "Michel", "Patrick", "Bernard", "Gérard", "Daniel", "Jean-Pierre",
           "Claude", "Dominique", "Jacques", "Yves", "Guy", "Francis", "André"],
}

METIERS_H = [
 "Artisan menuisier", "Chef de chantier", "Électricien", "Plombier chauffagiste",
 "Technicien de maintenance", "Chauffeur poids lourd", "Cuisinier", "Boulanger",
 "Commercial", "Agent immobilier", "Pompier", "Infirmier", "Kinésithérapeute",
 "Professeur des écoles", "Ingénieur", "Comptable", "Mécanicien", "Paysagiste",
 "Charpentier", "Conducteur de travaux", "Agriculteur", "Responsable logistique",
 "Développeur", "Vétérinaire", "Éducateur spécialisé", "Ambulancier",
 "Chef d'équipe", "Peintre en bâtiment", "Serrurier", "Technicien réseau",
]

RECHERCHES_H = [
 "Relation sérieuse",
 "Relation sans prise de tête",
 "Relation sérieuse sans prise de tête",
 "Quelqu'un d'actif",
 "Quelqu'un de sincère",
 "Une belle histoire",
 "Une relation durable",
 "Quelqu'un qui le fasse rire",
]

CTA_H = [
 "Si tu aimes son profil présente toi en commentaire \U0001F447\U0001F60A",
 "Si tu aimes son profil clique sur le lien en bio \U0001F447\U0001F60A",
 "Présente toi en commentaire s'il te plaît \U0001F447\U0001F60A",
]

REGISTRE_H = "gen/_prenoms_h_utilises.json"


def identite_h(age, rnd=None, memoriser=True):
    """Meme role que identite(), version masculine, avec son propre registre
    de prenoms pour ne pas se marcher dessus avec celui des femmes."""
    rnd = rnd or random.Random()
    recents = []
    if os.path.exists(REGISTRE_H):
        try:
            recents = json.load(open(REGISTRE_H, encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            recents = []
    pool = PRENOMS_H[_tranche(age)]
    libres = [p for p in pool if p not in recents[-25:]] or pool
    prenom = rnd.choice(libres)
    if memoriser:
        json.dump((recents + [prenom])[-60:], open(REGISTRE_H, 'w', encoding='utf-8'), indent=0)

    metier = rnd.choice(METIERS_H)
    recherche = rnd.choice(RECHERCHES_H)
    return {
        "prenom": prenom, "age": age, "metier": metier, "recherche": recherche,
        "textes": [
            f"Prénom : {prenom}",
            f"Âge : {age} ans",
            f"Profession : {metier}",
            f"Recherche : {recherche}",
            rnd.choice(CTA_H),
        ],
    }
