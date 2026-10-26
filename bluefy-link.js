(function () {
  const WAIT_MS = 3000;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-bluefy]');
    if (!a || !ios || navigator.bluetooth) return;

    e.preventDefault();
    const web = a.href;
    const encodedWeb = encodeURIComponent(web);

    let left = false;
    const away = () => { if (document.hidden) left = true; };

    document.addEventListener('visibilitychange', away);
    window.addEventListener('pagehide', () => { left = true; }, { once: true });

    setTimeout(() => {
      document.removeEventListener('visibilitychange', away);
      // Fallback: only redirects to web if Bluefy wasn't opened and user stayed on page
      if (!left && !document.hidden) {
        location.href = web;
      }
    }, WAIT_MS);

    // FIX: Instead of location.href (which glitches on iOS), 
    // dynamically create and click a real link to trigger Bluefy natively.
    const tempLink = document.createElement('a');
    tempLink.href = 'bluefy://open?url=' + encodedWeb;
    tempLink.style.display = 'none';
    document.body.appendChild(tempLink);
    tempLink.click();
    document.body.removeChild(tempLink);
  });
})();
