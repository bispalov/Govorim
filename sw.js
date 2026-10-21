// Кэш и охват привязаны к папке публикации, поэтому несколько копий на одном домене не мешают друг другу.
const SC=self.registration.scope,V='govorim-v3|'+SC,F=['./','./index.html','./manifest.json','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(F)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x.startsWith('govorim-')&&x.endsWith('|'+SC)&&x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;
e.respondWith(caches.open(V).then(c=>c.match(e.request,{ignoreSearch:true}).then(r=>{
const n=fetch(e.request).then(x=>{if(x&&x.ok)c.put(e.request,x.clone());return x}).catch(()=>r||c.match('./index.html'));
return r||n})))});
