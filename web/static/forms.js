// Comportements des formulaires, sans attribut JavaScript en ligne que la CSP bloquerait
(function () {
    document.addEventListener("change", function (pEvent) {
        var vField = pEvent.target.closest("[data-autosubmit]");

        if (vField && vField.form) {
            vField.form.requestSubmit();
        }
    });
})();
