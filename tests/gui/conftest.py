"""Configuration commune des tests de l'interface graphique"""

import os

import pytest

# Les tests tournent sans écran, en local comme sur la CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qt_application():
    """Fournit l'unique QApplication autorisée par Qt."""

    rApplication = QApplication.instance() or QApplication([])

    return rApplication
