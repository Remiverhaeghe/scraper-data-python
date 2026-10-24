// Enregistre le service worker qui rend le tableau de bord installable et
// lisible hors connexion. Les navigateurs ne l'acceptent qu'en HTTPS, ou sur
// ce PC (localhost).

if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {
            // Un certificat refusé par le navigateur empêche l'installation, pas
            // l'usage du tableau de bord : rien n'est signalé à l'utilisateur.
        });
    });
}

// Bandeau affiché sans réseau : la page lue est la dernière copie gardée, et
// les actions (statut, notes, recherche) attendent le retour du réseau.
function showConnectionState() {
    let vBanner = document.getElementById("offline-banner");

    if (navigator.onLine) {
        vBanner?.remove();
        return;
    }

    if (!vBanner) {
        vBanner = document.createElement("p");
        vBanner.id = "offline-banner";
        vBanner.className = "offline-banner";
        vBanner.setAttribute("role", "status");
        vBanner.textContent =
            "Hors connexion : vous lisez la dernière copie de cette page. " +
            "Les modifications seront possibles au retour du réseau.";
        document.body.prepend(vBanner);
    }
}

window.addEventListener("online", showConnectionState);
window.addEventListener("offline", showConnectionState);
document.addEventListener("DOMContentLoaded", showConnectionState);
