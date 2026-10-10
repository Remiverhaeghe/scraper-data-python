"""Tests de la page des paramètres"""

from gui.settings_page import SettingsPage, describe_source_state
from gui.theme import COLORS
from job.sources.config import SourceDefinition


def build_definition(pAvailable=True, pSettings=()):
    """Construit une source de test."""

    rDefinition = SourceDefinition(
        name="test",
        label="Test",
        load_parameters=None,
        scrape=None,
        available=pAvailable,
        settings=pSettings,
    )

    return rDefinition


def test_describe_source_state(monkeypatch):
    """Vérifie l'état affiché pour une source prête, à configurer ou indisponible."""

    monkeypatch.delenv("TEST_MISSING_KEY", raising=False)

    assert describe_source_state(build_definition())[2] == "Prête"
    assert describe_source_state(build_definition(pSettings=("TEST_MISSING_KEY",))) == (
        "circle-alert",
        COLORS["warning"],
        "À renseigner dans .env : TEST_MISSING_KEY",
    )
    assert describe_source_state(build_definition(pAvailable=False))[2] == (
        "Indisponible pour le moment"
    )


def test_theme_buttons_emit_choice(qt_application, tmp_path):
    """Vérifie que les boutons de thème demandent le thème choisi."""

    vRequested = []

    vPage = SettingsPage(tmp_path / "scraper.db")
    vPage.theme_requested.connect(vRequested.append)

    vButtons = vPage.theme_buttons.buttons()

    assert vButtons[0].isChecked()

    vButtons[1].click()

    assert vRequested == ["dark"]

    vPage.set_theme_enabled(False)

    assert not vButtons[1].isEnabled()
