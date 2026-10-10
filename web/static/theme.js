// Applique le thème choisi avant l'affichage de la page, pour éviter un flash de couleurs
(function () {
    var STORAGE_KEY = "theme";
    var vSystemDark = window.matchMedia("(prefers-color-scheme: dark)");

    function readChoice() {
        try {
            return localStorage.getItem(STORAGE_KEY) || "system";
        } catch (vError) {
            return "system";
        }
    }

    function saveChoice(pChoice) {
        try {
            localStorage.setItem(STORAGE_KEY, pChoice);
        } catch (vError) {
            // Stockage indisponible (navigation privée) : le choix vaut pour la page.
        }
    }

    function applyChoice(pChoice) {
        var vTheme = pChoice;

        if (pChoice !== "light" && pChoice !== "dark") {
            vTheme = vSystemDark.matches ? "dark" : "light";
        }

        document.documentElement.dataset.theme = vTheme;
        document.documentElement.dataset.themeChoice = pChoice;
    }

    applyChoice(readChoice());

    vSystemDark.addEventListener("change", function () {
        applyChoice(readChoice());
    });

    document.addEventListener("click", function (pEvent) {
        var vChoiceButton = pEvent.target.closest("[data-theme-choice]");
        var vToggleButton = pEvent.target.closest("[data-theme-toggle]");
        var vChoice = null;

        if (vChoiceButton) {
            vChoice = vChoiceButton.dataset.themeChoice;
        } else if (vToggleButton) {
            vChoice = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        }

        if (vChoice) {
            saveChoice(vChoice);
            applyChoice(vChoice);
        }
    });
})();
