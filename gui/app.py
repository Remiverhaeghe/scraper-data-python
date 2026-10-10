"""Lancement de l'application de bureau"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config import DATABASE_FILE
from gui.main_window import MainWindow
from utils.logger import get_logger

logger = get_logger(__name__)

APPLICATION_NAME = "RV - Web Scraper"

THEME_FILE = Path(__file__).with_name("theme.qss")


def run():
    """Ouvre la fenêtre principale et retourne le code de sortie de Qt."""

    vApplication = QApplication(sys.argv)
    vApplication.setApplicationName(APPLICATION_NAME)

    # Nom utilisé par QSettings pour mémoriser les derniers critères de recherche
    vApplication.setOrganizationName("Remiverhaeghe")

    # Fusion suit le thème clair ou sombre du système sur toutes les plateformes.
    vApplication.setStyle("Fusion")
    vApplication.setStyleSheet(THEME_FILE.read_text(encoding="utf-8"))

    vWindow = MainWindow(DATABASE_FILE, APPLICATION_NAME)
    vWindow.show()

    logger.info("Interface graphique ouverte")

    rExitCode = vApplication.exec()

    return rExitCode
