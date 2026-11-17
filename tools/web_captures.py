"""Captures d'écran du tableau de bord web sur des données fictives

Remplit une base temporaire avec des offres et des candidatures inventées,
démarre le tableau de bord sur un port libre, s'y connecte avec Playwright et
enregistre une capture de chaque page listée dans CAPTURES. Sert aux images du
portfolio et du README, qui suivent ainsi l'interface sans retouche.

    python -m tools.web_captures captures/
"""

import argparse
import logging
import os
import secrets
import socket
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import uvicorn

from storage.database import initialize_database
from storage.geo_cache import save_offer_positions
from storage.job_applications import create_application
from storage.job_offers import save_offers
from web.app import app
from web.auth import hash_password
from web.dependencies import get_database_file

logger = logging.getLogger(__name__)

# Page du tableau de bord et nom du fichier produit
CAPTURES = (
    ("/", "tableau-de-bord.png"),
    ("/offers", "offres.png"),
    ("/applications", "candidatures.png"),
    ("/market", "marche.png"),
)

VIEWPORT = {"width": 1280, "height": 800}

# Entreprises et offres inventées : aucune donnée réelle dans les captures
OFFERS = (
    ("Développeur Java", "Démo Rail", "Lille", 59, "CDI", 38000, 45000, True),
    ("Développeur Python", "Exemple Énergie", "Roubaix", 59, "CDI", 36000, 42000, True),
    ("Data engineer", "Atelier Démo", "Lille", 59, "CDI", 42000, 50000, False),
    ("Développeur web PHP", "Société Exemple", "Arras", 62, "CDD", 30000, 34000, False),
    ("Ingénieur DevOps", "Démo Logistique", "Lens", 62, "CDI", 45000, 52000, True),
    (
        "Développeur Java Spring",
        "Exemple Santé",
        "Villeneuve-d'Ascq",
        59,
        "CDI",
        40000,
        46000,
        True,
    ),
    (
        "Technicien support applicatif",
        "Démo Industrie",
        "Douai",
        59,
        "CDI",
        28000,
        32000,
        False,
    ),
    (
        "Développeur full stack",
        "Exemple Transport",
        "Tourcoing",
        59,
        "CDI",
        37000,
        43000,
        True,
    ),
    ("Analyste développeur", "Démo Assurance", "Lille", 59, "CDI", 39000, 44000, False),
    (
        "Développeur Flutter",
        "Atelier Exemple",
        "Valenciennes",
        59,
        "Freelance",
        None,
        None,
        True,
    ),
    (
        "Administrateur systèmes Linux",
        "Démo Collectivité",
        "Béthune",
        62,
        "CDI",
        33000,
        38000,
        False,
    ),
    (
        "Développeur Java junior",
        "Exemple Services",
        "Lille",
        59,
        "CDI",
        32000,
        36000,
        True,
    ),
)

POSITIONS = {
    "Lille": (50.63, 3.06),
    "Roubaix": (50.69, 3.17),
    "Arras": (50.29, 2.78),
    "Lens": (50.43, 2.83),
    "Villeneuve-d'Ascq": (50.62, 3.14),
    "Douai": (50.37, 3.08),
    "Tourcoing": (50.72, 3.16),
    "Valenciennes": (50.36, 3.52),
    "Béthune": (50.53, 2.64),
}

# Suivi de quelques offres, pour que la page des candidatures ne soit pas vide
APPLICATIONS = (
    (0, "INTERVIEW", 12),
    (1, "APPLIED", 6),
    (4, "APPLIED", 3),
    (5, "REJECTED", 20),
    (7, "INTERESTED", 1),
)


def build_offers(pNow):
    """Construit le tableau des offres fictives, publiées sur les dix derniers jours."""

    vRows = []

    for vIndex, (
        vTitle,
        vCompany,
        vCity,
        vDepartment,
        vContract,
        vMin,
        vMax,
        vRemote,
    ) in enumerate(OFFERS):
        vRows.append(
            {
                "source": "demo",
                "source_id": str(vIndex),
                "title": vTitle,
                "company": vCompany,
                "location": f"{vCity} ({vDepartment})",
                "city": vCity,
                "department": str(vDepartment),
                "country": "France",
                "contract_type": vContract,
                "salary_min": vMin,
                "salary_max": vMax,
                "salary_currency": "EUR" if vMin else None,
                "salary_period": "year" if vMin else None,
                "remote": vRemote,
                "published_at": (pNow - timedelta(days=vIndex % 10)).isoformat(),
                "url": f"https://example.com/offres/{vIndex}",
            }
        )

    rOffers = pd.DataFrame(vRows)
    return rOffers


def fill_database(pDatabaseFile, pNow):
    """Remplit la base avec les offres, leurs positions et quelques candidatures."""

    initialize_database(pDatabaseFile)
    save_offers(pDatabaseFile, build_offers(pNow), pNow)
    save_offer_positions(
        pDatabaseFile,
        [
            (*POSITIONS[vOffer[2]], str(vOffer[3]), "demo", str(vIndex))
            for vIndex, vOffer in enumerate(OFFERS)
        ],
    )

    for vIndex, vStatus, vDaysAgo in APPLICATIONS:
        create_application(
            pDatabaseFile,
            "demo",
            str(vIndex),
            pStatus=vStatus,
            pAppliedAt=pNow - timedelta(days=vDaysAgo),
        )


def get_free_port():
    """Retourne un port TCP libre sur la machine locale."""

    with socket.socket() as vSocket:
        vSocket.bind(("127.0.0.1", 0))
        rPort = vSocket.getsockname()[1]

    return rPort


def take_captures(pBaseUrl, pPassword, pOutput):
    """Se connecte au tableau de bord et enregistre une capture par page."""

    # Importé ici : Playwright ne sert qu'à cet outil, pas à l'application
    # pylint: disable-next=import-outside-toplevel
    from playwright.sync_api import sync_playwright

    rFiles = []

    with sync_playwright() as vPlaywright:
        vBrowser = vPlaywright.chromium.launch()
        vPage = vBrowser.new_page(
            base_url=pBaseUrl, viewport=VIEWPORT, device_scale_factor=2
        )
        vPage.goto("/login")
        vPage.fill("input[name=username]", "demo")
        vPage.fill("input[name=password]", pPassword)
        vPage.click("button[type=submit]")
        vPage.wait_for_url(f"{pBaseUrl}/")

        for vPath, vName in CAPTURES:
            vPage.goto(vPath)
            vPage.wait_for_load_state("networkidle")
            vFile = pOutput / vName
            vPage.screenshot(path=str(vFile))
            logger.info("Capture enregistrée : %s", vFile)
            rFiles.append(vFile)

        vBrowser.close()

    return rFiles


def main():
    """Point d'entrée : base fictive, serveur local, puis captures."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    vParser = argparse.ArgumentParser(description=__doc__)
    vParser.add_argument("output", type=Path, help="dossier des captures")
    vArgs = vParser.parse_args()
    vArgs.output.mkdir(parents=True, exist_ok=True)

    # Compte jetable, valable le temps des captures
    vPassword = secrets.token_urlsafe(16)
    os.environ["WEB_USERNAME"] = "demo"
    os.environ["WEB_PASSWORD_HASH"] = hash_password(vPassword, 1000)
    os.environ["WEB_SESSION_SECRET"] = secrets.token_hex(32)
    os.environ.pop("WEB_TOTP_SECRET", None)

    with tempfile.TemporaryDirectory() as vDirectory:
        vDatabaseFile = Path(vDirectory) / "scraper.db"
        app.dependency_overrides[get_database_file] = lambda: vDatabaseFile
        fill_database(vDatabaseFile, datetime.now())

        vPort = get_free_port()
        vServer = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=vPort, log_level="warning")
        )
        vThread = threading.Thread(target=vServer.run, daemon=True)
        vThread.start()

        while not vServer.started:
            time.sleep(0.05)

        try:
            take_captures(f"http://127.0.0.1:{vPort}", vPassword, vArgs.output)
        finally:
            vServer.should_exit = True
            vThread.join(timeout=10)
            app.dependency_overrides.clear()


if __name__ == "__main__":
    main()
