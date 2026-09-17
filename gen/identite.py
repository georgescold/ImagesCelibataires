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

Les prenoms sortent du fichier de l'INSEE, cohorte de naissance par cohorte de
naissance, et aucun ne revient avant quarante profils. Voir PRENOMS plus bas.
"""
import datetime, json, os, random

REGISTRE = "gen/_prenoms_utilises.json"

# Un prenom ne peut pas revenir avant FENETRE profils. Chaque banque en compte
# 60 : meme si les 40 derniers profils tombaient tous dans la meme cohorte, il
# en resterait vingt de libres, donc la regle tient toujours.
FENETRE = 40
MEMOIRE = 2 * FENETRE          # ce qu'on garde du registre sur le disque

# --- Les banques sont indexees par ANNEE DE NAISSANCE, pas par age -----------
#
# Les prenoms suivent la generation, pas l'age : une femme de 45 ans est nee en
# 1981 aujourd'hui et en 1991 dans dix ans, et ce ne sont pas les memes prenoms.
# Ancrer les banques sur l'annee de naissance les garde justes sans y revenir.
#
# Chaque liste est le classement reel des 60 prenoms les plus donnes a cette
# cohorte, calcule sur le fichier des prenoms de l'INSEE (naissances 1900-2022,
# www.insee.fr/fr/statistiques/7633685), les variantes accentuees fusionnees
# avec leur forme non accentuee — l'etat civil enregistre 182 343 « JEROME »
# contre 22 847 « JÉRÔME », et c'est le meme prenom. Ces soixante prenoms
# couvrent de 46 % (nes 1997-2004) a 81 % (hommes nes 1956-1964) des naissances
# de leur cohorte.
PRENOMS = {
 (1956, 1964): [
   "Sylvie", "Catherine", "Marie", "Martine", "Christine", "Brigitte", "Isabelle",
   "Patricia", "Véronique", "Françoise", "Chantal", "Dominique", "Corinne", "Nadine",
   "Pascale", "Nathalie", "Annie", "Béatrice", "Évelyne", "Monique", "Laurence", "Nicole",
   "Anne", "Claudine", "Michèle", "Élisabeth", "Marie-Christine", "Fabienne", "Florence",
   "Jocelyne", "Valérie", "Annick", "Joëlle", "Agnès", "Christiane", "Maryse", "Bernadette",
   "Jacqueline", "Anne-Marie", "Josiane", "Hélène", "Muriel", "Mireille", "Sophie",
   "Ghislaine", "Odile", "Danielle", "Geneviève", "Régine", "Sylviane", "Myriam",
   "Michelle", "Carole", "Marie-Claude", "Colette", "Viviane", "Marie-Hélène", "Danièle",
   "Marie-France", "Maryline"
 ],
 (1965, 1972): [
   "Nathalie", "Isabelle", "Valérie", "Sylvie", "Sandrine", "Catherine", "Véronique",
   "Laurence", "Christine", "Corinne", "Sophie", "Florence", "Marie", "Christelle",
   "Patricia", "Anne", "Karine", "Fabienne", "Carole", "Béatrice", "Stéphanie", "Françoise",
   "Cécile", "Céline", "Pascale", "Virginie", "Martine", "Delphine", "Agnès", "Sabine",
   "Muriel", "Nadine", "Élisabeth", "Caroline", "Hélène", "Emmanuelle", "Myriam",
   "Brigitte", "Chantal", "Dominique", "Frédérique", "Magali", "Nadia", "Maria", "Sandra",
   "Séverine", "Murielle", "Claire", "Annie", "Évelyne", "Sonia", "Mireille", "Géraldine",
   "Marie-Christine", "Claudine", "Lydie", "Christel", "Laure", "Marie-Laure",
   "Marie-Pierre"
 ],
 (1973, 1980): [
   "Stéphanie", "Sandrine", "Céline", "Nathalie", "Virginie", "Christelle", "Isabelle",
   "Sophie", "Séverine", "Karine", "Delphine", "Laëtitia", "Valérie", "Marie", "Sandra",
   "Caroline", "Aurélie", "Cécile", "Sylvie", "Audrey", "Anne", "Angélique", "Sabrina",
   "Véronique", "Alexandra", "Magali", "Carole", "Sonia", "Laurence", "Florence",
   "Catherine", "Carine", "Émilie", "Hélène", "Vanessa", "Emmanuelle", "Christine", "Julie",
   "Estelle", "Claire", "Nadège", "Nadia", "Gaëlle", "Mélanie", "Patricia", "Corinne",
   "Géraldine", "Élodie", "Fabienne", "Laure", "Myriam", "Béatrice", "Sabine", "Peggy",
   "Aurore", "Ingrid", "Fanny", "Natacha", "Élisabeth", "Muriel"
 ],
 (1981, 1988): [
   "Aurélie", "Émilie", "Élodie", "Céline", "Julie", "Marie", "Audrey", "Stéphanie",
   "Laëtitia", "Virginie", "Sophie", "Mélanie", "Vanessa", "Caroline", "Sabrina",
   "Jennifer", "Jessica", "Amandine", "Marion", "Angélique", "Claire", "Delphine", "Cindy",
   "Pauline", "Cécile", "Sandrine", "Amélie", "Aurore", "Alexandra", "Christelle", "Hélène",
   "Nathalie", "Lucie", "Charlotte", "Laura", "Fanny", "Sarah", "Sandra", "Anne", "Gaëlle",
   "Marine", "Camille", "Anaïs", "Laure", "Isabelle", "Emmanuelle", "Séverine", "Adeline",
   "Sonia", "Magali", "Coralie", "Mathilde", "Ludivine", "Florence", "Carole", "Aline",
   "Karine", "Élise", "Estelle", "Anne-Sophie"
 ],
 (1989, 1996): [
   "Laura", "Marie", "Marine", "Julie", "Camille", "Élodie", "Marion", "Pauline", "Anaïs",
   "Manon", "Mélanie", "Sarah", "Mathilde", "Audrey", "Justine", "Aurélie", "Émilie",
   "Amandine", "Charlotte", "Léa", "Chloé", "Morgane", "Lucie", "Céline", "Claire",
   "Sophie", "Mélissa", "Cindy", "Amélie", "Caroline", "Laëtitia", "Fanny", "Jessica",
   "Coralie", "Jennifer", "Alexandra", "Adeline", "Margaux", "Clémence", "Estelle",
   "Ophélie", "Stéphanie", "Océane", "Charlène", "Angélique", "Noémie", "Alice", "Hélène",
   "Sabrina", "Maëva", "Aurore", "Juliette", "Cécile", "Sandra", "Élise", "Marina",
   "Laurie", "Lisa", "Alexia", "Ludivine"
 ],
 (1997, 2004): [
   "Léa", "Manon", "Camille", "Chloé", "Marie", "Emma", "Océane", "Sarah", "Laura", "Julie",
   "Mathilde", "Pauline", "Anaïs", "Clara", "Marine", "Lucie", "Inès", "Justine", "Lisa",
   "Juliette", "Morgane", "Marion", "Charlotte", "Éva", "Maëva", "Émilie", "Jade",
   "Mélissa", "Margaux", "Noémie", "Louise", "Amandine", "Célia", "Élisa", "Clémence",
   "Amélie", "Romane", "Mélanie", "Alice", "Élodie", "Lola", "Jeanne", "Margot", "Élise",
   "Alicia", "Audrey", "Zoé", "Carla", "Claire", "Léna", "Laurine", "Fanny", "Agathe",
   "Coralie", "Valentine", "Solène", "Alexia", "Lou", "Maëlle", "Ambre"
 ],
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


def _cohorte(banques, age):
    """La banque dont la tranche de naissance contient cette personne."""
    naissance = datetime.date.today().year - age
    for bornes in sorted(banques):                   # des plus agees aux plus jeunes
        if naissance <= bornes[1]:
            return banques[bornes]
    return banques[max(banques)]


def _charger(chemin=REGISTRE):
    if os.path.exists(chemin):
        try:
            return json.load(open(chemin, encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return []          # registre illisible : on repart proprement
    return []


def _sauver(l, chemin=REGISTRE):
    json.dump(l[-MEMOIRE:], open(chemin, 'w', encoding='utf-8'), indent=0)


def _choisir(pool, recents, rnd):
    """Un prenom qui n'a pas servi depuis FENETRE profils.

    Le repli sur le moins recemment servi ne devrait jamais s'appliquer, 60
    prenoms suffisant a une fenetre de 40 ; il est la pour que la regle ne
    depende pas de cette arithmetique. Il ne tire PAS au hasard dans la banque
    entiere : ce serait rendre le prenom le plus recent aussi probable que les
    autres, exactement ce qu'on cherche a eviter.
    """
    bloques = set(recents[-FENETRE:])
    libres = [p for p in pool if p not in bloques]
    if libres:
        return rnd.choice(libres)
    rang = {p: i for i, p in enumerate(recents)}
    return min(pool, key=lambda p: rang.get(p, -1))


def identite(age, rnd=None, memoriser=True):
    """Prenom (pas revu depuis 40 profils), metier, recherche, et les 5 textes."""
    rnd = rnd or random.Random()
    recents = _charger()
    prenom = _choisir(_cohorte(PRENOMS, age), recents, rnd)
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


# ===========================================================================
#                              VERSION MASCULINE
# ===========================================================================

PRENOMS_H = {
 (1956, 1964): [
   "Philippe", "Patrick", "Jean", "Pascal", "Alain", "Michel", "Thierry", "Éric",
   "Christian", "Didier", "Dominique", "Bruno", "Daniel", "Bernard", "Gilles", "Pierre",
   "Marc", "Jean-Pierre", "Serge", "Gérard", "Jean-Luc", "Claude", "François", "Jacques",
   "Laurent", "Denis", "Patrice", "Frédéric", "Joël", "Yves", "Hervé", "Jean-Claude",
   "Christophe", "Jean-Marc", "Olivier", "André", "Francis", "Jean-Michel", "Guy",
   "Jean-François", "Stéphane", "Jean-Paul", "Jean-Louis", "Franck", "Robert", "Jean-Marie",
   "René", "Gilbert", "Fabrice", "Jean-Jacques", "Georges", "Joseph", "Luc", "Vincent",
   "Jacky", "Richard", "Lionel", "Roger", "Henri", "Régis"
 ],
 (1965, 1972): [
   "Christophe", "Laurent", "Philippe", "Stéphane", "Éric", "Thierry", "Frédéric", "Pascal",
   "Olivier", "David", "Franck", "Bruno", "Patrick", "Jean", "Didier", "Alain", "Fabrice",
   "Michel", "Hervé", "Dominique", "Emmanuel", "Christian", "Gilles", "Sébastien", "Jérôme",
   "François", "Marc", "Pierre", "Nicolas", "Vincent", "Patrice", "Denis", "Daniel",
   "Jean-Luc", "Sylvain", "Jean-François", "Xavier", "Lionel", "Jean-Marc", "Jean-Pierre",
   "Jean-Michel", "Arnaud", "Serge", "Ludovic", "Yannick", "Claude", "Richard", "Joël",
   "Benoît", "Bernard", "José", "Yves", "Bertrand", "Jacques", "Régis", "Jean-Philippe",
   "Fabien", "Jean-Christophe", "Yann", "Jean-Claude"
 ],
 (1973, 1980): [
   "Sébastien", "David", "Christophe", "Frédéric", "Stéphane", "Nicolas", "Jérôme",
   "Olivier", "Laurent", "Cédric", "Julien", "Vincent", "Ludovic", "Éric", "Guillaume",
   "Arnaud", "Fabrice", "Franck", "Alexandre", "Philippe", "Michaël", "Sylvain", "Grégory",
   "Mickaël", "Emmanuel", "Cyril", "Benoît", "Fabien", "Thierry", "Jean", "Pascal",
   "François", "Xavier", "Thomas", "Pierre", "Yann", "Yannick", "Bruno", "Damien",
   "Anthony", "Mathieu", "Marc", "Lionel", "Patrick", "Samuel", "Hervé", "Patrice", "Loïc",
   "Raphaël", "Benjamin", "Cyrille", "Michel", "Jean-François", "Matthieu", "Romain",
   "Bertrand", "Antoine", "Gilles", "Didier", "Daniel"
 ],
 (1981, 1988): [
   "Julien", "Nicolas", "Sébastien", "Guillaume", "Alexandre", "Romain", "David", "Thomas",
   "Anthony", "Cédric", "Jérémy", "Jonathan", "Vincent", "Mathieu", "Mickaël", "Jérôme",
   "Damien", "Christophe", "Pierre", "Benjamin", "Frédéric", "Ludovic", "Kévin", "Fabien",
   "Grégory", "Olivier", "Maxime", "Arnaud", "Stéphane", "Benoît", "Sylvain", "Aurélien",
   "Laurent", "Florian", "Michaël", "Matthieu", "Antoine", "Loïc", "Cyril", "François",
   "Jean", "Adrien", "Clément", "Florent", "Xavier", "Rémi", "Emmanuel", "Yannick",
   "Franck", "Yoann", "Yann", "Alexis", "Marc", "Philippe", "Éric", "Samuel", "Mohamed",
   "Fabrice", "Raphaël", "Lionel"
 ],
 (1989, 1996): [
   "Kévin", "Thomas", "Nicolas", "Alexandre", "Maxime", "Julien", "Anthony", "Romain",
   "Florian", "Guillaume", "Jérémy", "Quentin", "Benjamin", "Antoine", "Pierre", "Clément",
   "Vincent", "Alexis", "Mathieu", "Jonathan", "Valentin", "Adrien", "Sébastien", "Jordan",
   "Damien", "David", "Mickaël", "Loïc", "Dylan", "Paul", "Aurélien", "Matthieu", "Lucas",
   "Cédric", "Arnaud", "Rémi", "Baptiste", "Florent", "Simon", "Benoît", "Hugo",
   "Christopher", "Fabien", "Thibault", "Jérôme", "Ludovic", "Corentin", "François",
   "Bastien", "Arthur", "Raphaël", "Steven", "Gaëtan", "Victor", "Louis", "Cyril",
   "Sylvain", "Axel", "Théo", "Christophe"
 ],
 (1997, 2004): [
   "Thomas", "Lucas", "Théo", "Hugo", "Maxime", "Alexandre", "Quentin", "Nicolas",
   "Antoine", "Clément", "Alexis", "Romain", "Valentin", "Julien", "Enzo", "Louis",
   "Florian", "Dylan", "Paul", "Pierre", "Nathan", "Baptiste", "Kévin", "Benjamin", "Léo",
   "Anthony", "Arthur", "Guillaume", "Adrien", "Tom", "Corentin", "Axel", "Mathieu",
   "Mathis", "Vincent", "Victor", "Jérémy", "Raphaël", "Jules", "Maxence", "Bastien",
   "Simon", "Jordan", "Yanis", "Loïc", "Damien", "Samuel", "Dorian", "Rémi", "Mattéo",
   "Thibault", "Tristan", "Matthieu", "Gabriel", "Aurélien", "Martin", "Killian", "Mohamed",
   "Mathéo", "David"
 ],
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
    recents = _charger(REGISTRE_H)
    prenom = _choisir(_cohorte(PRENOMS_H, age), recents, rnd)
    if memoriser:
        _sauver(recents + [prenom], REGISTRE_H)

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


def _simuler(banques, profils=400, graine=0):
    """Tire `profils` prenoms d'affilee, ages au hasard entre 30 et 70, et rend
    le plus court ecart observe entre deux emplois d'un meme prenom.
    En memoire : la verification ne touche pas au registre du disque."""
    rnd = random.Random(graine)
    recents, vu, ecart = [], {}, 10 ** 9
    for i in range(profils):
        p = _choisir(_cohorte(banques, rnd.randint(30, 70)), recents, rnd)
        if p in vu:
            ecart = min(ecart, i - vu[p])      # profils separant les deux emplois
        vu[p] = i
        recents.append(p)
    return ecart, len(vu)


if __name__ == "__main__":
    annee = datetime.date.today().year
    for etiquette, banques in (("femmes", PRENOMS), ("hommes", PRENOMS_H)):
        print(f"\n--- {etiquette}")
        for bornes in sorted(banques):
            a0, a1 = bornes
            print(f"  nes {a0}-{a1}  ({annee - a1} a {annee - a0} ans) : "
                  f"{len(banques[bornes])} prenoms, de {banques[bornes][0]} a {banques[bornes][-1]}")
        ecart, distincts = _simuler(banques)
        print(f"  400 profils : {distincts} prenoms differents, "
              f"plus court retour au bout de {ecart} profils (regle : {FENETRE})")

    r = random.Random()
    for age in (41, 49, 58):
        i = identite(age, r, memoriser=False)     # un essai ne consomme pas de prenom
        print(f"\n--- {age} ans")
        for t in i["textes"]:
            print("   ", t)
