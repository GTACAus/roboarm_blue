/* Links to the robot controller: <a data-bluefy href="https://gtacaus.github.io/roboarm_blue/remote/">.
On an iPad or iPhone, a tap tries to open the page in the Bluefy app (Safari has no Bluetooth).
If Bluefy isn't installed, nothing opens (Safari may show a brief "address is invalid" alert)
and after a moment the link opens here instead, where the controller asks for Bluefy.
Anywhere else (a computer, or already inside Bluefy) the link opens normally. */
(function () {
  const WAIT_MS = 1500;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);   // iPadOS asks for desktop sites
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-bluefy]');
    if (!a || !ios || navigator.bluetooth) return;
    e.preventDefault();
    const web = a.href;
    let left = false;                       // Bluefy opened: this page went to the background
    const away = () => { if (document.hidden) left = true; };
    document.addEventListener('visibilitychange', away);
    window.addEventListener('pagehide', () => { left = true; }, { once: true });
    setTimeout(() => {
      document.removeEventListener('visibilitychange', away);
      if (!left && !document.hidden) location.href = web;
    }, WAIT_MS);
    location.href = 'bluefy://open?url=' + web;
  });
})();
