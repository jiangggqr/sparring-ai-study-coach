const CACHE_NAME = "sparring-shell-v8";
const ROOT_URL = new URL("./", self.registration.scope).href;
const APP_SHELL = [
  ROOT_URL,
  new URL("index.html", ROOT_URL).href,
  new URL("styles.css?v=7", ROOT_URL).href,
  new URL("app.js?v=8", ROOT_URL).href,
  new URL("demo-engine.mjs?v=7", ROOT_URL).href,
  new URL("favicon.svg", ROOT_URL).href,
  new URL("vendor/pdf.mjs", ROOT_URL).href,
  new URL("vendor/pdf.worker.mjs", ROOT_URL).href,
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
      ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(event.request);
        if (cached) return cached;
        if (event.request.mode === "navigate") return caches.match(ROOT_URL);
        return Response.error();
      }),
  );
});
