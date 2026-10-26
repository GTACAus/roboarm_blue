(function () {
  const WAIT_MS = 3000; // Increased to 3 seconds to give iOS time to switch apps without a false fallback
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
      // Only forces Safari fallback if Bluefy genuinely didn't open (user stayed on page)
      if (!left && !document.hidden) {
        location.href = web; 
      }
    }, WAIT_MS);

    // Launch Bluefy
    location.href = 'bluefy://open?url=' + encodedWeb;
  });
})();
