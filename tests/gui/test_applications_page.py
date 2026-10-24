"""Tests de la page des candidatures"""

from datetime import datetime

import pandas as pd
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton

import gui.applications_page as applications_page
import gui.follow_ups_panel as follow_ups_panel
from gui.applications_page import ApplicationsPage
from gui.spontaneous_dialog import SpontaneousDialog
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 11, 10, 0)


def create_page(pDatabaseFile):
    """Crée la page avec une candidature envoyée et une offre à postuler."""

    initialize_database(pDatabaseFile)
    save_offers(
        pDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Java",
                    "company": "Acme",
                },
                {
                    "source": "remotive",
                    "source_id": "2",
                    "title": "Data",
                    "company": "Acme",
                },
            ]
        ),
        NOW,
    )
    save_application(pDatabaseFile, "remotive", "1", "APPLIED", pNow=NOW)
    save_application(pDatabaseFile, "remotive", "2", "INTERESTED", pNow=NOW)

    rPage = ApplicationsPage(pDatabaseFile)
    rPage.refresh()

    return rPage


def get_column_titles(pPage, pIndex):
    """Retourne les titres des cartes d'une colonne."""

    vCard, _ = pPage.board_columns[pIndex]

    rTitles = [
        vButton.text()
        for vButton in vCard.findChildren(QPushButton)
        if vButton.objectName() == "linkButton"
    ]

    return rTitles


def test_page_shows_board_and_statistics(qt_application, tmp_path):
    """Vérifie les colonnes, leurs compteurs et les chiffres clés."""

    vPage = create_page(tmp_path / "scraper.db")

    assert get_column_titles(vPage, 0) == ["Data"]
    assert get_column_titles(vPage, 1) == ["Java"]
    assert vPage.board_columns[1][0].findChild(QLabel, "cardTitle").text() == (
        "Postulé (1)"
    )
    assert vPage.statistic_cards["sent"].value_label.text() == "1"
    assert vPage.statistic_cards["rate"].value_label.text() == "0 %"
    assert vPage.statistic_tables[0][1].item(0, 0).text() == "Remotive"


def test_status_change_moves_card(qt_application, tmp_path):
    """Vérifie qu'un nouveau statut déplace la carte et met à jour la base."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    vChanged = []
    vPage.application_changed.connect(lambda: vChanged.append(True))

    vCombo = vPage.board_columns[1][0].findChild(QComboBox)
    vCombo.setCurrentIndex(vCombo.findData("INTERVIEW"))

    assert get_application(vDatabaseFile, "remotive", "1")["status"] == "INTERVIEW"
    assert vChanged == [True]
    assert vPage.statistic_cards["rate"].value_label.text() == "100 %"


def test_card_title_opens_offer(qt_application, tmp_path):
    """Vérifie la demande d'ouverture de l'offre depuis sa carte."""

    vPage = create_page(tmp_path / "scraper.db")
    vRequested = []
    vPage.offer_requested.connect(lambda *pArgs: vRequested.append(pArgs))

    vCard, _ = vPage.board_columns[1]
    next(
        vButton
        for vButton in vCard.findChildren(QPushButton)
        if vButton.objectName() == "linkButton"
    ).click()

    assert vRequested == [([("remotive", "1")], "Candidature « Java »")]


def test_errors_are_reported(qt_application, tmp_path, monkeypatch):
    """Vérifie les messages affichés quand la lecture ou l'écriture échoue."""

    vPage = create_page(tmp_path / "scraper.db")

    monkeypatch.setattr(
        applications_page,
        "update_application_status",
        lambda *pArgs: (_ for _ in ()).throw(OSError("disque")),
    )
    vPage.change_status({"source": "remotive", "source_id": "1"}, "INTERVIEW")

    assert vPage.message_label.text() == "Le statut n'a pas pu être modifié."

    monkeypatch.setattr(
        applications_page,
        "build_board",
        lambda *pArgs: (_ for _ in ()).throw(OSError("disque")),
    )
    vPage.refresh()

    assert vPage.message_label.text() == "Les candidatures n'ont pas pu être chargées."


def test_calendar_export(qt_application, tmp_path, monkeypatch):
    """Vérifie l'écriture du fichier agenda et le message de fin."""

    vPage = create_page(tmp_path / "scraper.db")
    vPath = tmp_path / "agenda.ics"
    vShown = []

    monkeypatch.setattr(
        applications_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vPath), ""),
    )
    monkeypatch.setattr(
        applications_page.QMessageBox,
        "information",
        lambda pParent, pTitle, pText: vShown.append(pTitle),
    )

    vPage.choose_calendar_file()

    assert vPath.read_bytes().startswith(b"BEGIN:VCALENDAR\r\n")
    assert vShown == ["Export terminé"]


def test_week_follow_ups_are_copied_and_marked(qt_application, tmp_path):
    """Vérifie le brouillon copié et la relance notée depuis la page."""

    vPage = create_page(tmp_path / "scraper.db")
    vPanel = vPage.follow_ups_panel

    assert [vFollowUp["title"] for vFollowUp in vPanel.follow_ups] == ["Java"]

    vPanel.copy_all()

    assert (
        qt_application.clipboard()
        .text()
        .startswith("Objet : ma candidature au poste de Java")
    )

    vPanel.mark_done(vPanel.follow_ups[0])

    assert (
        get_application(tmp_path / "scraper.db", "remotive", "1")["follow_up_count"]
        == 1
    )
    assert not vPanel.follow_ups[0]["follow_up_due"]


def test_follow_up_is_sent_after_review(qt_application, tmp_path, monkeypatch):
    """Vérifie l'envoi depuis la fenêtre de relecture, puis les refus expliqués."""

    vPage = create_page(tmp_path / "scraper.db")
    vPanel = vPage.follow_ups_panel
    vFollowUp = vPanel.follow_ups[0]
    vSent = []

    vDialog = follow_ups_panel.FollowUpDialog(vPanel, vFollowUp)

    assert vDialog.draft_edit.toPlainText().startswith("Objet : ma candidature")

    monkeypatch.setattr(
        follow_ups_panel.FollowUpDialog,
        "exec",
        lambda pDialog: (
            pDialog.recipient_edit.setText("rh@acme.fr"),
            follow_ups_panel.QDialog.DialogCode.Accepted,
        )[1],
    )
    monkeypatch.setattr(
        "job.application_tracking.send_email",
        lambda pRecipient, pSubject, pText: vSent.append(pRecipient),
    )
    vPanel.send(vFollowUp)

    assert vSent == ["rh@acme.fr"]
    assert vPanel.message_label.text() == "Relance envoyée et notée."
    assert get_application(tmp_path / "scraper.db", "remotive", "1")[
        "contact_email"
    ] == ("rh@acme.fr")

    def fail(*_pArgs):
        raise OSError("hors ligne")

    monkeypatch.setattr("job.application_tracking.send_email", fail)
    vPanel.send(vFollowUp)

    assert "L'envoi a échoué" in vPanel.message_label.text()

    monkeypatch.setattr(
        follow_ups_panel.FollowUpDialog,
        "exec",
        lambda pDialog: (
            pDialog.recipient_edit.setText("pas-une-adresse"),
            follow_ups_panel.QDialog.DialogCode.Accepted,
        )[1],
    )
    vPanel.send(vFollowUp)

    assert vPanel.message_label.text() == "Adresse e-mail du recruteur invalide."

    monkeypatch.setattr(
        follow_ups_panel.FollowUpDialog,
        "exec",
        lambda pDialog: follow_ups_panel.QDialog.DialogCode.Rejected,
    )
    vPanel.send(vFollowUp)

    assert vPanel.message_label.text() == "Adresse e-mail du recruteur invalide."


def test_funnel_is_shown(qt_application, tmp_path):
    """Vérifie une barre par étape de l'entonnoir."""

    vPage = create_page(tmp_path / "scraper.db")
    vLayout = vPage.funnel_panel.rows_layout

    assert vLayout.rowCount() == 4
    assert vLayout.itemAtPosition(0, 1).widget().format() == "1  ·  100 %"


def test_search_journal_export(qt_application, tmp_path, monkeypatch):
    """Vérifie l'écriture du journal de recherche et le message de fin."""

    vPage = create_page(tmp_path / "scraper.db")
    vPath = tmp_path / "journal.csv"
    monkeypatch.setattr(
        applications_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vPath), ""),
    )

    vPage.export_journal()

    assert vPath.read_bytes().startswith(b"\xef\xbb\xbfDate;")
    assert "Journal enregistré" in vPage.message_label.text()


def test_spontaneous_dialog_saves_or_explains(qt_application, tmp_path):
    """Vérifie l'enregistrement depuis la fenêtre, et le message sans entreprise."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vDialog = SpontaneousDialog(None, vDatabaseFile)

    vDialog.save()

    assert "entreprise manquante" in vDialog.message_label.text()

    vDialog.company_edit.setText("OVHcloud")
    vDialog.save()

    assert vDialog.result() == vDialog.DialogCode.Accepted
