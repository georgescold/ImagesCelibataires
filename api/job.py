# -*- coding: utf-8 -*-
"""
Avancement des generations, lu dans la table `jobs`.

    /api/job?id=<id>   un job, celui que l'appareil vient de lancer
    /api/job           toutes les generations en cours, D'OU QU'ELLES VIENNENT,
                       plus celles finies depuis moins de deux minutes : chaque
                       appareil voit ainsi ce qu'un autre a lance, et son issue.

Une seule fonction pour les deux usages : le plan Hobby de Vercel plafonne a
douze fonctions, et le projet les a toutes.
"""
import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L

# Au-dela, le job ne peut plus etre vivant : la fonction qui le faisait tourner
# est tuee a 300 s (vercel.json). Or une fonction tuee ne peut pas ecrire son
# propre echec : sans ce delai, le job restait « en cours » pour toujours, et
# l'interface l'interrogeait en boucle — ce qu'on a vu sur une generation morte
# a la quatrieme photo, que l'ecran affichait encore sept minutes plus tard.
MORT_APRES = 330

# une generation finie reste visible ce temps-la dans la liste, pour que les
# autres appareils voient qu'elle a abouti (ou echoue) au lieu de la voir disparaitre
RECENTE = 120

CHAMPS = "id,nom,etat,type,total,libelle,lignes,erreur,cree,maj"


def _enterrer_si_mort(job):
    """Declare en echec un job « en cours » trop vieux pour etre vivant."""
    if job.get("etat") != "en cours" or not job.get("cree"):
        return job
    debut = datetime.datetime.fromisoformat(job["cree"].replace("Z", "+00:00"))
    if (datetime.datetime.now(datetime.timezone.utc) - debut).total_seconds() <= MORT_APRES:
        return job
    job["etat"] = "erreur"
    job["erreur"] = ("La génération a dépassé les 300 secondes qu'accorde Vercel "
                     "et a été interrompue : rien n'a été enregistré.")
    job["lignes"] = (job.get("lignes") or []) + ["ECHEC : temps depasse, generation interrompue"]
    job["maj"] = L._horodatage()
    # on l'ecrit, pour que la prochaine lecture n'ait pas a le recalculer
    L.rest(f"jobs?id=eq.{job['id']}", "PATCH",
           {k: job[k] for k in ("etat", "erreur", "lignes", "maj")}, prefer="return=minimal")
    return job


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        jid = parse_qs(urlparse(self.path).query).get("id", [""])[0]

        if not jid:
            c, d = L.rest(f"jobs?select={CHAMPS}&or=(etat.eq.en%20cours,maj.gt.{L.horodatage_url(-RECENTE)})"
                          "&order=cree.desc&limit=20")
            jobs = [_enterrer_si_mort(j) for j in d] if c == 200 and isinstance(d, list) else []
            return L.json_rep(self, {"jobs": jobs})

        c, d = L.rest(f"jobs?id=eq.{jid}&select={CHAMPS}")
        if not (c == 200 and isinstance(d, list) and d):
            return L.json_rep(self, {"etat": "inconnu"})
        L.json_rep(self, _enterrer_si_mort(d[0]))
