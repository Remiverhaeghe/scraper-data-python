"""Lancement de l'application de bureau"""

import sys

from PySide6.QtWidgets import QApplication

from config import DATABASE_FILE
from gui.main_window import MainWindow
from gui.theme import build_palette, build_stylesheet
from utils.logger import get_logger

logger = get_logger(__name__)

APPLICATION_NAME = "RV - Web Scraper"


def run():
    """Ouvre la fenêtre principale et retourne le code de sortie de Qt."""

    vApplication = QApplication(sys.argv)
    vApplication.setApplicationName(APPLICATION_NAME)

    # Nom utilisé par QSettings pour mémoriser les derniers critères de recherche
    vApplication.setOrganizationName("Remiverhaeghe")

    # Fusion respecte la palette fournie, identique sur toutes les plateformes.
    vApplication.setStyle("Fusion")
    vApplication.setPalette(build_palette())
    vApplication.setStyleSheet(build_stylesheet())

    vWindow = MainWindow(DATABASE_FILE, APPLICATION_NAME)
    vWindow.show()

    logger.info("Interface graphique ouverte")

    rExitCode = vApplication.exec()

    return rExitCode
