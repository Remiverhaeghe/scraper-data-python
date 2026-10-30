// Partie de test de recrutement : une question à la fois, réponse suivante au clic,
// compte à rebours, formulaire envoyé à la fin du temps. Sans ce script, toutes les
// questions restent visibles et le bouton « Terminer » suffit.
(function () {
    var TICK_MS = 1000;

    function start(pForm) {
        var vQuestions = pForm.querySelectorAll("[data-aptitude-question]");
        var vTimer = document.querySelector("[data-aptitude-timer]");
        var vEnd = Date.now() + Number(pForm.dataset.seconds) * 1000;
        var vCurrent = 0;
        var vSent = false;

        function show(pIndex) {
            vQuestions.forEach(function (pQuestion, vIndex) {
                pQuestion.hidden = vIndex !== pIndex;
            });
        }

        function send() {
            if (!vSent) {
                vSent = true;
                pForm.submit();
            }
        }

        function tick() {
            var vRemaining = Math.max(0, Math.round((vEnd - Date.now()) / 1000));

            if (vTimer) {
                vTimer.textContent = Math.floor(vRemaining / 60) + ":" + String(vRemaining % 60).padStart(2, "0");
            }

            if (vRemaining === 0) {
                send();
            }
        }

        pForm.addEventListener("change", function (pEvent) {
            if (pEvent.target.type !== "radio") {
                return;
            }

            vCurrent += 1;

            if (vCurrent >= vQuestions.length) {
                send();
            } else {
                show(vCurrent);
            }
        });

        show(0);
        tick();
        window.setInterval(tick, TICK_MS);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var vForm = document.querySelector("[data-aptitude-form]");

        if (vForm) {
            start(vForm);
        }
    });
})();
