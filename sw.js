// Версия кэша. При каждом изменении файлов приложения увеличивайте число —
// тогда установленное приложение скачает новые файлы и обновится само.
const V = 'govorim-v17',
      F = [
        '/Govorim/',
        '/Govorim/index.html',
        '/Govorim/manifest.json',
        '/Govorim/icon-192.png',
        '/Govorim/icon-512.png'
      ];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(V)
      // cache:'reload' — берём свежие файлы с сервера, а не из HTTP-кэша браузера
      .then(c => c.addAll(F.map(u => new Request(u, { cache: 'reload' }))))
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
  // Списки слов из репозитория (/Govorim/lex/…): сначала сеть, при успехе кладём в кэш, офлайн берём из кэша
  if (new URL(e.request.url).pathname.startsWith('/Govorim/lex/')) {
    e.respondWith(
      caches.open(V).then(c =>
        fetch(e.request)
          .then(r => { if (r.ok) c.put(e.request, r.clone()); return r; })
          .catch(() => c.match(e.request).then(r => r || Response.error()))
      )
    );
    return;
  }
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true })
      .then(r => r || fetch(e.request).catch(() => caches.match('/Govorim/index.html')))
  );
});
