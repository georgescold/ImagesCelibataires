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
    (r'src="/vignette/\$\{f\.nom\}/\$\{n\}\.jpg"',
     'src="${(f.vignettes && f.vignettes[n]) || `/api/media?nom=${f.nom}&n=${n}`}"',
     "vignettes"),
    (r'href="/dl/\$\{f\.nom\}/\$\{n\}\.jpg" download',
     'href="/api/media?nom=${f.nom}&n=${n}&plein=1" download',
     "telechargement d'une photo"),
    (r'href="/zip/\$\{f\.nom\}"',
     'href="/api/archive?nom=${f.nom}"',
     "telechargement du carrousel"),
    (r"fetch\('/api/job/' \+ job\)",
     "fetch('/api/job?id=' + job)",
     "avancement"),
    (r"fetch\(a\.dataset\.archivee === '1' \? '/api/restaurer' : '/api/archiver', \{\s*"
     r"method:'POST', headers:\{'Content-Type':'application/json'\},\s*"
     r"body: JSON\.stringify\(\{nom: a\.dataset\.archive\}\)\s*\}\)",
     "fetch('/api/action', {\n"
     "      method:'POST', headers:{'Content-Type':'application/json'},\n"
     "      body: JSON.stringify({nom: a.dataset.archive,\n"
     "                            action: a.dataset.archivee === '1' ? 'restaurer' : 'archiver'})\n"
     "    })",
     "archiver / restaurer"),
    # en local le favori est un fichier a part ; en ligne c'est une colonne de
    # la fiche, donc la meme fonction que les changements de statut
    (r"fetch\('/api/favori', \{\s*"
     r"method:'POST', headers:\{'Content-Type':'application/json'\},\s*"
     r"body: JSON\.stringify\(\{nom: fav\.dataset\.favori, favori: fav\.dataset\.aimee !== '1'\}\)\s*\}\)",
     "fetch('/api/action', {\n"
     "      method:'POST', headers:{'Content-Type':'application/json'},\n"
     "      body: JSON.stringify({nom: fav.dataset.favori,\n"
     "                            action: fav.dataset.aimee === '1' ? 'defavori' : 'favori'})\n"
     "    })",
     "favori"),
    (r"fetch\('/api/supprimer', \{\s*"
     r"method:'POST', headers:\{'Content-Type':'application/json'\},\s*"
     r"body: JSON\.stringify\(\{nom: sup\.dataset\.supprime\}\)\s*\}\)",
     "fetch('/api/action', {\n"
     "      method:'POST', headers:{'Content-Type':'application/json'},\n"
     "      body: JSON.stringify({nom: sup.dataset.supprime, action: 'supprimer'})\n"
     "    })",
     "suppression"),
    (r"Les 5 photos partent dans gen/_corbeille, tu peux encore les récupérer à la main\.",
     "Le carrousel passe en corbeille : il disparaît des deux onglets mais les photos restent en ligne.",
     "message de confirmation"),
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
        '  <button class="bouton minuscule" id="sortir" '
        'style="margin-left:auto">Se déconnecter</button>',
        "bouton de deconnexion")

    # une session expiree renvoie 401 : on repasse par la page de connexion
    html = remplacer(
        html,
        "async function charger(){\n"
        "  const d = await (await fetch('/api/librairie' + REQUETE[ONGLET])).json();",
        "async function charger(){\n"
        "  const r = await fetch('/api/librairie' + REQUETE[ONGLET]);\n"
        "  if(r.status === 401){ location.reload(); return; }\n"
        "  const d = await r.json();",
        "session expiree")

    # On s'accroche a la DERNIERE ligne du script, pas a `charger();` : l'ancre
    # d'origine visait cette ligne quand elle fermait le fichier, et le jour ou
    # `solde()` puis `chargerTypes()` sont passes apres, le remplacement a cesse
    # de s'appliquer — en silence. Le bouton « Se déconnecter » etait affiche en
    # ligne sans rien faire. D'ou `remplacer` plutot que `str.replace`.
    html = remplacer(
        html,
        "chargerTypes();\n</script>",
        "chargerTypes();\n\n"
        "$('#sortir').onclick = async () => {\n"
        "  await fetch('/api/sortir', {method:'POST'});\n"
        "  location.reload();\n"
        "};\n</script>",
        "branchement de la deconnexion")

    return remplacer(html, "<title>Atelier carrousels</title>",
                     "<title>Atelier carrousels — en ligne</title>", "titre")


if __name__ == "__main__":
    os.makedirs(os.path.dirname(CIBLE), exist_ok=True)
    html = transformer(open(SOURCE, encoding="utf-8").read())
    open(CIBLE, "w", encoding="utf-8").write(html)
    print(f"web/app.html ecrit ({len(html)} octets), {len(REGLES)} regles appliquees")
