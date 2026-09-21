// Service worker de l'atelier.
//
// Il ne met RIEN en cache, et c'est voulu. L'atelier ne sert a rien hors ligne :
// generer, controler, lister, tout se fait sur le serveur. Et l'interface locale
// est relue a chaque requete pour pouvoir la modifier a chaud — un cache la
// figerait, et on chercherait longtemps pourquoi une modification n'apparait pas.
//
// Il a deux roles, et seulement deux :
//   - rendre l'app installable avec un bouton a nous : Chrome n'envoie son
//     evenement « beforeinstallprompt » qu'en presence d'un gestionnaire fetch ;
//   - hors ligne, remplacer la page d'erreur du navigateur par un message clair,
//     ce qui compte dans une app installee, ou il n'y a plus de barre d'adresse.
//
// Il vit a la racine du site et non dans web/ : un service worker ne controle
// que les pages situees sous son propre chemin, et l'atelier est servi sur « / ».

const HORS_LIGNE = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0e0c11">
<title>Atelier carrousels</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;min-height:100svh;display:grid;place-items:center;padding:24px;
    background:radial-gradient(1400px 700px at 50% -18%,#241b23 0%,#0e0c11 62%);color:#f0ecf2;
    font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
  .carte{width:min(420px,100%);background:#191722;border:1px solid #332f3f;border-radius:16px;
    padding:28px 26px;text-align:center}
  h1{margin:0 0 8px;font-size:20px}
  p{margin:0 0 22px;color:#a9a2b4}
  button{font:inherit;font-weight:700;width:100%;min-height:48px;border:0;border-radius:10px;
    color:#2b060f;background:linear-gradient(180deg,#ff6b8c,#e5385f);cursor:pointer}
</style></head>
<body><div class="carte">
  <h1>Pas de connexion</h1>
  <p>L'atelier a besoin d'internet : les photos se génèrent et se rangent sur le serveur.</p>
  <button onclick="location.reload()">Réessayer</button>
</div></body></html>`;

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  // Seules les pages passent par ici. Les appels a l'API, les photos et les
  // telechargements ne sont pas interceptes : le navigateur les traite comme
  // s'il n'y avait pas de service worker.
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(() =>
    new Response(HORS_LIGNE, {headers: {'Content-Type': 'text/html; charset=utf-8'}})));
});
