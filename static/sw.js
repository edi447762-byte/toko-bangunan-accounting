/**
 * Service Worker untuk PWA Toko Bangunan.
 * Cache asset statis + fallback offline page.
 * Streamlit sendiri server-side, jadi halaman utama butuh internet.
 */
const CACHE_VERSION = 'toko-bangunan-v1';
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/offline.html'
];

// Install: cache asset statis
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
      .catch((err) => console.warn('SW install gagal cache:', err))
  );
});

// Activate: hapus cache lama
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first untuk halaman, cache-first untuk statis
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Hanya handle GET
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Untuk asset statis: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) =>
        cached || fetch(request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, copy));
          return res;
        })
      )
    );
    return;
  }

  // Untuk halaman lain: network-first, fallback ke offline.html
  event.respondWith(
    fetch(request)
      .then((res) => {
        // Cache dokumen HTML berhasil
        if (res.headers.get('content-type')?.includes('text/html')) {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(request)
          .then((cached) => cached || caches.match('/static/offline.html'))
      )
  );
});
