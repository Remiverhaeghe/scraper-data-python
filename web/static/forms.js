// Comportements des formulaires, sans attribut JavaScript en ligne que la CSP bloquerait
(function () {
    document.addEventListener("change", function (pEvent) {
        var vField = pEvent.target.closest("[data-autosubmit]");

        if (vField && vField.form) {
            vField.form.requestSubmit();
        }
    });

    // Copie le texte d'une demande puis ouvre le site indiqué (ChatGPT).
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

        vButton.textContent = "Copié : collez dans ChatGPT";

        if (vButton.dataset.open) {
            window.open(vButton.dataset.open, "_blank", "noopener");
        }
    });
})();
