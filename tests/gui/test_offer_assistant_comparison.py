"""Tests de la comparaison des offres depuis l'assistant du bureau"""

from datetime import datetime

import pandas as pd

import gui.offer_assistant as offer_assistant
from gui.offer_assistant import OfferAssistantPanel
from storage.database import initialize_database
from storage.job_offers import save_offers


def test_offer_is_added_to_comparison_and_shown(qt_application, tmp_path, monkeypatch):
    """Vérifie l'ajout, le libellé des boutons et le tableau affiché."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "Dev <Go>"}]),
        datetime.now(),
    )

    vPanel = OfferAssistantPanel(vDatabaseFile)
    vPanel.set_offer({"source": "remotive", "source_id": "1", "title": "Dev <Go>"})

    assert not vPanel.show_comparison_button.isEnabled()

    vPanel.compare_button.click()

    assert vPanel.compare_button.text() == "Retirer de la comparaison"
    assert vPanel.show_comparison_button.text() == "Voir la comparaison (1)"

    vShown = []
    monkeypatch.setattr(
        offer_assistant,
        "show_text_dialog",
        lambda pParent, pTitle, pHtml: vShown.append(pHtml),
    )
    vPanel.show_comparison()

    assert "Dev &lt;Go&gt;" in vShown[0]
    assert "Correspondance" in vShown[0]
