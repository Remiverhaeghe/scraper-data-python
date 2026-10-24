// Application installable et lecture hors connexion : fichiers statiques en cache,
// dernière copie des pages de lecture consultées, page hors ligne sinon.
// Les pages contiennent offres, candidatures et notes : seules les pages de
// lecture sont gardées, 40 au plus, et la déconnexion les efface
// (en-tête Clear-Site-Data de /logout).

const CACHE_NAME = "jobboard-static-v2";
const PAGES_CACHE_NAME = "jobboard-pages-v1";
const MAX_PAGES = 40;
const OFFLINE_URL = "/static/offline.html";
const STATIC_FILES = [
    OFFLINE_URL,
    "/static/style.css",
    "/static/theme.js",
    "/static/htmx.min.js",
    "/static/forms.js",
    "/static/pwa.js",
    "/static/icon-192.png",
];

// Pages de lecture gardées pour la consultation hors connexion ; jamais les
// réglages, la connexion, l'API ni les téléchargements.
const READABLE_PATHS = ["/", "/offers", "/offer", "/applications", "/skills", "/market"];

self.addEventListener("install", (pEvent) => {
    pEvent.waitUntil(
        caches.open(CACHE_NAME).then((pCache) => pCache.addAll(STATIC_FILES))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (pEvent) => {
    // Une nouvelle version du service worker remplace l'ancien cache statique.
    pEvent.waitUntil(
        caches.keys().then((pNames) =>
            Promise.all(
                pNames
                    .filter((pName) => pName !== CACHE_NAME && pName !== PAGES_CACHE_NAME)
                    .map((pName) => caches.delete(pName))
            )
        )
    );
    self.clients.claim();
});

/** Indique si la réponse est une page de lecture à garder pour le hors connexion. */
function isReadablePage(pRequest, pResponse) {
    const vUrl = new URL(pRequest.url);

    return (
        vUrl.origin === self.location.origin &&
        READABLE_PATHS.includes(vUrl.pathname) &&
        pResponse.ok &&
        !pResponse.redirected &&
        (pResponse.headers.get("Content-Type") || "").startsWith("text/html")
    );
}

/** Garde la copie d'une page, puis oublie les plus anciennes au-delà du plafond. */
async function keepPage(pRequest, pResponse) {
    const vCache = await caches.open(PAGES_CACHE_NAME);

    await vCache.put(pRequest, pResponse);

    const vKeys = await vCache.keys();

    await Promise.all(
        vKeys.slice(0, Math.max(vKeys.length - MAX_PAGES, 0)).map((pKey) => vCache.delete(pKey))
    );
}

/** Le réseau d'abord ; sans réseau, la dernière copie de la page, sinon la page hors ligne. */
async function readPage(pRequest) {
    try {
        const vResponse = await fetch(pRequest);

        if (isReadablePage(pRequest, vResponse)) {
            await keepPage(pRequest, vResponse.clone());
        }

        return vResponse;
    } catch (pError) {
        const vCopy = await caches.match(pRequest, { cacheName: PAGES_CACHE_NAME });

        return vCopy || caches.match(OFFLINE_URL);
    }
}

self.addEventListener("fetch", (pEvent) => {
    const vRequest = pEvent.request;

    if (vRequest.method !== "GET") {
        return;
    }

    if (vRequest.mode === "navigate") {
        pEvent.respondWith(readPage(vRequest));
        return;
    }

    // Fichier statique : le cache d'abord, le réseau sinon.
    if (new URL(vRequest.url).pathname.startsWith("/static/")) {
        pEvent.respondWith(
            caches.match(vRequest).then((pCached) => pCached || fetch(vRequest))
        );
    }
});
