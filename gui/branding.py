"""Icône de l'application dessinée à partir de son logo"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from config import LOGO_FILE

# Tailles demandées par Windows pour la barre de titre, la barre des tâches et Alt+Tab
LOGO_SIZES = (16, 24, 32, 48, 64, 128)


def create_logo_icon():
    """Retourne l'icône de l'application, lissée à chaque taille standard."""

    vLogo = QPixmap(str(LOGO_FILE))

    rIcon = QIcon()

    for vSize in LOGO_SIZES:
        rIcon.addPixmap(
            vLogo.scaled(
                vSize,
                vSize,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    return rIcon
