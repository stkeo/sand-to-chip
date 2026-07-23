/* 모래에서 칩까지 — 오프라인 캐시 서비스워커
   전략: HTML=네트워크 우선(배포 즉시 반영, 오프라인 시 캐시 폴백) ·
        three.min.js/이미지=캐시 우선(불변 대용량, 재방문 즉시 로드)
   배포 시 캐시 갱신이 필요하면 CACHE 버전만 올리면 된다(구 캐시는 activate에서 청소) */
const CACHE = 's2c-v3';
const PRECACHE = [
  './', './en.html', './404.html',
  './three.min.js',
  './og.png', './og-en.png',
  './icon-192.png', './icon-512.png', './apple-touch-icon.png',
  './manifest.webmanifest'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  /* 불변 대용량 자산: 캐시 우선 */
  if (/\.(js|png|webmanifest)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
        return res;
      }))
    );
    return;
  }

  /* HTML 등: 네트워크 우선, 실패(오프라인) 시 캐시 폴백 */
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return res;
    }).catch(() =>
      caches.match(e.request).then(hit => hit || caches.match('./'))
    )
  );
});
