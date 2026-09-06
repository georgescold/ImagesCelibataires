# Atelier carrousels

Générateur local de carrousels photo pour TikTok : 5 images d'une même personne
fictive, dans 5 lieux différents, prêtes à recevoir un texte incrusté.

Interface web locale, génération via l'API [fal](https://fal.ai).

---

## Lancer

Double-clic sur **`start.bat`**, ou :

```bash
python gen/serveur.py --ouvrir
```

Puis ouvrir **http://127.0.0.1:8420** — et pas `localhost` : sous Windows,
`localhost` se résout d'abord en IPv6, le serveur n'écoute qu'en IPv4, et
chaque requête attend deux secondes avant de retomber. Mesuré : 2051 ms
contre 2 ms.

### Prérequis

- Python 3.9+
- Pillow (`pip install pillow`) — `start.bat` l'installe si besoin
- Une clé fal dans un fichier `.env` à la racine :

```
FAL_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

Copier `.env.example` et y mettre sa clé. Le fichier `.env` n'est pas versionné.

---

## Ce que fait le pipeline

| Étape | Modèle | Prix |
|---|---|---|
| Photo 1, le hero (texte → image) | `fal-ai/flux-2-pro` | 0,030 $ |
| Photos 2 à 5 (même visage, image → image) | `fal-ai/flux-2-pro/edit` | 0,045 $ |

**0,21 $ le carrousel de 5 photos, environ 80 secondes.**

Ces deux modèles ont été retenus après un banc d'essai sur 14 modèles
text-to-image. Prix mesurés sur les autres candidats : `flux-2 klein 9B`
0,005 $ (le meilleur rapport qualité-prix, ~80 % du résultat pour six fois
moins cher), `flux-2 [dev]` 0,012 $, `mai-image-2.5` 0,0395 $,
`seedream v5 pro` 0,0675 $, `nano-banana-2` 0,080 $.

Après génération, chaque image passe par un post-traitement local gratuit
qui fait autant que le modèle : recadrage en 640×800, léger flou, bruit de
capteur, étalonnage doux, horizon de travers et double compression JPEG.
C'est ce qui transforme une image IA propre en photo qui sort d'un téléphone.

---

## Les règles, et d'où elles viennent

Le format a été reconstitué à partir d'un compte source analysé au scraper :
13 carrousels, 40 300 vues médianes, 144 700 au meilleur. Le chiffre qui
explique tout est le **ratio commentaires/likes de 14,4 %**, là où la normale
sur TikTok est de 1 à 3 %. Le compte ne fait pas de la belle photo, il
fabrique une machine à commentaires.

Constats repris dans le générateur :

- **38 ans et plus font 66 700 vues de moyenne, les moins de 38 ans 19 000.**
- Le visage n'est presque jamais centré, la tête est toujours inclinée.
- Un accessoire sert de prétexte à la photo.
- Au moins une photo où le sujet est minuscule dans le cadre.
- Les expressions sont retenues : pas de rire, pas de pose.
- Les scènes sont banales, voire répétitives : canapé, voiture, miroir, terrasse.
- Aucun texte dans l'image, y compris en arrière-plan.

---

## Structure

| Fichier | Rôle |
|---|---|
| `start.bat` | Lancement : trouve Python, vérifie Pillow, démarre tout |
| `gen/ouvre.bat` | Attend que le serveur réponde puis ouvre le navigateur |
| `gen/serveur.py` | Serveur local, API, vignettes, zip, archives, corbeille |
| `gen/interface.html` | Interface (relue à chaque requête, modifiable à chaud) |
| `gen/carrousel.py` | Le générateur complet |
| `gen/runner.py` | Appels fal, lecture de la clé |
| `gen/visages.py` | ~747 milliards de visages, versions féminine et masculine |
| `gen/poses.py` | 86 poses sûres, contraintes d'anatomie et de regard |
| `gen/lieux.py` | 225 fonds, carence de 30 générations avant réutilisation |
| `gen/filters.py` | Étalonnage doux et continu, par persona |
| `gen/identite.py` | Prénoms, métiers et textes à incruster |
| `gen/genre.py` | Conversion féminin → masculin des banques de textes |
| `gen/pipeline.py` | Post-traitement « vraie photo de téléphone » |

---

## Quelques partis pris

**Les poses à risque sont bannies, pas rafistolées.** 23 poses sur 86 ont été
supprimées parce que le modèle les rate systématiquement : troisième bras,
main désincarnée, articulation impossible. Contracter les deux biceps devant
un miroir reste faux même en écrivant explicitement « un seul bras levé, le
téléphone dans l'autre main » — le geste est trop associé à la symétrie dans
les données d'entraînement.

**Un fond ne peut pas revenir avant 30 générations.** À 5 photos par profil,
cela bloque 150 fonds en permanence, d'où les 225 de la banque. Le tirage
privilégie les types de scène dont la réserve est la plus libre, sinon un type
s'épuise localement. Vérifié par simulation sur 300 profils : zéro violation.

**Les banques de textes ne sont pas dupliquées pour les hommes, elles sont
converties.** La seule difficulté de l'anglais est « her », tantôt possessif
(`her free hand` → *his*) tantôt complément (`behind her` → *him*) ; la règle
qui tranche est ce qui suit le mot, avec une exception devant les déterminants
et les adverbes. Vérifié sur les 119 textes de la banque.

---

## Limite connue

**La cohérence du visage se dégrade sur environ une photo sur dix**, davantage
au-delà de 50 ans, et d'autant plus que les lumières des scènes tirées sont
éloignées les unes des autres. La parade actuelle est de régénérer la photo
fautive (0,045 $). Un contrôle automatique de ressemblance reste à faire.
