"""Icône de l'application dessinée à partir de son logo"""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import LOGO_FILE

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
