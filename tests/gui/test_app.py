"""Tests du lancement de l'application de bureau"""

from PySide6.QtCore import QSettings

from gui.app import THEME_SETTING, DesktopApplication
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
