// Points gagnés, quêtes réussies et passage de niveau, repérés dans l'encart du menu
// en le comparant à la dernière visite. Le mode « Jeu et animations » est gardé
// dans ce navigateur ; sans choix, il suit la préférence « réduire les animations ».
(function () {
    var MODE_KEY = "jobboard-game";
    var LAST_KEY = "jobboard-progress";
    var MODES = ["full", "discreet", "off"];
    var TOAST_GAP_MS = 700;
    var CELEBRATION_MS = 2600;
    var CONFETTI_COUNT = 90;
    var CONFETTI_COLORS = ["#3B82F6", "#F59E0B", "#8B5CF6", "#10B981", "#EC4899", "#06B6D4"];

    function readStorage(pKey) {
        try {
            return localStorage.getItem(pKey);
        } catch (vError) {
            return null;
        }
    }

    function writeStorage(pKey, pValue) {
        try {
            localStorage.setItem(pKey, pValue);
        } catch (vError) {
            // Stockage indisponible (navigation privée) : rien n'est comparé.
        }
    }

    function getMode() {
        var vMode = readStorage(MODE_KEY);

        if (MODES.indexOf(vMode) >= 0) {
            return vMode;
        }

        return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "discreet" : "full";
    }

    function applyMode() {
        var vMode = getMode();

        document.documentElement.dataset.game = vMode;
        document.querySelectorAll("[data-game-choice]").forEach(function (pButton) {
            pButton.classList.toggle("is-active", pButton.dataset.gameChoice === vMode);
        });
    }

    function showToast(pText, pAnchor, pDelay) {
        window.setTimeout(function () {
            var vToast = document.createElement("div");
            var vRect = pAnchor.getBoundingClientRect();

            vToast.className = "xp-toast";
            vToast.textContent = pText;
            vToast.style.top = vRect.top + "px";
            vToast.addEventListener("animationend", function () {
                vToast.remove();
            });
            document.body.appendChild(vToast);
            // Centrée sur l'encart, mais sans sortir de l'écran à gauche.
            vToast.style.left = Math.max(
                vRect.left + vRect.width / 2,
                vToast.offsetWidth / 2 + 8
            ) + "px";
        }, pDelay || 0);
    }

    function drawConfetti(pCanvas, pStart) {
        var vContext = pCanvas.getContext("2d");
        var vPieces = [];

        for (var vIndex = 0; vIndex < CONFETTI_COUNT; vIndex++) {
            vPieces.push({
                x: Math.random() * pCanvas.width,
                y: -Math.random() * pCanvas.height * 0.6,
                speed: 0.18 + Math.random() * 0.24,
                drift: (Math.random() - 0.5) * 0.12,
                spin: (Math.random() - 0.5) * 0.024,
                angle: Math.random() * Math.PI,
                size: 6 + Math.random() * 6,
                color: CONFETTI_COLORS[vIndex % CONFETTI_COLORS.length]
            });
        }

        function frame(pNow) {
            var vElapsed = pNow - pStart;

            if (!pCanvas.isConnected) {
                return;
            }

            vContext.clearRect(0, 0, pCanvas.width, pCanvas.height);
            vPieces.forEach(function (pPiece) {
                vContext.save();
                vContext.translate(
                    pPiece.x + pPiece.drift * vElapsed,
                    (pPiece.y + pPiece.speed * vElapsed) % (pCanvas.height + 40)
                );
                vContext.rotate(pPiece.angle + pPiece.spin * vElapsed);
                vContext.fillStyle = pPiece.color;
                vContext.fillRect(-pPiece.size / 2, -pPiece.size / 4, pPiece.size, pPiece.size / 2);
                vContext.restore();
            });
            window.requestAnimationFrame(frame);
        }

        window.requestAnimationFrame(frame);
    }

    function celebrate(pTitle, pSubtitle, pDetail) {
        var vOverlay = document.createElement("div");
        var vCanvas = document.createElement("canvas");
        var vCard = document.createElement("div");

        vOverlay.className = "celebration";
        vOverlay.setAttribute("role", "status");
        vCanvas.width = window.innerWidth;
        vCanvas.height = window.innerHeight;
        vCard.className = "celebration-card";
        [["strong", pTitle], ["span", pSubtitle], ["small", pDetail]].forEach(function (pPart) {
            var vElement = document.createElement(pPart[0]);

            vElement.textContent = pPart[1];
            vCard.appendChild(vElement);
        });

        vOverlay.appendChild(vCanvas);
        vOverlay.appendChild(vCard);
        vOverlay.addEventListener("click", function () {
            vOverlay.remove();
        });
        document.body.appendChild(vOverlay);
        drawConfetti(vCanvas, performance.now());
        window.setTimeout(function () {
            vOverlay.classList.add("is-leaving");
            window.setTimeout(function () {
                vOverlay.remove();
            }, 350);
        }, CELEBRATION_MS);
    }

    function readLast() {
        try {
            return JSON.parse(readStorage(LAST_KEY) || "null");
        } catch (vError) {
            return null;
        }
    }

    function check(pBox) {
        var vMode = getMode();
        var vNow = {
            xp: Number(pBox.dataset.xp),
            level: Number(pBox.dataset.level),
            quests: pBox.dataset.quests ? pBox.dataset.quests.split("|") : []
        };
        var vLast = readLast();
        var vDelay = 0;

        writeStorage(LAST_KEY, JSON.stringify(vNow));

        // Première visite : la référence, sans fête pour l'historique.
        if (vMode === "off" || !vLast) {
            return;
        }

        if (vNow.xp > vLast.xp) {
            showToast("+" + (vNow.xp - vLast.xp) + " XP", pBox, vDelay);
            vDelay += TOAST_GAP_MS;
        }

        vNow.quests.forEach(function (pQuest) {
            if ((vLast.quests || []).indexOf(pQuest) < 0) {
                showToast("Quête réussie : " + pQuest, pBox, vDelay);
                vDelay += TOAST_GAP_MS;
            }
        });

        if (vNow.level > vLast.level) {
            if (vMode === "full") {
                celebrate(
                    "Niveau " + vNow.level,
                    pBox.dataset.title,
                    "Prochain titre : " + pBox.dataset.nextTitle
                );
            } else {
                showToast("Niveau " + vNow.level + " : " + pBox.dataset.title, pBox, vDelay);
            }
        }
    }

    applyMode();

    document.addEventListener("htmx:afterSwap", function (pEvent) {
        var vBox = pEvent.detail.target.querySelector(".progress-box");

        if (vBox) {
            check(vBox);
        }
    });

    document.addEventListener("click", function (pEvent) {
        var vChoiceButton = pEvent.target.closest("[data-game-choice]");

        if (vChoiceButton) {
            writeStorage(MODE_KEY, vChoiceButton.dataset.gameChoice);
            applyMode();
        }
    });

    document.addEventListener("DOMContentLoaded", applyMode);
})();
