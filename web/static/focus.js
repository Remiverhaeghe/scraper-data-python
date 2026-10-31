// Session de concentration : l'anneau se vide seconde après seconde, puis la
// page se recharge à la fin ; le serveur clôt alors la session et affiche le bilan.
(function () {
    var TICK_MS = 1000;

    function start(pRing) {
        var vClock = pRing.querySelector("[data-focus-clock]");
        var vDuration = Number(pRing.dataset.duration);
        var vEnd = Date.now() + Number(pRing.dataset.remaining) * 1000;

        function tick() {
            var vRemaining = Math.max(0, Math.round((vEnd - Date.now()) / 1000));

            pRing.style.setProperty("--share", vRemaining / vDuration);
            vClock.textContent = String(Math.floor(vRemaining / 60)).padStart(2, "0") + ":" + String(vRemaining % 60).padStart(2, "0");

            if (vRemaining === 0) {
                window.clearInterval(vTimer);
                window.location.reload();
            }
        }

        var vTimer = window.setInterval(tick, TICK_MS);

        tick();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-focus-ring]").forEach(start);
    });
}());
