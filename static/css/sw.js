// FoodHub Service Worker - PWA Support
const CACHE_NAME = 'foodhub-v1';
const STATIC_ASSETS = [
  '/',
  '/foods/',
  '/cart/',
  '/orders/',
  '/static/css/style.css',
];

// Install — cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('PWA: Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', event => {
  // Skip non-GET and API calls
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/admin/')) return;
  if (event.request.url.includes('/ajax-')) return;
  if (event.request.url.includes('/add-to-cart/')) return;
  if (event.request.url.includes('/wishlist/toggle/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache fresh responses
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => {
        // Offline fallback from cache
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // Offline page fallback
          return new Response(
            `<!DOCTYPE html>
            <html><head><title>FoodHub - Offline</title>
            <style>
              body{font-family:sans-serif;text-align:center;padding:60px;background:#FFFBF7;}
              h1{color:#FF5722;font-size:2rem;}
              p{color:#6b7280;}
              .btn{background:#FF5722;color:#fff;padding:12px 28px;border-radius:99px;text-decoration:none;display:inline-block;margin-top:20px;}
            </style></head>
            <body>
              <div style="font-size:4rem;margin-bottom:16px;">🌐</div>
              <h1>You're Offline</h1>
              <p>Please check your internet connection and try again.</p>
              <a href="/" class="btn" onclick="location.reload()">🔄 Retry</a>
            </body></html>`,
            { headers: { 'Content-Type': 'text/html' } }
          );
        });
      })
  );
});