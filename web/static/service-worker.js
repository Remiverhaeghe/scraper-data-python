// Application installable : fichiers statiques en cache et page hors ligne.
// Les pages de l'application ne sont jamais mises en cache : elles contiennent
// les offres, candidatures et notes, protégées par la connexion.

const CACHE_NAME = "jobboard-static-v1";
const OFFLINE_URL = "/static/offline.html";
const STATIC_FILES = [
    OFFLINE_URL,
    "/static/style.css",
    "/static/theme.js",
    "/static/htmx.min.js",
    "/static/forms.js",
    "/static/icon-192.png",
];

self.addEventListener("install", (pEvent) => {
    pEvent.waitUntil(
        caches.open(CACHE_NAME).then((pCache) => pCache.addAll(STATIC_FILES))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (pEvent) => {
    // Une nouvelle version du service worker remplace l'ancien cache.
    pEvent.waitUntil(
        caches.keys().then((pNames) =>
            Promise.all(
                pNames
                    .filter((pName) => pName !== CACHE_NAME)
                    .map((pName) => caches.delete(pName))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (pEvent) => {
    const vRequest = pEvent.request;

    if (vRequest.method !== "GET") {
        return;
    }

    // Page : toujours le réseau ; sans réseau, la page hors ligne.
    if (vRequest.mode === "navigate") {
        pEvent.respondWith(fetch(vRequest).catch(() => caches.match(OFFLINE_URL)));
        return;
    }

    // Fichier statique : le cache d'abord, le réseau sinon.
    if (new URL(vRequest.url).pathname.startsWith("/static/")) {
        pEvent.respondWith(
            caches.match(vRequest).then((pCached) => pCached || fetch(vRequest))
        );
    }
});
