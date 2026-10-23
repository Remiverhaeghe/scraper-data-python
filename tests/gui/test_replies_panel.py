"""Tests du panneau des réponses de recruteurs"""

from datetime import datetime

import gui.replies_panel as replies_panel
from gui.replies_panel import RepliesPanel

REPLY = {
    "message_id": "<1>",
    "subject": "Votre candidature",
    "date": datetime(2026, 10, 22),
    "source": "adzuna",
    "source_id": "1",
    "title": "Développeur Java",
    "company": "Kiabi",
    "current_status": "APPLIED",
    "status": "REJECTED",
}


def test_reply_is_shown_then_applied(qt_application, tmp_path, monkeypatch):
    """Vérifie la ligne d'une réponse, puis le statut appliqué et le signal émis."""

    vApplied = []
    monkeypatch.setattr(
        replies_panel,
        "apply_reply",
        lambda pDatabaseFile, pReply, pNow: vApplied.append(pReply["status"]),
    )
    vPanel = RepliesPanel(tmp_path / "scraper.db")
    vChanged = []
    vPanel.changed.connect(lambda: vChanged.append(True))

    vPanel.show_replies([REPLY], None, "success")

    assert vPanel.rows_layout.count() == 1
    assert "1 réponse(s)" in vPanel.message_label.text()

    vRow = vPanel.rows_layout.itemAt(0).widget()
    vPanel.handle(vRow, REPLY, True)

    assert vApplied == ["REJECTED"]
    assert vChanged == [True]
    assert "Refusé" in vPanel.message_label.text()


def test_missing_gmail_settings_are_explained(qt_application, tmp_path, monkeypatch):
    """Vérifie le message sans adresse Gmail, lu dans le même fil pour le test."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    vPanel = RepliesPanel(tmp_path / "scraper.db")

    vPanel.run_read()

    assert "À renseigner dans .env" in vPanel.message_label.text()
    assert vPanel.read_button.isEnabled()
