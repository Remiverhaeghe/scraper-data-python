"""Tests de la fenêtre du jeu de négociation salariale"""

from PySide6.QtWidgets import QPushButton

import job.salary_negotiation as negotiation
from gui.negotiation_dialog import NegotiationDialog
from storage.database import initialize_database

BUDGET = {
    "median": 36000,
    "low": 32000,
    "high": 40000,
    "target": 38000,
    "ceiling": 42000,
}


def click(pDialog, pStart):
    """Clique la réponse dont le texte commence par pStart."""

    next(
        vButton
        for vButton in pDialog.findChildren(QPushButton)
        if vButton.isVisibleTo(pDialog) and vButton.text().startswith(pStart)
    ).click()


def test_negotiation_is_played_until_the_score(qt_application, tmp_path, monkeypatch):
    """Vérifie une partie jouée au clic, puis la partie sans marché expliquée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.setattr(negotiation, "build_budget", lambda *pArgs: dict(BUDGET))
    vDialog = NegotiationDialog(None, vDatabaseFile, {"title": "Technicien"})

    assert "prétentions salariales" in vDialog.transcript.toPlainText()

    click(vDialog, "Entre ")
    click(vDialog, "Pour ce poste")
    click(vDialog, "J'accepte")

    assert vDialog.message_label.text().startswith("Accord à")
    assert "score 88 / 100" in vDialog.message_label.text()

    def no_market(*_pArgs):
        raise ValueError("Pas encore assez d'offres avec un salaire.")

    monkeypatch.setattr(negotiation, "build_budget", no_market)
    click(vDialog, "Rejouer")

    assert vDialog.message_label.text() == "Pas encore assez d'offres avec un salaire."
