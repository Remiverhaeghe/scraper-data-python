"""Tests du lancement de l'application de bureau"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser

from gui.app import THEME_SETTING, DesktopApplication
from gui.dialogs import show_legal_notice, show_license
from gui.theme import COLORS, THEMES, apply_theme
from storage.database import initialize_database


def test_theme_change_is_saved_and_applied(qt_application, tmp_path, monkeypatch):
    """Vérifie qu'un changement de thème est mémorisé et repeint la même fenêtre."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    monkeypatch.setattr("gui.app.DATABASE_FILE", vDatabaseFile)

    vSettings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    vSettings.setValue(THEME_SETTING, "light")

    try:
        vDesktop = DesktopApplication(qt_application, vSettings)
        vWindow = vDesktop.window

        vDesktop.change_theme("dark")

        assert vSettings.value(THEME_SETTING) == "dark"
        assert COLORS == THEMES["dark"]
        assert vDesktop.window is vWindow
        assert vWindow.pages.currentWidget() is vWindow.settings_page

        vWindow.close()

    finally:
        apply_theme(qt_application, "light")


def test_license_dialog_is_read_only(qt_application, monkeypatch):
    """Vérifie que la licence s'affiche en lecture seule, depuis le fichier LICENSE."""

    vShown = []

    def capture(pDialog):
        vBrowser = pDialog.findChild(QTextBrowser)
        vShown.append((vBrowser.isReadOnly(), vBrowser.toPlainText()))

    monkeypatch.setattr(QDialog, "exec", capture)

    show_license(None)

    assert vShown[0][0] is True
    assert "PolyForm Strict License 1.0.0" in vShown[0][1]
    assert "seul le texte anglais fait foi" in vShown[0][1]


def test_legal_notice_dialog_is_in_french(qt_application, monkeypatch):
    """Vérifie le bouton de fermeture traduit et la présence des mentions."""

    vShown = []

    def capture(pDialog):
        vButtons = pDialog.findChild(QDialogButtonBox)
        vShown.append(
            (
                vButtons.button(QDialogButtonBox.StandardButton.Close).text(),
                pDialog.findChild(QTextBrowser).toPlainText(),
            )
        )

    monkeypatch.setattr(QDialog, "exec", capture)

    show_legal_notice(None)

    assert vShown[0][0] == "Fermer"
    assert "Limitation de responsabilité" in vShown[0][1]
