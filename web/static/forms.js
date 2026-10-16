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
})();
