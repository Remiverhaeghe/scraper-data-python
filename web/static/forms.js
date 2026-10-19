// Comportements des formulaires, sans attribut JavaScript en ligne que la CSP bloquerait
(function () {
    document.addEventListener("change", function (pEvent) {
        var vField = pEvent.target.closest("[data-autosubmit]");

        if (vField && vField.form) {
            vField.form.requestSubmit();
        }
    });

    // Copie le texte d'un champ, puis ouvre le site indiqué s'il y en a un (ChatGPT).
    // navigator.clipboard n'existe qu'en HTTPS ou en local : par Tailscale en HTTP,
    // la sélection du texte et execCommand prennent le relais.
    document.addEventListener("click", function (pEvent) {
        var vButton = pEvent.target.closest("[data-copy]");

        if (!vButton) {
            return;
        }

        var vText = document.querySelector("#" + vButton.dataset.copy + " textarea");

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(vText.value);
        } else {
            vText.select();
            document.execCommand("copy");
        }

        vButton.textContent = vButton.dataset.copied || "Copié : collez dans ChatGPT";

        if (vButton.dataset.open) {
            window.open(vButton.dataset.open, "_blank", "noopener");
        }
    });

    // Cartes titrées : un chevron dans le titre replie la carte. L'état est gardé
    // par page et par titre ; sans JavaScript, les cartes restent ouvertes.
    document.querySelectorAll("article.card > h2:first-child").forEach(function (pTitle) {
        var vCard = pTitle.parentElement;
        var vKey = "card:" + location.pathname + ":" + pTitle.textContent.trim();
        var vButton = document.createElement("button");

        vButton.type = "button";
        vButton.className = "card-toggle";

        function setOpen(pOpen) {
            vCard.classList.toggle("is-collapsed", !pOpen);
            vButton.setAttribute("aria-expanded", pOpen ? "true" : "false");
            vButton.setAttribute("aria-label", pOpen ? "Réduire" : "Afficher");
            vButton.title = pOpen ? "Réduire" : "Afficher";
        }

        var vOpen = true;

        try {
            vOpen = localStorage.getItem(vKey) !== "1";
        } catch (pError) {
            vOpen = true;
        }

        setOpen(vOpen);
        pTitle.classList.add("card-title");
        pTitle.appendChild(vButton);

        vButton.addEventListener("click", function () {
            var vNowOpen = vCard.classList.contains("is-collapsed");

            setOpen(vNowOpen);

            try {
                localStorage.setItem(vKey, vNowOpen ? "0" : "1");
            } catch (pError) {
                // Stockage indisponible : la carte se rouvrira au prochain affichage.
            }
        });
    });

    // Blocs repliables : l'état choisi est gardé d'une page à l'autre, quand le
    // navigateur le permet (navigation privée, stockage bloqué).
    document.querySelectorAll("details[data-remember]").forEach(function (pDetails) {
        var vKey = "collapsed:" + pDetails.dataset.remember;

        try {
            if (localStorage.getItem(vKey) === "1") {
                pDetails.open = false;
            }
        } catch (pError) {
            return;
        }

        pDetails.addEventListener("toggle", function () {
            try {
                localStorage.setItem(vKey, pDetails.open ? "0" : "1");
            } catch (pError) {
                // Stockage indisponible : le bloc se rouvrira au prochain affichage.
            }
        });
    });

    // Compte à rebours de l'examen : même texte que format_countdown côté serveur.
    document.querySelectorAll(".exam-timer[data-remaining]").forEach(function (pTimer) {
        var vRemaining = parseInt(pTimer.dataset.remaining, 10);

        function pad(pValue) {
            return String(pValue).padStart(2, "0");
        }

        function show() {
            var vSeconds = Math.abs(vRemaining);
            var vText = pad(Math.floor(vSeconds / 60)) + ":" + pad(vSeconds % 60);

            pTimer.textContent = vRemaining >= 0
                ? "Temps restant : " + vText
                : "Temps dépassé de " + vText;
            pTimer.classList.toggle("tone-success", vRemaining >= 60);
            pTimer.classList.toggle("tone-warning", vRemaining >= 0 && vRemaining < 60);
            pTimer.classList.toggle("tone-danger", vRemaining < 0);
        }

        window.setInterval(function () {
            vRemaining -= 1;
            show();
        }, 1000);
    });
})();
