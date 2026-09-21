// Installation de l'atelier comme une app, sur l'ecran d'accueil du telephone.
//
// Partage par la page de connexion et par l'atelier, pour que l'invitation
// apparaisse des la premiere ouverture sur le telephone — c'est-a-dire sur la
// page de connexion.
//
// Deux mondes :
//   - Android (Chrome, Edge, Samsung) envoie « beforeinstallprompt » : on le
//     garde, et un bouton « Installer » declenche la vraie boite d'installation.
//   - iOS n'a AUCUNE invitation programmable : l'installation passe forcement
//     par Partager, puis « Sur l'ecran d'accueil ». On explique donc le geste.
//
// Rien ne s'affiche a la souris : sur ordinateur, le navigateur propose deja
// l'installation dans sa barre d'adresse, et un bandeau de plus serait du bruit.
// Rien ne s'affiche non plus une fois l'app installee, ni pendant 30 jours apres
// un refus.
(() => {
  if ('serviceWorker' in navigator) {
    addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
  }

  const installee = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const auDoigt = matchMedia('(pointer: coarse)').matches;
  // iPadOS se presente comme un Mac : on le reconnait a son ecran tactile
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent) ||
              (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
  if (installee || !auDoigt) return;

  const CLE = 'atelier-installation-refusee';
  const TRENTE_JOURS = 30 * 24 * 3600 * 1000;
  try {
    // le stockage peut manquer (navigation privee) : on s'en passe
    if (Date.now() - Number(localStorage.getItem(CLE) || 0) < TRENTE_JOURS) return;
  } catch (err) {}

  const PARTAGER = '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" ' +
    'style="vertical-align:-3px;margin:0 2px"><path fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" d="M12 3v12M8 7l4-4 4 4M6 11H5a1 1 0 0 0-1 1v8a1 ' +
    '1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1"/></svg>';

  function styles() {
    if (document.getElementById('installer-styles')) return;
    const s = document.createElement('style');
    s.id = 'installer-styles';
    s.textContent = `
      .installer{position:fixed; z-index:50; left:12px; right:12px; margin:0 auto; max-width:480px;
        bottom:calc(12px + env(safe-area-inset-bottom));
        display:flex; align-items:center; gap:12px; padding:12px 12px 12px 14px;
        background:var(--panneau,#191722); color:var(--texte,#f0ecf2);
        border:1px solid var(--bord-vif,#463f55); border-radius:16px;
        box-shadow:0 12px 40px rgba(0,0,0,.55); font-size:15px; line-height:1.45;
        animation:installer-entree .25s ease-out}
      @keyframes installer-entree{from{transform:translateY(20px); opacity:0}}
      .installer img{width:40px; height:40px; border-radius:10px; flex:none}
      .installer .texte{flex:1; min-width:0}
      .installer .texte b{display:block; font-size:15px}
      .installer .texte span{color:var(--doux,#a9a2b4); font-size:14px}
      .installer button{font:inherit; font-weight:700; cursor:pointer; border-radius:10px; min-height:44px}
      .installer .go{border:0; padding:0 16px; color:#2b060f;
        background:linear-gradient(180deg,var(--accent-clair,#ff6b8c),var(--accent,#e5385f))}
      .installer .non{flex:none; width:44px; border:1px solid var(--bord,#332f3f); background:none;
        color:var(--doux,#a9a2b4); font-size:20px; line-height:1}`;
    document.head.appendChild(s);
  }

  function bandeau(texte, action) {
    styles();
    const b = document.createElement('div');
    b.className = 'installer';
    b.setAttribute('role', 'region');
    b.setAttribute('aria-label', "Installer l'application");
    b.innerHTML = `<img src="/web/icones/icone-192.png" alt="">
      <div class="texte"><b>Installer l'atelier</b><span>${texte}</span></div>
      ${action ? '<button class="go">Installer</button>' : ''}
      <button class="non" aria-label="Plus tard">×</button>`;
    b.querySelector('.non').onclick = () => {
      b.remove();
      try { localStorage.setItem(CLE, String(Date.now())); } catch (err) {}
    };
    if (action) b.querySelector('.go').onclick = () => action(b);
    document.body.appendChild(b);
    return b;
  }

  if (ios) {
    // une seconde de delai : que la page ait le temps d'apparaitre avant l'invitation
    setTimeout(() => bandeau(`Touche ${PARTAGER} Partager, puis « Sur l'écran d'accueil ».`), 1200);
    return;
  }

  let invitation = null, affiche = null;
  addEventListener('beforeinstallprompt', e => {
    e.preventDefault();                 // on garde l'invitation pour notre propre bouton
    invitation = e;
    if (affiche) return;
    affiche = bandeau("Sur l'écran d'accueil, en plein écran, comme une app.", async b => {
      b.remove();
      invitation.prompt();
      const {outcome} = await invitation.userChoice;
      if (outcome !== 'accepted') {
        try { localStorage.setItem(CLE, String(Date.now())); } catch (err) {}
      }
      invitation = null;
    });
  });
  addEventListener('appinstalled', () => { if (affiche) affiche.remove(); });
})();
