(function () {
  const WAIT_MS = 1500;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); // iPadOS asks for desktop sites

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-bluefy]');
    if (!a || !ios || navigator.bluetooth) return;

    e.preventDefault();
    const web = a.href;
    const encodedWeb = encodeURIComponent(web); // Properly encodes the target URL for Bluefy

    let left = false; // Bluefy opened: this page went to the background
    const away = () => { if (document.hidden) left = true; };

    document.addEventListener('visibilitychange', away);
    window.addEventListener('pagehide', () => { left = true; }, { once: true });

    setTimeout(() => {
      document.removeEventListener('visibilitychange', away);
      if (!left && !document.hidden) {
        location.href = web; // Fallback: opens the regular web page if Bluefy isn't installed
      }
    }, WAIT_MS);

    // Launch Bluefy with the properly encoded URL parameter
    location.href = 'bluefy://open?url=' + encodedWeb;
  });
})();
