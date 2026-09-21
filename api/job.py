# -*- coding: utf-8 -*-
"""Avancement d'une generation, lu dans la table `jobs`."""
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not L.authentifie(self.headers):
            return L.refuser(self)
        jid = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        if not jid:
            return L.json_rep(self, {"etat": "inconnu"})
        c, d = L.rest(f"jobs?id=eq.{jid}")
        if not (c == 200 and isinstance(d, list) and d):
            return L.json_rep(self, {"etat": "inconnu"})
        job = d[0]

        if job.get("etat") == "en cours" and job.get("cree"):
            debut = datetime.datetime.fromisoformat(job["cree"].replace("Z", "+00:00"))
            age = (datetime.datetime.now(datetime.timezone.utc) - debut).total_seconds()
            if age > MORT_APRES:
                job["etat"] = "erreur"
                job["erreur"] = ("La génération a dépassé les 300 secondes qu'accorde Vercel "
                                 "et a été interrompue : rien n'a été enregistré.")
                job["lignes"] = (job.get("lignes") or []) + ["ECHEC : temps depasse, generation interrompue"]
                # on l'ecrit, pour que la prochaine lecture n'ait pas a le recalculer
                L.rest(f"jobs?id=eq.{jid}", "PATCH",
                       {k: job[k] for k in ("etat", "erreur", "lignes")}, prefer="return=minimal")
        L.json_rep(self, job)
