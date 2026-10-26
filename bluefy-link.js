(function () {
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  // If it's an iOS device without native Bluetooth, update all [data-bluefy] links
  if (ios && !navigator.bluetooth) {
    document.querySelectorAll('a[data-bluefy]').forEach(a => {
      const webUrl = a.href;
      a.href = 'bluefy://open?url=' + encodeURIComponent(webUrl);
    });
  }
})();
