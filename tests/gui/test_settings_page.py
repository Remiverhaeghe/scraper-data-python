"""Tests de la page des paramètres"""

from datetime import datetime

import pytest

from gui import settings_page
from gui.settings_page import SettingsPage, describe_source_state
from gui.theme import COLORS
from job.schedule import load_schedule, save_scheduled_search
from job.settings import load_settings
from job.sources.config import SourceDefinition
from storage.database import initialize_database
from storage.saved_searches import save_search


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

    vPage.set_actions_enabled(False)

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


def create_page(pDatabaseFile, pMonkeypatch, pGmailConfigured=True):
    """Crée la page avec un compte Gmail configuré ou non."""

    for vName in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"):
        if pGmailConfigured:
            pMonkeypatch.setenv(vName, "valeur")
        else:
            pMonkeypatch.delenv(vName, raising=False)

    initialize_database(pDatabaseFile)

    rPage = SettingsPage(pDatabaseFile)

    return rPage


def test_schedule_requires_a_saved_search(qt_application, tmp_path, monkeypatch):
    """Vérifie qu'une planification sans recherche enregistrée est refusée."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    vPage.schedule_check.setChecked(True)
    vPage.save_schedule()

    assert "Enregistrez d'abord une recherche" in vPage.schedule_message.text()
    assert vPage.schedule_search_label.text() == "Aucune recherche enregistrée"


def test_schedule_is_saved_from_the_page(qt_application, tmp_path, monkeypatch):
    """Vérifie l'activation, la fréquence et le résumé de la recherche planifiée."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    save_scheduled_search(vDatabaseFile, ["remotive"], {"keyword": "Java"})
    vPage.refresh_schedule()

    vPage.schedule_check.setChecked(True)
    vPage.interval_combo.setCurrentIndex(vPage.interval_combo.findData(12))
    vPage.save_schedule()

    vSchedule = load_schedule(vDatabaseFile)

    assert vSchedule["enabled"] is True
    assert vSchedule["interval_hours"] == 12
    assert vPage.schedule_message.text() == "Planification enregistrée."
    assert vPage.schedule_search_label.text() == "Java"
    assert vPage.schedule_sources_label.text() == "Remotive"


def test_schedule_uses_a_saved_search(qt_application, tmp_path, monkeypatch):
    """Vérifie le remplacement de la recherche planifiée par une recherche enregistrée."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    save_search(
        vDatabaseFile, "Python", ["remotive"], {"keyword": "Python"}, datetime.now()
    )
    vPage.refresh()

    vPage.schedule_search_combo.setCurrentIndex(1)
    vPage.save_schedule()

    assert load_schedule(vDatabaseFile)["search"] == {
        "sources": ["remotive"],
        "criteria": {"keyword": "Python"},
    }
    assert vPage.schedule_search_label.text() == "Python"


@pytest.mark.parametrize(
    "pEmail, pMessage, pSaved",
    [
        ("moi@example.com", "Adresse enregistrée.", "moi@example.com"),
        ("", "Notifications désactivées.", None),
        ("invalide", "Adresse e-mail invalide.", None),
    ],
)
def test_email_is_saved_from_the_page(
    qt_application, tmp_path, monkeypatch, pEmail, pMessage, pSaved
):
    """Vérifie l'enregistrement de l'adresse de notification."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    vPage.email_edit.setText(pEmail)
    vPage.save_email()

    assert vPage.email_message.text() == pMessage
    assert load_schedule(vDatabaseFile)["email"] == pSaved


def test_test_email_is_disabled_without_gmail(qt_application, tmp_path, monkeypatch):
    """Vérifie que l'e-mail de test n'est proposé qu'avec un compte configuré."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch, pGmailConfigured=False)

    assert not vPage.test_email_button.isEnabled()


@pytest.mark.parametrize(
    "pEmail, pError, pMessage",
    [
        ("", None, "Saisissez d'abord une adresse."),
        ("moi@example.com", None, "E-mail de test envoyé."),
        ("moi@example.com", OSError("hors ligne"), "Échec de l'envoi : hors ligne"),
    ],
)
def test_send_test_email(
    qt_application, tmp_path, monkeypatch, pEmail, pError, pMessage
):
    """Vérifie le message affiché après l'envoi de l'e-mail de test."""

    vSent = []

    def fake_send(pRecipient, pSubject, pText):
        if pError:
            raise pError

        vSent.append(pRecipient)

    monkeypatch.setattr(settings_page, "send_email", fake_send)

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vPage.email_edit.setText(pEmail)
    vPage.send_test_email()

    assert vPage.email_message.text() == pMessage
    assert vSent == (["moi@example.com"] if pEmail and not pError else [])


@pytest.mark.parametrize("pConfirmed", [True, False])
def test_reset_asks_confirmation(qt_application, tmp_path, monkeypatch, pConfirmed):
    """Vérifie que la réinitialisation n'a lieu qu'après confirmation."""

    vResets = []

    def fake_exec(pDialog):
        vButtons = {vButton.text(): vButton for vButton in pDialog.buttons()}
        pDialog.clickedButton = lambda: vButtons[
            "Réinitialiser" if pConfirmed else "Annuler"
        ]

    monkeypatch.setattr(settings_page.QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(
        settings_page,
        "reset_database",
        lambda pDatabaseFile, pNow: vResets.append(pDatabaseFile)
        or tmp_path / "backups" / "scraper-1.db",
    )

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vMessages = []
    vPage.data_reset.connect(vMessages.append)

    vPage.confirm_reset()

    assert len(vResets) == (1 if pConfirmed else 0)
    assert vMessages == (
        ["Données réinitialisées. Sauvegarde : scraper-1.db"] if pConfirmed else []
    )


def test_reset_failure_is_reported(qt_application, tmp_path, monkeypatch):
    """Vérifie le message affiché lorsque la réinitialisation échoue."""

    def refuse(pDatabaseFile, pNow):
        raise OSError("disque plein")

    monkeypatch.setattr(settings_page, "reset_database", refuse)

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vPage.reset_data()

    assert "La réinitialisation a échoué" in vPage.reset_message.text()


def test_companies_are_saved_from_the_page(qt_application, tmp_path, monkeypatch):
    """Vérifie l'enregistrement des listes d'entreprises et le message d'erreur."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    vPage.company_edits["excluded"].setPlainText("Globex\nInitech")
    vPage.company_edits["preferred"].setPlainText("Acme")
    vPage.save_companies()

    assert vPage.companies_message.text() == (
        "2 entreprise(s) exclue(s), 1 privilégiée(s)."
    )

    vPage.company_edits["preferred"].setPlainText("globex")
    vPage.save_companies()

    assert "à la fois exclue et privilégiée" in vPage.companies_message.text()


def test_scheduled_search_can_be_removed(qt_application, tmp_path, monkeypatch):
    """Vérifie le retrait de la recherche planifiée et la désactivation."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    save_scheduled_search(vDatabaseFile, ["remotive"], {"keyword": "Java"})
    vPage.refresh()

    vPage.schedule_check.setChecked(True)
    vPage.save_schedule()

    assert not vPage.remove_schedule_button.isHidden()

    monkeypatch.setattr(
        settings_page.QMessageBox,
        "question",
        lambda *pArgs: settings_page.QMessageBox.StandardButton.Yes,
    )
    vPage.remove_schedule_button.click()

    vSchedule = load_schedule(vDatabaseFile)

    assert vSchedule["search"] is None
    assert vSchedule["enabled"] is False
    assert vPage.schedule_search_label.text() == "Aucune recherche enregistrée"
    assert vPage.remove_schedule_button.isHidden()
    assert vPage.schedule_message.text() == "Recherche planifiée retirée."


def test_min_score_is_saved_with_the_email(qt_application, tmp_path, monkeypatch):
    """Vérifie l'enregistrement du score minimal des alertes avec l'adresse."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    vPage.email_edit.setText("moi@example.com")
    vPage.min_score_combo.setCurrentIndex(vPage.min_score_combo.findData(70))
    vPage.save_email()

    assert load_schedule(vDatabaseFile)["min_score"] == 70
    assert vPage.email_message.text() == "Adresse enregistrée."


def test_calendar_address_is_created_copied_and_renewed(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la création, la copie et le renouvellement confirmé de l'adresse."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    assert vPage.calendar_edit.text() == ""
    assert not vPage.copy_calendar_button.isEnabled()

    vPage.calendar_button.click()
    vFirst = vPage.calendar_edit.text()

    assert vFirst.startswith(f"{settings_page.WEB_BASE_URL}/calendar/")
    assert vPage.calendar_button.text() == "Renouveler l'adresse"

    vPage.copy_calendar_button.click()

    assert settings_page.QApplication.clipboard().text() == vFirst

    vAnswers = [
        settings_page.QMessageBox.StandardButton.No,
        settings_page.QMessageBox.StandardButton.Yes,
    ]
    monkeypatch.setattr(
        settings_page.QMessageBox, "question", lambda *pArgs: vAnswers.pop(0)
    )

    vPage.calendar_button.click()

    assert vPage.calendar_edit.text() == vFirst

    vPage.calendar_button.click()

    assert vPage.calendar_edit.text() not in ("", vFirst)


def test_archive_is_exported_then_restored(qt_application, tmp_path, monkeypatch):
    """Vérifie l'export de la sauvegarde complète, puis sa restauration confirmée."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vArchive = tmp_path / "sauvegarde.zip"
    vMessages = []
    vPage.data_reset.connect(vMessages.append)

    monkeypatch.setattr(
        settings_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vArchive), ""),
    )
    vPage.export_archive_button.click()

    assert vPage.archive_message.text().startswith("Sauvegarde exportée")

    monkeypatch.setattr(
        settings_page.QFileDialog,
        "getOpenFileName",
        lambda *pArgs: (str(vArchive), ""),
    )
    monkeypatch.setattr(
        settings_page.QMessageBox,
        "warning",
        lambda *pArgs: settings_page.QMessageBox.StandardButton.Yes,
    )
    vPage.restore_archive_button.click()

    assert vMessages[0].startswith("Sauvegarde restaurée.")


def test_archive_restore_reports_refused_file(qt_application, tmp_path, monkeypatch):
    """Vérifie le message d'une archive refusée et d'un export impossible."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vText = tmp_path / "faux.zip"
    vText.write_text("texte", encoding="utf-8")

    vPage.restore_archive(str(vText))

    assert "pas un fichier .zip" in vPage.archive_message.text()

    vPage.export_archive(str(tmp_path / "absent" / "sauvegarde.zip"))

    assert vPage.archive_message.text() == "L'export a échoué. Voir les journaux."


def test_calendar_and_archive_errors_are_reported(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie les messages d'échec de l'adresse d'agenda et de la restauration."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    def fail(*pArgs):
        raise OSError("disque plein")

    monkeypatch.setattr(settings_page, "renew_calendar_token", fail)
    monkeypatch.setattr(settings_page, "restore_archive", fail)
    monkeypatch.setattr(
        settings_page.QFileDialog, "getOpenFileName", lambda *pArgs: ("", "")
    )

    vPage.calendar_button.click()
    vPage.restore_archive_button.click()

    assert vPage.calendar_message.text() == "L'adresse n'a pas pu être créée."
    assert vPage.archive_message.text() == ""

    vPage.restore_archive(str(tmp_path / "sauvegarde.zip"))

    assert (
        vPage.archive_message.text() == "La restauration a échoué. Voir les journaux."
    )


def test_mobile_token_is_created_copied_and_renewed(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la carte de l'application mobile : création, copie et renouvellement."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    assert vPage.mobile_edit.text() == ""
    assert not vPage.copy_mobile_button.isEnabled()

    vPage.mobile_button.click()
    vFirst = vPage.mobile_edit.text()

    assert len(vFirst) >= 40
    assert vPage.mobile_button.text() == "Renouveler le jeton"

    vPage.copy_mobile_button.click()

    assert settings_page.QApplication.clipboard().text() == vFirst

    vAnswers = [
        settings_page.QMessageBox.StandardButton.No,
        settings_page.QMessageBox.StandardButton.Yes,
    ]
    monkeypatch.setattr(
        settings_page.QMessageBox, "question", lambda *pArgs: vAnswers.pop(0)
    )

    vPage.mobile_button.click()

    assert vPage.mobile_edit.text() == vFirst

    vPage.mobile_button.click()

    assert vPage.mobile_edit.text() not in ("", vFirst)

    monkeypatch.setattr(settings_page, "renew_mobile_token", lambda *pArgs: 1 / 0)
    vPage.mobile_button.setText("Créer le jeton")
    vPage.mobile_edit.clear()
    vPage.mobile_button.click()

    assert vPage.mobile_message.text() == "Le jeton n'a pas pu être créé."


def test_messages_are_colored_and_cards_reflow(qt_application, tmp_path, monkeypatch):
    """Vérifie les messages colorés et le passage sur une colonne en fenêtre étroite."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    vPage.company_edits["excluded"].setPlainText("acme")
    vPage.company_edits["preferred"].setPlainText("acme")
    vPage.save_companies()

    assert COLORS["warning"] in vPage.companies_message.styleSheet()

    vPage.company_edits["preferred"].setPlainText("globex")
    vPage.save_companies()

    assert COLORS["success"] in vPage.companies_message.styleSheet()
    assert vPage.company_edits["excluded"].objectName() == "excludedCompanies"

    vPage.resize(800, 600)
    vPage.arrange_cards(vPage.width() < settings_page.SINGLE_COLUMN_WIDTH)

    assert vPage.columns[1].count() == 1
    assert vPage.columns[0].count() == 11

    vPage.arrange_cards(False)

    assert vPage.columns[1].count() == 6
