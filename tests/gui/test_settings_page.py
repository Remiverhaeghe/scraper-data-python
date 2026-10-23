"""Tests de la page des paramètres"""

import shutil
from datetime import datetime

import pytest
from PySide6.QtWidgets import QLabel

from gui import data_panel, settings_page, token_access_panel
from gui.settings_page import SettingsPage, describe_source_state
from gui.theme import COLORS
from job.schedule import load_schedule, save_scheduled_search
from job.settings import load_settings
from job.sources.config import SourceDefinition
from storage.database import initialize_database
from storage.backup import backup_database, copy_to_nas
from storage.saved_searches import get_saved_searches, save_search


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

    # Sans choix mémorisé, « Auto » est coché : le thème suit Windows.
    assert [vButton.text() for vButton in vButtons] == ["Auto", "Clair", "Sombre"]
    assert vButtons[0].isChecked()

    vButtons[2].click()

    assert vRequested == ["dark"]

    vPage.set_actions_enabled(False)

    assert not vButtons[2].isEnabled()


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


def test_extra_searches_are_saved_from_the_page(qt_application, tmp_path, monkeypatch):
    """Vérifie l'ajout d'une recherche enregistrée à la planification."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    save_search(
        vDatabaseFile, "Python", ["remotive"], {"keyword": "Python"}, datetime.now()
    )
    vPage.refresh()

    vPage.schedule_search_combo.setCurrentIndex(1)
    vPage.extra_search_checks["Python"].setChecked(True)
    vPage.save_schedule()

    assert load_schedule(vDatabaseFile)["extra_searches"] == ["Python"]
    assert vPage.extra_search_checks["Python"].isChecked()
    assert "Python" in vPage.schedule_extra_label.text()


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
        data_panel,
        "reset_database",
        lambda pDatabaseFile, pNow: vResets.append(pDatabaseFile)
        or tmp_path / "backups" / "scraper-1.db",
    )

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vMessages = []
    vPage.data_reset.connect(vMessages.append)

    vPage.data_panel.confirm_reset()

    assert len(vResets) == (1 if pConfirmed else 0)
    assert vMessages == (
        ["Données réinitialisées. Sauvegarde : scraper-1.db"] if pConfirmed else []
    )


def test_reset_failure_is_reported(qt_application, tmp_path, monkeypatch):
    """Vérifie le message affiché lorsque la réinitialisation échoue."""

    def refuse(pDatabaseFile, pNow):
        raise OSError("disque plein")

    monkeypatch.setattr(data_panel, "reset_database", refuse)

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vPage.data_panel.reset_data()

    assert "La réinitialisation a échoué" in vPage.data_panel.reset_message.text()


def test_companies_are_saved_from_the_page(qt_application, tmp_path, monkeypatch):
    """Vérifie l'enregistrement des listes d'entreprises et le message d'erreur."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)

    vPage.company_edits["excluded"].setPlainText("Globex\nInitech")
    vPage.company_edits["preferred"].setPlainText("Acme")
    vPage.company_edits["agencies"].setPlainText("Proman\nAgence Locale SAS, proman")
    vPage.save_companies()

    assert vPage.companies_message.text() == (
        "2 entreprise(s) exclue(s), 1 privilégiée(s), 2 agence(s) d'intérim."
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

    assert vPage.calendar_panel.edit.text() == ""
    assert not vPage.calendar_panel.copy_button.isEnabled()

    vPage.calendar_panel.button.click()
    vFirst = vPage.calendar_panel.edit.text()

    assert vFirst.startswith(f"{settings_page.WEB_BASE_URL}/calendar/")
    assert vPage.calendar_panel.button.text() == "Renouveler l'adresse"

    vPage.calendar_panel.copy_button.click()

    assert settings_page.QApplication.clipboard().text() == vFirst

    vAnswers = [
        settings_page.QMessageBox.StandardButton.No,
        settings_page.QMessageBox.StandardButton.Yes,
    ]
    monkeypatch.setattr(
        settings_page.QMessageBox, "question", lambda *pArgs: vAnswers.pop(0)
    )

    vPage.calendar_panel.button.click()

    assert vPage.calendar_panel.edit.text() == vFirst

    vPage.calendar_panel.button.click()

    assert vPage.calendar_panel.edit.text() not in ("", vFirst)


def test_archive_is_exported_then_restored(qt_application, tmp_path, monkeypatch):
    """Vérifie l'export de la sauvegarde complète, puis sa restauration confirmée."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vArchive = tmp_path / "sauvegarde.zip"
    vMessages = []
    vPage.data_reset.connect(vMessages.append)

    monkeypatch.setattr(
        data_panel.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vArchive), ""),
    )
    vPage.data_panel.export_archive_button.click()

    assert vPage.data_panel.archive_message.text().startswith("Sauvegarde exportée")

    monkeypatch.setattr(
        data_panel.QFileDialog,
        "getOpenFileName",
        lambda *pArgs: (str(vArchive), ""),
    )
    monkeypatch.setattr(
        settings_page.QMessageBox,
        "warning",
        lambda *pArgs: settings_page.QMessageBox.StandardButton.Yes,
    )
    vPage.data_panel.restore_archive_button.click()

    assert vMessages[0].startswith("Sauvegarde restaurée.")


def test_archive_restore_reports_refused_file(qt_application, tmp_path, monkeypatch):
    """Vérifie le message d'une archive refusée et d'un export impossible."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)
    vText = tmp_path / "faux.zip"
    vText.write_text("texte", encoding="utf-8")

    vPage.data_panel.restore_archive(str(vText))

    assert "pas un fichier .zip" in vPage.data_panel.archive_message.text()

    vPage.data_panel.export_archive(str(tmp_path / "absent" / "sauvegarde.zip"))

    assert (
        vPage.data_panel.archive_message.text()
        == "L'export a échoué. Voir les journaux."
    )


def test_calendar_and_archive_errors_are_reported(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie les messages d'échec de l'adresse d'agenda et de la restauration."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    def fail(*pArgs):
        raise OSError("disque plein")

    monkeypatch.setattr(settings_page, "renew_calendar_token", fail)
    monkeypatch.setattr(data_panel, "restore_archive", fail)
    monkeypatch.setattr(
        data_panel.QFileDialog, "getOpenFileName", lambda *pArgs: ("", "")
    )

    vPage.calendar_panel.button.click()
    vPage.data_panel.restore_archive_button.click()

    assert (
        vPage.calendar_panel.message_label.text() == "L'adresse n'a pas pu être créée."
    )
    assert vPage.data_panel.archive_message.text() == ""

    vPage.data_panel.restore_archive(str(tmp_path / "sauvegarde.zip"))

    assert (
        vPage.data_panel.archive_message.text()
        == "La restauration a échoué. Voir les journaux."
    )


def test_mobile_token_is_created_copied_and_renewed(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la carte de l'application mobile : création, copie et renouvellement."""

    vPage = create_page(tmp_path / "scraper.db", monkeypatch)

    assert vPage.mobile_panel.edit.text() == ""
    assert not vPage.mobile_panel.copy_button.isEnabled()

    vPage.mobile_panel.button.click()
    vFirst = vPage.mobile_panel.edit.text()

    assert len(vFirst) >= 40
    assert vPage.mobile_panel.button.text() == "Renouveler le jeton"

    vPage.mobile_panel.copy_button.click()

    assert settings_page.QApplication.clipboard().text() == vFirst

    # Le QR code s'affiche à la demande, dans une fenêtre fermée aussitôt ici.
    vShown = []
    monkeypatch.setattr(
        token_access_panel.QDialog,
        "exec",
        lambda pDialog: vShown.append(pDialog.findChild(QLabel).pixmap().width()),
    )

    assert vPage.mobile_panel.qr_button.isEnabled()

    vPage.mobile_panel.qr_button.click()

    assert vShown and vShown[0] > 100

    vAnswers = [
        settings_page.QMessageBox.StandardButton.No,
        settings_page.QMessageBox.StandardButton.Yes,
    ]
    monkeypatch.setattr(
        settings_page.QMessageBox, "question", lambda *pArgs: vAnswers.pop(0)
    )

    vPage.mobile_panel.button.click()

    assert vPage.mobile_panel.edit.text() == vFirst

    vPage.mobile_panel.button.click()

    assert vPage.mobile_panel.edit.text() not in ("", vFirst)

    monkeypatch.setattr(settings_page, "renew_mobile_token", lambda *pArgs: 1 / 0)
    vPage.mobile_panel.button.setText("Créer le jeton")
    vPage.mobile_panel.edit.clear()
    vPage.mobile_panel.button.click()

    assert vPage.mobile_panel.message_label.text() == "Le jeton n'a pas pu être créé."


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
    assert vPage.columns[0].count() == 12

    vPage.arrange_cards(False)

    assert vPage.columns[1].count() == 7


def test_database_backup_is_listed_and_restored(qt_application, tmp_path, monkeypatch):
    """Vérifie la liste des sauvegardes et la restauration confirmée de l'une d'elles."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile, monkeypatch)
    vPanel = vPage.data_panel

    assert not vPanel.restore_backup_button.isEnabled()

    save_search(vDatabaseFile, "Avant", ["remotive"], {}, datetime.now())
    backup_database(vDatabaseFile, datetime(2026, 10, 18, 9, 0), "auto")
    save_search(vDatabaseFile, "Après", ["remotive"], {}, datetime.now())
    vPanel.refresh()

    assert vPanel.backups_combo.currentText().startswith(
        "18/10/2026 09:00 · automatique"
    )

    vMessages = []
    vPage.data_reset.connect(vMessages.append)
    monkeypatch.setattr(
        data_panel.QMessageBox,
        "warning",
        lambda *pArgs: data_panel.QMessageBox.StandardButton.Yes,
    )
    vPanel.restore_backup_button.click()

    assert vMessages[0].startswith("Sauvegarde restaurée.")
    assert [vSearch["name"] for vSearch in get_saved_searches(vDatabaseFile)] == [
        "Avant"
    ]

    vPanel.restore_backup("absente.db")

    assert vPanel.backup_message.text() == "Sauvegarde introuvable."


def test_database_is_restored_from_the_nas(qt_application, tmp_path, monkeypatch):
    """Vérifie la restauration d'une copie du NAS après la perte des sauvegardes."""

    vDatabaseFile = tmp_path / "pc" / "scraper.db"
    vNas = tmp_path / "nas"
    initialize_database(vDatabaseFile)
    save_search(vDatabaseFile, "Avant", ["remotive"], {}, datetime.now())
    backup_database(vDatabaseFile, datetime(2026, 10, 18, 2, 0), "auto")
    copy_to_nas(vDatabaseFile, vNas)
    shutil.rmtree(vDatabaseFile.parent / "backups")
    save_search(vDatabaseFile, "Après", ["remotive"], {}, datetime.now())

    vPanel = data_panel.DataPanel(vDatabaseFile, vNas)
    vMessages = []
    vPanel.data_reset.connect(vMessages.append)
    vOffered = []

    def choose(*pArgs):
        vOffered.extend(pArgs[3])
        return pArgs[3][0], True

    monkeypatch.setattr(data_panel.QInputDialog, "getItem", choose)
    monkeypatch.setattr(
        data_panel.QMessageBox,
        "warning",
        lambda *pArgs: data_panel.QMessageBox.StandardButton.Yes,
    )

    assert not vPanel.nas_button.isHidden()

    vPanel.nas_button.click()

    assert vOffered[0].startswith("18/10/2026 02:00 · automatique")
    assert vMessages[0].startswith("Sauvegarde restaurée.")
    assert [vSearch["name"] for vSearch in get_saved_searches(vDatabaseFile)] == [
        "Avant"
    ]


def test_nas_restore_reports_missing_nas_or_copies(qt_application, tmp_path):
    """Vérifie les messages d'un NAS injoignable puis d'un NAS sans copie."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vPanel = data_panel.DataPanel(vDatabaseFile, tmp_path / "absent")
    vPanel.choose_nas_copy()

    assert "injoignable" in vPanel.backup_message.text()

    (tmp_path / "vide").mkdir()
    vPanel = data_panel.DataPanel(vDatabaseFile, tmp_path / "vide")
    vPanel.choose_nas_copy()

    assert vPanel.backup_message.text() == "Aucune copie sur le NAS."
    assert data_panel.DataPanel(vDatabaseFile, None).nas_button.isHidden()
