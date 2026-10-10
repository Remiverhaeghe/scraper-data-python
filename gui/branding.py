"""Identité de l'application : nom, slogan, logo et liens"""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

APPLICATION_NAME = "RV Veille Emploi"

TAGLINE = "Offres, candidatures et relances au même endroit"

REPOSITORY_URL = "https://github.com/Remiverhaeghe/scraper-data-python"

LICENSE_NAME = "PolyForm Strict 1.0.0"

LOGO_FILE = Path(__file__).with_name("logo.svg")

# Tailles demandées par Windows pour la barre de titre, la barre des tâches et Alt+Tab
LOGO_SIZES = (16, 24, 32, 48, 64, 256)


def create_logo_icon():
    """Retourne l'icône de l'application, dessinée à chaque taille standard."""

    vRenderer = QSvgRenderer(QByteArray(LOGO_FILE.read_bytes()))

    rIcon = QIcon()

    for vSize in LOGO_SIZES:
        vPixmap = QPixmap(vSize, vSize)
        vPixmap.fill(Qt.GlobalColor.transparent)

        vPainter = QPainter(vPixmap)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vRenderer.render(vPainter)
        vPainter.end()

        rIcon.addPixmap(vPixmap)

    return rIcon
