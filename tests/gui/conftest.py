"""Configuration commune des tests de l'interface graphique"""

import gc
import os

import pytest

# Les tests tournent sans écran, en local comme sur la CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)


@pytest.fixture(scope="session")
def qt_application():
    """Fournit l'unique QApplication autorisée par Qt."""

    rApplication = QApplication.instance() or QApplication([])

    yield rApplication

    # Sous Linux, laisser Python détruire Qt à la sortie de l'interpréteur fait
    # planter le processus (code 139) après des tests pourtant réussis : les
    # fenêtres sont détruites ici, puis l'application est arrêtée explicitement.
    for vWidget in rApplication.topLevelWidgets():
        vWidget.close()
        vWidget.deleteLater()

    rApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    rApplication.shutdown()


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """Écrit les préférences de l'interface (QSettings) dans un dossier temporaire."""

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path)
    )


@pytest.fixture(autouse=True)
def no_cache_warm_up(monkeypatch):
    """Coupe le calcul anticipé et la sauvegarde du démarrage, faits sur une base supprimée."""

    monkeypatch.setattr(
        "gui.main_window.prepare_quiz_caches", lambda pDatabaseFile: None
    )
    monkeypatch.setattr(
        "gui.main_window.run_due_backup", lambda pDatabaseFile, pNow: None
    )
    monkeypatch.setattr(
        "gui.main_window.refresh_education_levels_safely", lambda pDatabaseFile: None
    )
    monkeypatch.setattr("gui.main_window.warm_up_scores", lambda pDatabaseFile: None)


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


# Fenêtres qui attendent une réponse : sans simulation, un test resterait bloqué
# jusqu'à ce qu'on tue pytest. Chacune répond « annuler » et le test échoue.
MODAL_METHODS = {
    QDialog: {"exec": 0},
    QMessageBox: {
        "exec": 0,
        "question": QMessageBox.StandardButton.NoButton,
        "warning": QMessageBox.StandardButton.NoButton,
        "information": QMessageBox.StandardButton.NoButton,
        "critical": QMessageBox.StandardButton.NoButton,
    },
    QInputDialog: {
        "exec": 0,
        "getText": ("", False),
        "getMultiLineText": ("", False),
        "getItem": ("", False),
        "getInt": (0, False),
        "getDouble": (0.0, False),
    },
    QFileDialog: {
        "exec": 0,
        "getOpenFileName": ("", ""),
        "getOpenFileNames": ([], ""),
        "getSaveFileName": ("", ""),
        "getExistingDirectory": "",
    },
}


@pytest.fixture(autouse=True)
def refuse_modal_windows(monkeypatch):
    """Fait échouer un test qui ouvre une fenêtre modale sans la simuler.

    L'échec est signalé après le test : levée dans un slot Qt, une exception
    serait seulement affichée et le test passerait quand même.
    """

    vOpened = []

    for vClass, vMethods in MODAL_METHODS.items():
        for vName, vAnswer in vMethods.items():

            def refuse(*_pArgs, pName=f"{vClass.__name__}.{vName}", pAnswer=vAnswer):
                vOpened.append(pName)

                return pAnswer

            monkeypatch.setattr(vClass, vName, refuse)

    yield

    if vOpened:
        pytest.fail(
            "Fenêtre modale non simulée : "
            + ", ".join(dict.fromkeys(vOpened))
            + ". Simulez-la avec monkeypatch dans le test."
        )
