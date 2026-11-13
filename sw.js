// Версия кэша. При каждом изменении файлов приложения увеличивайте число —
// тогда установленное приложение скачает новые файлы и обновится само.
const V = 'govorim-v62';

// Папка приложения берётся из адреса самого sw.js (на GitHub Pages — /Govorim/),
// поэтому копию можно разместить в любой папке любого сайта без правки путей.
const BASE = new URL('./', self.location).pathname,
      PAGE = BASE + 'index.html',
      // Имя кэша включает папку: копии в разных папках одного сайта не мешают друг другу
      CN = V + ':' + BASE,
      F = ['', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png'].map(f => BASE + f);

// Свои старые кэши: той же папки (govorim-vNN:/папка/) и, для /Govorim/, прежние без папки (govorim-vNN).
// Кэши других приложений сайта (например, «Знову слова») не трогаем.
const isOld = k => k !== CN && (k.startsWith('govorim-') && k.endsWith(':' + BASE) || (BASE === '/Govorim/' && /^govorim-v\d+$/.test(k)));
const isLex = p => p.startsWith(BASE + 'lex/');

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CN)
      // cache:'reload' — берём свежие файлы с сервера, а не из HTTP-кэша браузера
      .then(c => c.addAll(F.map(u => new Request(u, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(k => Promise.all(k.filter(isOld).map(x => caches.delete(x))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  // Списки слов из репозитория (lex/…): сначала сеть, при успехе кладём в кэш, офлайн берём из кэша
  if (isLex(url.pathname)) {
    e.respondWith(
      caches.open(CN).then(c =>
        fetch(e.request)
          .then(r => { if (r.ok) c.put(e.request, r.clone()); return r; })
          .catch(() => c.match(e.request).then(r => r || Response.error()))
      )
    );
    return;
  }
  e.respondWith(
    caches.open(CN).then(c =>
      c.match(e.request, { ignoreSearch: true })
        .then(r => r || fetch(e.request).catch(() => c.match(PAGE).then(p => p || Response.error())))
    )
  );
});
