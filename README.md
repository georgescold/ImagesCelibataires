# Atelier carrousels

Générateur local de carrousels photo pour TikTok : 5 images d'une même personne
fictive, dans 5 lieux différents, prêtes à recevoir un texte incrusté.

Interface web locale, génération via l'API [fal](https://fal.ai).

---

## Deux façons de l'utiliser

**En ligne** — https://images-celibataires.vercel.app, protégé par mot de passe.
Fonctions Vercel, photos et bibliothèque dans Supabase.

**En local** — `start.bat`, tout sur la machine. `python gen/sauvegarde.py`
envoie vers Supabase ce qui manque en ligne.

---

## Lancer en local

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
| Contrôle de chaque photo (2 appels) | `openrouter/router/vision` | 0,001 $ |

**0,21 $ le carrousel de 5 photos, environ 80 secondes.** Le contrôle ajoute
0,006 $ et 25 secondes ; chaque photo qu'il fait refaire coûte 0,045 $ de plus.
Mesuré sur un profil de 52 ans : trois photos refaites, soit 0,35 $ au total.

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

## Photos en plus, reprises, et favoris

**« + 5 photos »** sur la fiche d'une personne repart de son visage plutôt que
d'en inventer un autre : sa description, ses signes particuliers et sa photo 1
sont déjà dans sa fiche. Les nouvelles photos reprennent les cinq mêmes textes
en boucle — prénom, âge, profession, recherche, appel à commenter — si bien
qu'un lot de cinq se poste tel quel comme un second carrousel de la même femme.
Environ 0,22 $ le lot.

La référence est l'image **brute** de la photo 1, pas celle qui est publiée :
celle-ci a reçu flou, bruit et double compression, et le modèle d'édition s'en
servirait pour dessiner un visage un peu plus flou à chaque fois. En ligne, la
photo brute est donc déposée dans le stockage à la génération.

**La petite flèche ↻**, en haut à droite de chaque photo, refait cette photo-là.
Même personne et **même décor** — le lieu est déjà consommé dans les registres, et
c'est lui qui donne sa place à la photo dans le carrousel — mais pose, cadrage,
angle, lumière et tenue sont retirés au sort, et la pose ratée est exclue du
tirage : la rejouer à l'identique la raterait encore. Environ 0,05 $, pas de
confirmation — la flèche est petite, posée sur la photo concernée, et c'est un
geste de retouche.

La photo 1 se refait depuis elle-même. Elle porte le visage de référence des
autres : la repasser en text-to-image donnerait un autre visage, qui ne collerait
plus aux suivantes. Le modèle d'édition, lui, garde les traits et redessine la
scène.

**L'étoile** met une personne dans l'onglet « Favoris », qui est une catégorie à
part et non un filtre : on y trouve aussi bien des femmes à poster que des
archivées. Une femme mise à la corbeille en sort. En local les favoris sont une
simple liste dans `gen/_favoris.json`, ce qui permet d'en marquer une générée
avant l'interface, qui n'a pas de `meta.json` ; en ligne, c'est une colonne de
la fiche.

---

## Sur iPad et téléphone

L'interface en ligne est faite pour être utilisée au doigt, et vérifiée de 320 px
(iPhone SE) à 1440 px : aucun défilement horizontal, aucune cible tactile sous
44 px, aucun texte sous 13 px.

**« Télécharger » range la photo dans la pellicule, pas dans Fichiers.** Sur iOS,
un lien de téléchargement dépose l'image dans l'app Fichiers, d'où il faut aller
la rechercher pour l'enregistrer à la main dans Photos — alors que c'est depuis
la pellicule qu'on poste. Au doigt, « Télécharger » ouvre donc la feuille de
partage du système, qui propose « Enregistrer l'image » ; « Tout télécharger » y
envoie toutes les photos d'un coup (« Enregistrer 13 images ») au lieu d'un zip.
Safari n'accepte de partager que dans la foulée d'un geste : si les images ont
mis trop longtemps à arriver, le bouton affiche « Toucher pour enregistrer », et
ce second toucher partage aussitôt, sans rien retélécharger. À la souris, rien ne
change — la feuille de partage de Windows serait une surprise.

**« Copier le texte »** passe par le presse-papiers moderne et, s'il refuse, par
une zone de texte sélectionnée — sur iOS, `select()` seul n'y sélectionne rien.

**La flèche ↻** reste discrète à la souris jusqu'au survol ; au doigt, où il n'y a
pas de survol, elle est toujours visible et à la taille d'un doigt.

Sur téléphone, les onglets se partagent la largeur en trois, compteur sous le
libellé ; l'étoile rejoint le nom ; les actions d'une fiche forment une grille de
deux colonnes ; et la dominante colorimétrique et le nom de dossier, qui servent
à l'atelier et pas au choix d'une photo, s'effacent. La ligne de compteurs de
l'en-tête, qui répète ceux des onglets, s'efface aussi : l'en-tête reste collé en
haut de l'écran, et chaque ligne y coûte en permanence.

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

## L'architecture en ligne

Le serveur local est un processus persistant qui écrit sur le disque ;
Vercel exécute des fonctions sans état sur un système de fichiers éphémère.
Trois choses ont donc été déplacées :

- les photos et les vignettes vont dans le bucket Supabase ;
- la bibliothèque et l'état des générations vivent dans des tables ;
- les registres de poses, lieux et prénoms sont téléchargés dans `/tmp`
  avant chaque génération, puis renvoyés au stockage — sans quoi deux
  générations successives rejoueraient les mêmes poses et les mêmes lieux.

Le code de génération n'est pas dupliqué : on recrée dans `/tmp`
l'arborescence qu'il attend et on le laisse travailler. Une génération prend
environ 95 secondes, sous la limite de 300 s déclarée dans `vercel.json`.

`web/app.html` est fabriqué depuis `gen/interface.html` par
`python gen/faire_web.py`, qui échoue bruyamment si une règle de
transformation ne s'applique plus. Une seule source pour les deux interfaces.
**On ne modifie jamais `web/app.html` à la main** : deux retouches faites
directement dedans — les appels de la carte de personnalité en ligne, et la
gestion d'erreur de la bibliothèque — ont été effacées par une régénération, et
la carte est restée cassée en ligne jusqu'à ce qu'on s'en aperçoive. Elles vivent
maintenant dans la source et dans les règles, et le fichier généré le rappelle
en tête.

Les vignettes sont servies directement par le CDN Supabase, avec des URL
signées fabriquées **en un seul appel groupé**. Les signer une par une
demandait 165 requêtes enchaînées, soit 24 secondes de bibliothèque ; les
faire transiter par une fonction coûtait 8,5 secondes par image.

---

## Structure

| Fichier | Rôle |
|---|---|
| `start.bat` | Lancement : trouve Python, vérifie Pillow, démarre tout |
| `gen/ouvre.bat` | Attend que le serveur réponde puis ouvre le navigateur |
| `gen/serveur.py` | Serveur local, API, vignettes, zip, archives, corbeille |
| `gen/interface.html` | Interface (relue à chaque requête, modifiable à chaud) |
| `gen/carrousel.py` | Le générateur complet, et l'ajout de photos à un profil |
| `gen/controle.py` | Contrôle visuel de chaque photo avant de la garder |
| `gen/runner.py` | Appels fal, lecture de la clé |
| `gen/visages.py` | ~747 milliards de visages, versions féminine et masculine |
| `gen/poses.py` | 86 poses sûres, contraintes d'anatomie et de regard |
| `gen/lieux.py` | 225 fonds, carence de 30 générations avant réutilisation |
| `gen/filters.py` | Étalonnage doux et continu, par persona |
| `gen/identite.py` | Prénoms INSEE par cohorte, métiers et textes à incruster |
| `gen/genre.py` | Conversion féminin → masculin des banques de textes |
| `gen/pipeline.py` | Post-traitement « vraie photo de téléphone » |
| `gen/sauvegarde.py` | Envoi des carrousels locaux vers Supabase |
| `gen/faire_web.py` | Fabrique `web/app.html` depuis l'interface locale |
| `api/*.py` | Fonctions Vercel : bibliothèque, génération, extension, médias, session |
| `web/*.html` | Interface en ligne et page de connexion |

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

**Les prénoms viennent de l'état civil, pas de l'intuition.** Les six banques
sont le classement réel des 60 prénoms les plus donnés à chaque cohorte de
naissance, calculé sur le [fichier des prénoms de
l'INSEE](https://www.insee.fr/fr/statistiques/7633685) — de 46 % des naissances
pour les plus jeunes à 81 % pour les hommes nés entre 1956 et 1964. Deux
précautions à la lecture du fichier : l'état civil enregistre les variantes
accentuées séparément (182 343 `JEROME` contre 22 847 `JÉRÔME`, qui sont le même
prénom, et dont la graphie majoritaire est la fautive), et un prénom suit sa
génération et non un âge — une femme de 45 ans est née en 1981 aujourd'hui et en
1991 dans dix ans. Les banques sont donc indexées par année de naissance, ce qui
les garde justes sans y revenir.

**Un prénom ne revient pas avant 40 profils**, et c'est arithmétique plutôt que
probabiliste : 60 prénoms par banque contre une fenêtre de 40, si bien que même
quarante profils consécutifs de la même cohorte en laissent vingt de libres.
`python gen/identite.py` le vérifie par simulation — sur 400 profils d'âges
tirés au hasard, 134 prénoms différents et le retour le plus court à 41 profils.

**Les banques de textes ne sont pas dupliquées pour les hommes, elles sont
converties.** La seule difficulté de l'anglais est « her », tantôt possessif
(`her free hand` → *his*) tantôt complément (`behind her` → *him*) ; la règle
qui tranche est ce qui suit le mot, avec une exception devant les déterminants
et les adverbes. Vérifié sur les 119 textes de la banque.

---

## Le contrôle automatique

Chaque photo est relue avant d'être gardée, sur l'image **brute** — le flou, le
bruit et la double compression du post-traitement sont ajoutés exprès, et un juge
les prendrait pour des défauts. Ce n'est pas théorique : sur la version dégradée
d'une photo à trois bras, il ne les voit plus. Quatre questions : est-ce la même
personne que sur la photo 1, le corps est-il possible, y a-t-il un élément qui ne
peut pas exister, et la personne fait-elle son âge. Une photo recalée est refaite,
deux fois au plus, avec la faute constatée réinjectée dans le prompt.
`ATELIER_CONTROLE=0` désactive tout.

Mesure sur 20 photos déjà générées : zéro faux positif sur le corps, et les vrais
défauts attrapés — une femme de 49 ans au visage de 35, deux visages qui ont
dérivé, un double biceps où une **troisième main** tient le téléphone.

### Une question par appel

Les trois appels ne sont pas une précaution, ce sont des mesures. Chaque fois
qu'une question a rejoint les autres dans le même appel, la réponse s'est
dégradée — et toujours en silence, en répondant « ok ».

| Question | Posée seule | Posée avec les autres |
|---|---|---|
| Hauteur du visage, sujet lointain | 6 % | 14 %, au-dessus du seuil |
| Bras d'un double biceps à trois bras | 3 détections sur 3 | 0 sur 3 |

La deuxième ligne est la plus instructive : il a suffi d'**accompagner** la
question d'une liste de ce qu'il fallait chercher — bras partant d'un mauvais
endroit, articulation à l'envers, torse vrillé — pour qu'elle passe de 3/3 à 0/3.
L'énumération fait comparer l'image à une liste ; son absence oblige à la
regarder. La consigne sur le corps tient donc en trois lignes, et demande de
**compter** plutôt que de juger : on agit sur les nombres — plus de deux bras, de
deux mains, de deux jambes — et pas sur l'avis. Moins de deux n'est jamais une
faute : un membre sort du cadre à presque chaque photo.

### Le juge ne sait pas s'abstenir

Sur la photo où le sujet est minuscule dans le cadre — une règle du format, pas
un accident — il répond « ce n'est pas la même personne » avec 90 % de certitude
et cite les traits qui diffèrent, sur un visage haut de 50 pixels. Lui demander
de douter ne change rien, sa certitude vaut 90 dans les deux cas. En revanche il
*localise* très bien. Un verdict qui porte sur le visage déclenche donc un
troisième appel qui ne demande que la boîte englobante ; sous 12 % de la hauteur
d'image, le reproche est écarté. Mesuré : gros plan 30 à 44 %, plan moyen 18 à
23 %, femme au bout de la rue 5,9 %.

**La photo 1 a une exigence de plus** : son visage doit être lisible, puisque les
quatre autres s'y comparent. Un carrousel dont la photo 1 portait des lunettes
noires de nuit a vu ses quatre suivantes partir chacune de son côté.

---

## Limite connue

La cohérence du visage se dégrade toujours à la génération, davantage au-delà de
50 ans et quand les lumières des scènes tirées sont éloignées ; le contrôle la
rattrape au lieu de l'empêcher. Il reste aussi un biais du modèle d'image vers la
jeunesse que le prompt ne corrige qu'à moitié : à 52 ans demandés, le visage rendu
en paraît 45.

---

## Variables d'environnement

| Nom | Rôle |
|---|---|
| `FAL_KEY` | Clé fal, pour la génération et le contrôle |
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_SERVICE_KEY` | Clé de service, accès au stockage et aux tables |
| `ATELIER_MDP` | Mot de passe de l'interface en ligne |
| `SESSION_SECRET` | Signature du cookie de session |
| `ATELIER_CONTROLE` | `0` pour désactiver le contrôle visuel (actif par défaut) |

En local elles se lisent depuis `.env` ; en ligne depuis les variables du
projet Vercel. Le fichier `.env` n'est jamais versionné.
