// Enregistre le service worker qui rend le tableau de bord installable.
// Les navigateurs ne l'acceptent qu'en HTTPS, ou sur ce PC (localhost).

if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {
            // Un certificat refusé par le navigateur empêche l'installation, pas
            // l'usage du tableau de bord : rien n'est signalé à l'utilisateur.
        });
    });
}
