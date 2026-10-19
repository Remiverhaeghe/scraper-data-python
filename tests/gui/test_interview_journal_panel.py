"""Tests du panneau du journal d'entretien"""

from datetime import datetime

import pandas as pd

import gui.interview_journal_panel as journal_panel
from gui.interview_journal_panel import InterviewJournalPanel
from storage.database import initialize_database
from storage.job_offers import save_offers


def test_journal_entry_is_added_from_the_dialog(qt_application, tmp_path, monkeypatch):
    """Vérifie la saisie par la fenêtre, le résumé et l'affichage des entrées."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "Dev"}]),
        datetime.now(),
    )

    vPanel = InterviewJournalPanel(vDatabaseFile)
    vPanel.set_offer({"source": "remotive", "source_id": "1"})

    assert vPanel.summary_label.text() == "Aucune entrée pour cette offre."
    assert not vPanel.show_button.isEnabled()

    def fake_exec(pDialog):
        pDialog.questions_edit.setPlainText("Parlez-moi d'un échec")
        rCode = journal_panel.QDialog.DialogCode.Accepted

        return rCode

    vShown = []
    monkeypatch.setattr(journal_panel.InterviewDialog, "exec", fake_exec)
    monkeypatch.setattr(
        journal_panel,
        "show_text_dialog",
        lambda pParent, pTitle, pHtml: vShown.append(pHtml),
    )

    vPanel.add_note()
    vPanel.show_notes()

    assert vPanel.summary_label.text().startswith("1 entrée(s)")
    assert "Parlez-moi d&#x27;un échec" in vShown[0]

    vPanel.save_note("", "")

    assert "au moins une question" in vPanel.summary_label.text()
