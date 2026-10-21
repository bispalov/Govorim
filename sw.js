// Кеш та область дії ізольовані під папочку /govorim/
const V = 'govorim-v4',
      F = [
        '/govorim/',
        '/govorim/index.html',
        '/govorim/manifest.json',
        '/govorim/icon-192.png',
        '/govorim/icon-512.png'
      ];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(V)
      .then(c => c.addAll(F))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(k => Promise.all(k.filter(x => x !== V).map(x => caches.delete(x))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.open(V).then(c => 
      c.match(e.request, { ignoreSearch: true }).then(r => {
        const n = fetch(e.request).then(x => {
          if (x && x.ok) c.put(e.request, x.clone());
          return x;
        }).catch(() => r || c.match('/govorim/index.html'));
        return r || n;
      })
    )
  );
});
