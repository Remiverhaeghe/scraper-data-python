"""Configuration commune des tests de l'interface graphique"""

import os

import pytest

# Les tests tournent sans écran, en local comme sur la CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qt_application():
    """Fournit l'unique QApplication autorisée par Qt."""

    rApplication = QApplication.instance() or QApplication([])

    return rApplication


@pytest.fixture(autouse=True)
def close_windows():
    """Détruit les fenêtres laissées par un test, pour que les suivants restent rapides.

    Sans ce nettoyage, chaque changement de thème restyle toutes les pages
    créées par les tests précédents.
    """

    yield

    vApplication = QApplication.instance()

    if vApplication is not None:
        for vWidget in vApplication.topLevelWidgets():
            vWidget.close()
            vWidget.deleteLater()

        # deleteLater attend la boucle d'événements : la suppression est forcée ici.
        vApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
