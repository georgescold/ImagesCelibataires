# -*- coding: utf-8 -*-
"""
Fabrique web/app.html a partir de gen/interface.html.

L'interface locale et l'interface en ligne partagent le meme design et la
meme logique ; seules les adresses des routes changent, parce que le serveur
local sert des fichiers alors que Vercel sert des fonctions.

Plutot que d'entretenir deux fichiers qui divergeraient, on transforme le
premier en second. Une seule source, une seule commande :

    python gen/faire_web.py
"""
import os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "gen", "interface.html")
CIBLE = os.path.join(RACINE, "web", "app.html")

# (motif, remplacement, description) -- chaque regle DOIT s'appliquer,
# sinon c'est que l'interface locale a change et que la transformation
# ne suit plus : on echoue bruyamment plutot que de livrer du HTML casse.
REGLES = [
    # images : en ligne, la bibliotheque fournit des URL signees du stockage ;
    # ces chemins ne servent qu'en repli, par la fonction qui sert les photos
    (r"`/vignette/\$\{nom\}/\$\{n\}\.jpg`",
     "`/api/media?nom=${nom}&n=${n}`",
     "repli des vignettes"),
    (r"`/dl/\$\{nom\}/\$\{n\}\.jpg`",
     "`/api/media?nom=${nom}&n=${n}&plein=1`",
     "repli des photos pleine taille"),
    (r'href="/zip/\$\{f\.nom\}"',
     'href="/api/archive?nom=${f.nom}"',
     "telechargement du carrousel"),
    (r"fetch\('/api/job/' \+ job\)",
     "fetch('/api/job?id=' + job)",
     "avancement"),
    (r"Les 5 photos partent dans gen/_corbeille, tu peux encore les récupérer à la main\.",
     "Le carrousel passe en corbeille : il disparaît des deux onglets mais les photos restent en ligne.",
     "message de confirmation"),
    # --- carte de personnalite : en ligne, une seule fonction sert les trois
    # usages, aiguillee par ses parametres. Ces trois regles ont longtemps
    # manque : les bons appels avaient ete ecrits A LA MAIN dans web/app.html,
    # si bien que la premiere regeneration les a effaces et a casse la carte
    # en ligne. Elles vivent ici desormais.
    (r"fetch\('/api/types'\)",
     "fetch('/api/carte?types=1')",
     "types de personnalite"),
    (r"'/carte/' \+ d\.fichier \+ '\?v='",
     "'/api/carte?fichier=' + d.fichier + '&v='",
     "image de la carte"),
    (r"'/carte-dl/' \+ d\.fichier",
     "'/api/carte?fichier=' + d.fichier + '&dl=1'",
     "telechargement de la carte"),
]


def rater(quoi):
    raise SystemExit(
        f"Regle non appliquee : {quoi}\n"
        "gen/interface.html a change, la transformation web ne suit plus.\n"
        "Corrige la regle correspondante dans gen/faire_web.py."
    )


def remplacer(html, avant, apres, quoi):
    """Comme str.replace, mais qui refuse de ne rien faire. Un remplacement
    silencieux livrerait une interface en ligne amputee sans prevenir."""
    if avant not in html:
        rater(quoi)
    return html.replace(avant, apres)


def transformer(html):
    for motif, remplacement, quoi in REGLES:
        html, n = re.subn(motif, remplacement, html)
        if n == 0:
            rater(quoi)

    # bouton de deconnexion dans l'entete
    html = remplacer(
        html,
        '<span class="note" id="compte"></span>',
        '<span class="note" id="compte"></span>\n'
        '  <button class="bouton minuscule" id="sortir" style="margin-left:auto" '
        'title="Se déconnecter"><span class="sortir-long">Se déconnecter</span>'
        '<span class="sortir-court">Sortir</span></button>',
        "bouton de deconnexion")

    # Actions sur une fiche : en local une route par action, en ligne une seule
    # fonction (le plan Hobby plafonne a douze) ; le favori, fichier a part en
    # local, y est une colonne de la fiche comme le statut.
    html = remplacer(
        html,
        "function envoyerAction(nom, quoi){\n"
        "  const route = {supprimer:'/api/supprimer', archiver:'/api/archiver', restaurer:'/api/restaurer',\n"
        "                 favori:'/api/favori', defavori:'/api/favori'}[quoi];\n"
        "  return fetch(route, {method:'POST', headers:{'Content-Type':'application/json'},\n"
        "                       body: JSON.stringify({nom, favori: quoi === 'favori'})});\n"
        "}\n",
        "function envoyerAction(nom, quoi){\n"
        "  return fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'},\n"
        "                               body: JSON.stringify({nom, action: quoi})});\n"
        "}\n",
        "actions sur une fiche")

    # Une session expiree renvoie 401 : on repasse par la page de connexion, et
    # la promesse qui ne se resout jamais arrete tout le reste pendant ce temps.
    html = remplacer(
        html,
        "  const r = await fetch('/api/librairie' + REQUETE[quel]);\n",
        "  const r = await fetch('/api/librairie' + REQUETE[quel]);\n"
        "  if(r.status === 401){ location.reload(); return new Promise(() => {}); }\n",
        "session expiree")

    # web/app.html se lit comme une source : on previent qu'il n'en est pas une.
    # Deux retouches faites a la main ici — la carte en ligne et la gestion
    # d'erreur de la bibliotheque — ont ete effacees par une regeneration.
    html = remplacer(
        html, "<!doctype html>\n",
        "<!doctype html>\n"
        "<!-- Fichier FABRIQUE par gen/faire_web.py a partir de gen/interface.html.\n"
        "     Ne pas le modifier a la main : la prochaine regeneration effacerait la\n"
        "     modification. Changer gen/interface.html, ou une regle de faire_web.py. -->\n",
        "avertissement")

    # On s'accroche a la fermeture du script elle-meme, pas a sa derniere ligne :
    # l'ancre d'origine visait `charger();`, puis `chargerTypes();`, et chaque
    # appel ajoute apres elles la rendait caduque — la premiere fois en silence,
    # et le bouton « Se déconnecter » est reste affiche en ligne sans rien faire.
    html = remplacer(
        html,
        "\n</script>\n</body>",
        "\n\n$('#sortir').onclick = async () => {\n"
        "  await fetch('/api/sortir', {method:'POST'});\n"
        "  location.reload();\n"
        "};\n</script>\n</body>",
        "branchement de la deconnexion")

    return remplacer(html, "<title>Atelier carrousels</title>",
                     "<title>Atelier carrousels — en ligne</title>", "titre")


if __name__ == "__main__":
    os.makedirs(os.path.dirname(CIBLE), exist_ok=True)
    html = transformer(open(SOURCE, encoding="utf-8").read())
    open(CIBLE, "w", encoding="utf-8").write(html)
    print(f"web/app.html ecrit ({len(html)} octets), {len(REGLES)} regles appliquees")
