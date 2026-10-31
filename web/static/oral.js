// Entretien oral simulé : lecture de la question par la synthèse vocale du
// navigateur, chrono de la réponse, puis grille de notation. La durée mesurée
// remplit le champ du formulaire ; sans ce script, elle se saisit à la main.
(function () {
    var TICK_MS = 250;

    function format(pSeconds) {
        var vSeconds = Math.abs(Math.trunc(pSeconds));

        return (pSeconds < 0 ? "-" : "") + Math.floor(vSeconds / 60) + ":" + String(vSeconds % 60).padStart(2, "0");
    }

    function start(pCard) {
        var vQuestion = pCard.querySelector("[data-oral-question]");
        var vListen = pCard.querySelector("[data-oral-listen]");
        var vBegin = pCard.querySelector("[data-oral-begin]");
        var vDone = pCard.querySelector("[data-oral-done]");
        var vClock = pCard.querySelector("[data-oral-clock]");
        var vGrid = pCard.querySelector("[data-oral-grid]");
        var vSeconds = pCard.querySelector("[data-oral-seconds]");

        if (!vQuestion || !vGrid) {
            return;
        }

        var vDuration = Number(vClock.dataset.duration);
        var vStart = null;
        var vTimer = null;

        function tick() {
            var vRemaining = vDuration - (Date.now() - vStart) / 1000;

            vClock.textContent = format(vRemaining);
            vClock.classList.toggle("tone-danger", vRemaining < 0);
        }

        function begin() {
            if (vStart !== null) {
                return;
            }

            window.speechSynthesis && window.speechSynthesis.cancel();
            vStart = Date.now();
            vTimer = window.setInterval(tick, TICK_MS);
            vBegin.hidden = true;
            vListen.hidden = true;
            vDone.hidden = false;
            tick();
        }

        function listen() {
            var vUtterance = new SpeechSynthesisUtterance(vQuestion.textContent);

            vUtterance.lang = "fr-FR";
            vUtterance.onend = begin;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(vUtterance);
        }

        vGrid.hidden = true;
        vSeconds.readOnly = true;
        vClock.textContent = format(vDuration);
        vBegin.hidden = false;
        vBegin.addEventListener("click", begin);

        // La lecture demande un clic : les navigateurs refusent de parler d'eux-mêmes.
        if ("speechSynthesis" in window) {
            vListen.hidden = false;
            vListen.addEventListener("click", listen);
        }

        vDone.addEventListener("click", function () {
            window.clearInterval(vTimer);
            vSeconds.value = Math.round((Date.now() - vStart) / 1000);
            vDone.hidden = true;
            vGrid.hidden = false;
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-oral]").forEach(start);
    });
}());
