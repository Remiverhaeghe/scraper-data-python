"""Tests de la page des paramètres"""

from gui.settings_page import SettingsPage, describe_source_state
from gui.theme import COLORS
from job.settings import load_settings
from job.sources.config import SourceDefinition
from storage.database import initialize_database


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

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vPage = SettingsPage(vDatabaseFile)
    vPage.theme_requested.connect(vRequested.append)

    vButtons = vPage.theme_buttons.buttons()

    assert vButtons[0].isChecked()

    vButtons[1].click()

    assert vRequested == ["dark"]

    vPage.set_theme_enabled(False)

    assert not vButtons[1].isEnabled()


def test_rules_are_saved_from_the_page(qt_application, tmp_path):
    """Vérifie l'enregistrement des règles de calcul saisies dans la page."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vPage = SettingsPage(vDatabaseFile)
    vPage.setting_spins["follow_up_days"].setValue(10)
    vPage.save_rules()

    assert load_settings(vDatabaseFile)["follow_up_days"] == 10
    assert vPage.rules_message.text() == "Règles enregistrées."
