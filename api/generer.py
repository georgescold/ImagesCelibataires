# -*- coding: utf-8 -*-
"""
Generation d'un carrousel en ligne, ajout de photos a un carrousel existant, et
reprise d'une photo en particulier.

Le travail est fait dans une seule invocation : cinq appels a fal enchaines,
environ 80 secondes, sous la limite de 300 s declaree dans vercel.json.
L'avancement est ecrit au fur et a mesure dans la table `jobs`, ce qui permet
au navigateur de le suivre en interrogeant /api/job pendant que celle-ci
tourne encore.

Le code de generation n'est pas duplique : on recree dans /tmp l'arborescence
qu'il attend, on le laisse ecrire ses fichiers, puis on televerse le resultat.

Les trois travaux partagent cette fonction plutot que d'en avoir chacun une :
le plan Hobby de Vercel plafonne a douze fonctions par deploiement, et le
projet en compte deja douze. Ce n'est pas qu'un pis-aller — etendre un profil
ou refaire une de ses photos est une generation comme une autre, meme /tmp,
meme televersement. Le corps de la requete porte `etendre: true` ou
`refaire: true` pour demander l'une des deux autres.
"""
import json, os, re, threading, time, traceback
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

LOT = 5

# Une fonction Vercel est tuee a 300 s, et rien n'est televerse avant la fin :
# depasser, c'est perdre tout le carrousel, deja paye. Deux echeances, comptees
# depuis le debut du travail :
#   - plus aucune relance apres RELANCES_JUSQUA : les photos recalees au-dela
#     sont gardees telles quelles ;
#   - plus aucune photo entamee apres BUDGET.
# Pire cas : trois essais sur la photo 1 et trois sur la photo 2 menent a 150 s ;
# les trois dernieres, sans relance, a 225 s ; le televersement a 240 s.
# Constate avant ces echeances : huit relances d'affilee sur l'age ont mene une
# generation a 437 s, et Vercel l'a tuee au milieu de la quatrieme photo.
BUDGET = 235
RELANCES_JUSQUA = 150


def _maj(job_id, **champs):
    champs["maj"] = L._horodatage()          # pour dater une fin, vue des autres appareils
    L.rest(f"jobs?id=eq.{job_id}", "PATCH", champs, prefer="return=minimal")


# Au-dela, un job « en cours » est mort (cf. api/job.py) : il ne bloque plus rien.
VIVANT = 330

# Verrou en base tenu entre « ce nom est libre » (ou « ces numeros sont libres »)
# et l'inscription du job qui les prend.
LANCEMENT = "lancement"

# Une meme instance peut servir plusieurs requetes a la fois, qui partagent alors
# /tmp/atelier : la fiche d'une personne (meta.json) y est relue puis reecrite
# sous ce verrou, et non ecrasee par la copie qu'une autre avait lue au depart.
FICHES_TMP = threading.Lock()


def _jobs_actifs():
    c, d = L.rest(f"jobs?etat=eq.en%20cours&cree=gt.{L.horodatage_url(-VIVANT)}&select=nom")
    return {x["nom"] for x in d} if c == 200 and isinstance(d, list) else set()


def _nom_libre(base):
    """Un nom de dossier libre. Les generations en cours comptent : deux
    « femme58 » lancees ensemble auraient sinon ecrit dans le meme dossier, la
    fiche du carrousel n'existant qu'une fois la premiere terminee."""
    c, d = L.rest("carrousels?select=nom")
    pris = {x["nom"] for x in d} if c == 200 and isinstance(d, list) else set()
    pris |= _jobs_actifs()
    nom, i = base, 2
    while nom in pris:
        nom, i = f"{base}_{i}", i + 1
    return nom


def _prochain_numero(nom):
    """Premier numero libre pour un lot de photos en plus. A appeler sous le
    verrou LANCEMENT. Compter les photos en base ne suffit pas : deux lots lances
    ensemble sur la meme personne les compteraient tous deux et ecriraient 6-10
    l'un sur l'autre. Les numeros que se sont reserves les lots encore en cours
    comptent donc aussi : le second recoit 11-15."""
    c, ph = L.rest(f"photos?carrousel=eq.{nom}&select=numero&order=numero.desc&limit=1")
    dernier = ph[0]["numero"] if c == 200 and isinstance(ph, list) and ph else 0
    c, js = L.rest(f"jobs?nom=eq.{nom}&etat=eq.en%20cours&type=eq.extension"
                   f"&cree=gt.{L.horodatage_url(-VIVANT)}&select=depart,total")
    for j in js if c == 200 and isinstance(js, list) else []:
        if j.get("depart"):
            dernier = max(dernier, j["depart"] + (j.get("total") or 1) - 1)
    return dernier + 1


def _preparer_reprise(nom, fiche, racine):
    """Recree dans /tmp ce dont la reprise d'un carrousel a besoin : sa fiche en
    meta.json et la photo 1, qui sert de reference. Rend False si la photo 1 est
    introuvable dans le stockage.

    Partage par l'extension et par la reprise d'une photo : les deux repartent
    du meme visage et de la meme fiche."""
    dossier = os.path.join(racine, "gen", nom)
    brut = os.path.join(racine, "gen", nom + "_raw")
    os.makedirs(dossier, exist_ok=True)
    os.makedirs(brut, exist_ok=True)

    meta = {k: fiche.get(k) for k in
            ("nom", "genre", "prenom", "age", "metier", "recherche", "persona",
             "textes", "visage", "signes", "slides")}
    with FICHES_TMP:
        json.dump(meta, open(os.path.join(dossier, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    # la photo 1 d'avant post-traitement si elle existe, sinon celle qui est
    # publiee — les carrousels d'avant cette version n'ont que la seconde
    donnees = L.lire_objet(f"{nom}/brut/1.jpg") or L.lire_objet(f"{nom}/1.jpg")
    if not donnees:
        return False
    open(os.path.join(brut, "1.jpg"), "wb").write(donnees)
    return True


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        d = L.corps_json(self)
        if d.get("refaire"):
            return self._refaire(d)
        return self._etendre(d) if d.get("etendre") else self._creer(d)

    # ------------------------------------------------------------- nouveau profil
    def _creer(self, d):
        age = max(30, min(70, int(d.get("age") or 45)))
        genre = "h" if d.get("genre") == "h" else "f"
        persona = d.get("persona") if d.get("persona") in L.PERSONAS else "discrete_nature"
        base = re.sub(r"[^a-z0-9_]", "", (d.get("nom") or "").lower()) \
            or f"{'homme' if genre == 'h' else 'femme'}{age}"
        # Choisi et inscrit sous verrou : deux appareils lancant « femme58 » au
        # meme instant liraient tous deux le nom libre avant que l'un l'inscrive.
        with L.verrou(LANCEMENT):
            nom = _nom_libre(base)
            job_id = self._ouvrir_job(nom, "creation", 5,
                                      f"Nouveau profil · {'homme' if genre == 'h' else 'femme'} de {age} ans")
        if not job_id:
            return
        L.json_rep(self, {"job": job_id, "nom": nom})

        def faire(journal):
            debut = time.time()
            racine = L.preparer_tmp()
            import carrousel
            carrousel.build(nom, persona, age, journal=journal, genre=genre,
                            avant=debut + BUDGET, relances_jusqua=debut + RELANCES_JUSQUA,
                            tirage_exclusif=lambda: L.registres(racine, L.REGISTRES_TIRAGE, "tirage"))
            meta = json.load(open(os.path.join(racine, "gen", nom, "meta.json"),
                                  encoding="utf-8"))
            L.televerser(nom, racine, meta, journal)

        self._travailler(job_id, faire)

    # ------------------------------------------------------- photos en plus
    def _etendre(self, d):
        nom = d.get("nom", "")
        if not nom or not nom.replace("_", "").replace("-", "").isalnum():
            return L.json_rep(self, {"erreur": "nom refuse"}, 400)
        combien = max(1, min(10, int(d.get("combien") or LOT)))

        c, fiches = L.rest(f"carrousels?nom=eq.{nom}")
        if c != 200 or not isinstance(fiches, list) or not fiches:
            return L.json_rep(self, {"erreur": "carrousel introuvable"}, 404)
        fiche = fiches[0]
        if not fiche.get("visage"):
            return L.json_rep(self, {"erreur": "fiche trop ancienne : elle ne contient pas "
                                               "la description du visage"}, 409)
        # Rien n'empeche un second lot sur la meme personne pendant que le premier
        # tourne : chacun se reserve ses numeros, sous verrou (cf. _prochain_numero).
        with L.verrou(LANCEMENT):
            depart = _prochain_numero(nom)
            job_id = self._ouvrir_job(nom, "extension", combien,
                                      f"{fiche.get('prenom') or nom}, {fiche.get('age')} ans · "
                                      f"{combien} photo{'s' if combien > 1 else ''} de plus",
                                      depart=depart)
        if not job_id:
            return
        L.json_rep(self, {"job": job_id, "nom": nom, "combien": combien})

        def faire(journal):
            debut = time.time()
            racine = L.preparer_tmp()
            if not _preparer_reprise(nom, fiche, racine):
                raise RuntimeError("photo 1 introuvable dans le stockage")
            import carrousel
            nouvelles = carrousel.ajouter(nom, combien, journal=journal, depart=depart,
                                          avant=debut + BUDGET,
                                          relances_jusqua=debut + RELANCES_JUSQUA,
                                          tirage_exclusif=lambda: L.registres(
                                              racine, L.REGISTRES_TIRAGE, "tirage"),
                                          fiche_exclusive=lambda: FICHES_TMP)
            if nouvelles:
                # les fiches des photos viennent du retour d'ajouter(), pas d'une
                # relecture de meta.json, qu'une autre requete a pu reecrire depuis
                L.televerser(nom, racine, dict(fiche, slides=nouvelles), journal,
                             numeros=[s["n"] for s in nouvelles], creation=False)

        self._travailler(job_id, faire)

    # -------------------------------------------------- refaire une photo
    def _refaire(self, d):
        nom = d.get("nom", "")
        numero = int(d.get("numero") or 0)
        if not nom or not nom.replace("_", "").replace("-", "").isalnum():
            return L.json_rep(self, {"erreur": "nom refuse"}, 400)
        if not 1 <= numero <= 100:
            return L.json_rep(self, {"erreur": "numero de photo invalide"}, 400)

        c, fiches = L.rest(f"carrousels?nom=eq.{nom}")
        if c != 200 or not isinstance(fiches, list) or not fiches:
            return L.json_rep(self, {"erreur": "carrousel introuvable"}, 404)
        fiche = fiches[0]
        if not fiche.get("visage"):
            return L.json_rep(self, {"erreur": "fiche trop ancienne : elle ne contient pas "
                                               "la description du visage"}, 409)

        job_id = self._ouvrir_job(nom, "reprise", 1,
                                  f"{fiche.get('prenom') or nom}, {fiche.get('age')} ans · "
                                  f"photo {numero} refaite")
        if not job_id:
            return
        L.json_rep(self, {"job": job_id, "nom": nom, "numero": numero})

        def faire(journal):
            debut = time.time()
            racine = L.preparer_tmp()
            if not _preparer_reprise(nom, fiche, racine):
                raise RuntimeError("photo 1 introuvable dans le stockage")
            import carrousel
            refaite = carrousel.refaire(nom, numero, journal=journal,
                                        relances_jusqua=debut + RELANCES_JUSQUA,
                                        tirage_exclusif=lambda: L.registres(
                                            racine, L.REGISTRES_TIRAGE, "tirage"),
                                        fiche_exclusive=lambda: FICHES_TMP)
            L.televerser(nom, racine, dict(fiche, slides=[refaite]), journal,
                         numeros=[numero], creation=False)

        self._travailler(job_id, faire)

    # ------------------------------------------------------------------ commun
    def _ouvrir_job(self, nom, type_, total, libelle, depart=None):
        """`type_`, `total` et `libelle` servent a l'affichage des generations en
        cours sur tous les appareils : quoi, pour qui, et combien de photos.
        `depart` : premier des numeros de photos reserves par un lot."""
        ligne = {"nom": nom, "etat": "en cours", "lignes": [],
                 "type": type_, "total": total, "libelle": libelle}
        if depart is not None:
            ligne["depart"] = depart
        c, j = L.rest("jobs", "POST", ligne, prefer="return=representation")
        job_id = j[0]["id"] if c in (200, 201) and isinstance(j, list) and j else None
        if not job_id:
            L.json_rep(self, {"erreur": f"job : {c} {j}"}, 500)
        return job_id

    def _travailler(self, job_id, faire):
        """La reponse est deja partie : on travaille en ecrivant l'avancement
        dans la table `jobs`, que le navigateur interroge pendant ce temps."""
        lignes = []

        def journal(ligne):
            lignes.append(str(ligne).rstrip())
            _maj(job_id, lignes=lignes)

        try:
            faire(journal)
            _maj(job_id, etat="fini", lignes=lignes)
        except BaseException as e:
            lignes.append(f"ECHEC : {e}")
            _maj(job_id, etat="erreur", lignes=lignes,
                 erreur=str(e) + "\n" + traceback.format_exc()[-900:])
