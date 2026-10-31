// Planning de la semaine : une tâche glissée sur un autre jour y est déplacée,
// puis la page se recharge. Le jeton CSRF est celui que la page donne à htmx.
(function () {
    function start(pWeek) {
        var vToken = JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRF-Token"];

        pWeek.querySelectorAll("[data-item]").forEach(function (pItem) {
            pItem.addEventListener("dragstart", function (pEvent) {
                pEvent.dataTransfer.setData("text/plain", pItem.dataset.item);
            });
        });

        pWeek.querySelectorAll("[data-day]").forEach(function (pDay) {
            pDay.addEventListener("dragover", function (pEvent) {
                pEvent.preventDefault();
                pDay.classList.add("is-target");
            });
            pDay.addEventListener("dragleave", function () {
                pDay.classList.remove("is-target");
            });
            pDay.addEventListener("drop", function (pEvent) {
                var vBody = new URLSearchParams();

                pEvent.preventDefault();
                vBody.set("item", pEvent.dataTransfer.getData("text/plain"));
                vBody.set("day", pDay.dataset.day);
                fetch(pWeek.dataset.moveUrl, {
                    method: "POST",
                    headers: { "X-CSRF-Token": vToken, "X-Requested-With": "fetch" },
                    body: vBody
                }).then(function () {
                    window.location.reload();
                });
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-planning]").forEach(start);
    });
}());
