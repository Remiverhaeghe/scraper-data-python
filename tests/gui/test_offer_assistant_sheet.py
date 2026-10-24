"""Tests de l'export PDF de la fiche de préparation"""

from datetime import datetime

import pandas as pd
import pytest

import gui.offer_assistant as offer_assistant
from gui.offer_assistant import OfferAssistantPanel, write_pdf
from storage.database import initialize_database
from storage.job_offers import save_offers


def test_write_pdf_creates_a_pdf_file(qt_application, tmp_path):
    """Vérifie qu'un PDF non vide est écrit, et l'erreur sur un dossier absent."""

    vPath = tmp_path / "fiche.pdf"

    write_pdf(vPath, "<h1>Fiche</h1><ul><li>Pourquoi nous ?</li></ul>")

    assert vPath.read_bytes().startswith(b"%PDF")

    with pytest.raises(OSError):
        write_pdf(tmp_path / "absent" / "fiche.pdf", "<p>x</p>")


def test_sheet_is_saved_then_opened(qt_application, tmp_path, monkeypatch):
    """Vérifie la fiche enregistrée et ouverte, puis l'échec d'écriture signalé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vOffer = {"source": "lever", "source_id": "1", "title": "Dev", "company": "Acme"}
    save_offers(vDatabaseFile, pd.DataFrame([vOffer]), datetime(2026, 10, 24))
    vPanel = OfferAssistantPanel(vDatabaseFile)
    vPanel.offer = vOffer
    vTarget = tmp_path / "fiche.pdf"
    vOpened = []
    vWarnings = []

    monkeypatch.setattr(
        offer_assistant.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vTarget), ""),
    )
    monkeypatch.setattr(
        offer_assistant.QDesktopServices, "openUrl", lambda pUrl: vOpened.append(pUrl)
    )
    monkeypatch.setattr(
        offer_assistant.QMessageBox,
        "warning",
        lambda *pArgs: vWarnings.append(pArgs[2]),
    )

    vPanel.sheet_button.click()

    assert vTarget.read_bytes().startswith(b"%PDF")
    assert vOpened[0].toLocalFile().endswith("fiche.pdf")

    vTarget = tmp_path / "absent" / "fiche.pdf"
    vPanel.export_sheet()

    assert vWarnings[0].startswith("Enregistrement impossible")
