// Carte des offres : lit les points du gabarit et les place sur un fond
// OpenStreetMap. Les textes sont insérés comme texte, jamais comme HTML.
document.addEventListener("DOMContentLoaded", () => {
    const vElement = document.getElementById("offers-map");
    const vData = JSON.parse(document.getElementById("map-data").textContent);
    const vStyles = getComputedStyle(document.documentElement);
    const vColors = {
        success: vStyles.getPropertyValue("--success").trim(),
        warning: vStyles.getPropertyValue("--warning").trim(),
        muted: vStyles.getPropertyValue("--muted").trim(),
        primary: vStyles.getPropertyValue("--primary").trim(),
    };

    const vMap = L.map(vElement);

    // Sans Referer, les serveurs de tuiles d'OpenStreetMap refusent la demande.
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: "© contributeurs OpenStreetMap",
    }).addTo(vMap);

    const vBounds = [];

    for (const vPoint of vData.points) {
        const vPosition = [vPoint.latitude, vPoint.longitude];
        const vPopup = document.createElement("div");
        const vLink = document.createElement("a");
        const vDetail = document.createElement("div");

        vLink.href = vPoint.url;
        vLink.textContent = vPoint.title;
        vDetail.textContent = vPoint.score === null
            ? vPoint.detail
            : `${vPoint.detail} · ${vPoint.score} %`;
        vPopup.append(vLink, vDetail);

        L.circleMarker(vPosition, {
            radius: 8,
            weight: 1,
            color: "#ffffff",
            fillColor: vColors[vPoint.tone || "muted"],
            fillOpacity: 0.9,
        }).bindPopup(vPopup).addTo(vMap);

        vBounds.push(vPosition);
    }

    if (vData.home) {
        const vHome = [vData.home.latitude, vData.home.longitude];

        L.circleMarker(vHome, { radius: 10, color: vColors.primary, fillOpacity: 1 })
            .bindTooltip(`Domicile · ${vData.home.label}`)
            .addTo(vMap);

        if (vData.radius) {
            L.circle(vHome, {
                radius: vData.radius * 1000,
                color: vColors.primary,
                fillOpacity: 0.05,
            }).addTo(vMap);
        }

        vBounds.push(vHome);
    }

    if (vBounds.length) {
        vMap.fitBounds(vBounds, { padding: [30, 30], maxZoom: 11 });
    } else {
        // Aucune offre placée : la France entière
        vMap.setView([46.6, 2.4], 5);
    }
});
