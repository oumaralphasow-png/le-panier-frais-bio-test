const CACHE="lpfb-1-0-0-shell";
const SHELL=["/","/manifest.webmanifest","/assets/icon-192.png","/assets/icon-512.png",
"/assets/jus-shots-lpfb.webp","/assets/poke-bowls-lpfb.webp","/assets/pro-preparation-lpfb.webp"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET") return;
  const u=new URL(e.request.url);
  if(u.origin!==location.origin) return;
  if(u.pathname.startsWith("/api")||u.pathname.startsWith("/auth")||u.pathname.startsWith("/b2c")||u.pathname.startsWith("/pro")||u.pathname.startsWith("/purchase")||u.pathname.startsWith("/procurement")) return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match("/"))));
});
