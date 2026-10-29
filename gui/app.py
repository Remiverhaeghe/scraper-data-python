"""Lancement de l'application de bureau"""

import ctypes
import sys

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from config import APPLICATION_NAME, DATABASE_FILE
from gui.branding import create_logo_icon
from gui.main_window import MainWindow
from gui.theme import TEXT_SCALE_SETTING, THEME_SETTING, apply_theme
from utils.logger import get_logger

logger = get_logger(__name__)

# Identifiant propre à l'application : sans lui, Windows regroupe la fenêtre
# sous l'icône de Python dans la barre des tâches.
WINDOWS_APP_ID = "Remiverhaeghe.JobBoardPerso"


class DesktopApplication:
    """Ouvre la fenêtre principale et en repeint le contenu au changement de thème."""

    def __init__(self, pApplication, pSettings):
        """Applique le thème mémorisé puis ouvre la fenêtre."""
        self.application = pApplication
        self.settings = pSettings

        # Sans choix mémorisé, le premier lancement suit le thème de Windows.
        vTheme = apply_theme(
            self.application,
            self.settings.value(THEME_SETTING, "system", str),
            self.settings.value(TEXT_SCALE_SETTING, 100, int),
        )

        self.window = MainWindow(DATABASE_FILE, APPLICATION_NAME)
        self.window.theme_requested.connect(self.change_theme)
        self.window.text_scale_requested.connect(self.change_text_scale)
        self.window.showMaximized()

        logger.info("Application de bureau ouverte avec le thème %s", vTheme)

    def change_theme(self, pTheme):
        """Mémorise le thème choisi et repeint la fenêtre sans la recréer."""
        self.settings.setValue(THEME_SETTING, pTheme)

        # Différé : le clic vient d'un bouton de la page qui va être détruite.
        QTimer.singleShot(0, self.restyle_window)

        logger.info("Thème %s appliqué", pTheme)

    def change_text_scale(self, pTextScale):
        """Mémorise la taille du texte choisie et repeint la fenêtre."""
        self.settings.setValue(TEXT_SCALE_SETTING, pTextScale)

        QTimer.singleShot(0, self.restyle_window)

        logger.info("Taille du texte : %s %%", pTextScale)

    def restyle_window(self):
        """Applique le thème et la taille mémorisés, puis reconstruit les pages."""
        self.window.rebuild(
            "settings",
            lambda: apply_theme(
                self.application,
                self.settings.value(THEME_SETTING, "system", str),
                self.settings.value(TEXT_SCALE_SETTING, 100, int),
            ),
        )


def run():
    """Ouvre l'application et retourne le code de sortie de Qt."""

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)

    vApplication = QApplication(sys.argv)
    vApplication.setApplicationName(APPLICATION_NAME)
    vApplication.setWindowIcon(create_logo_icon())

    # Nom utilisé par QSettings pour mémoriser le thème et les derniers critères
    vApplication.setOrganizationName("Remiverhaeghe")

    # Fusion respecte la palette fournie, identique sur toutes les plateformes.
    vApplication.setStyle("Fusion")

    # La référence garde la fenêtre en vie pendant toute la boucle d'événements.
    vDesktop = DesktopApplication(vApplication, QSettings())

    rExitCode = vApplication.exec()

    del vDesktop

    return rExitCode
