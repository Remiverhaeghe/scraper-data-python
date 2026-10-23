"""Tests de la carte des pages carrière suivies"""

import gui.company_pages_panel as company_pages_panel
from gui.company_pages_panel import CompanyPagesPanel
from job.company_pages import load_company_list
from storage.database import initialize_database


def test_lists_are_saved_then_checked(qt_application, tmp_path, monkeypatch):
    """Vérifie l'enregistrement des listes et le bilan de vérification."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.delenv("LEVER_COMPANIES", raising=False)
    vPanel = CompanyPagesPanel(vDatabaseFile)
    vPanel.refresh()

    assert vPanel.edits["smartrecruiters"].text().startswith("Alten, Assystem")

    vPanel.edits["lever"].setText("qonto,  inconnue\nmalt")
    vPanel.save()

    assert load_company_list("lever", vDatabaseFile) == "qonto,inconnue,malt"
    assert vPanel.edits["lever"].text() == "qonto, inconnue, malt"

    def count(pPlatform, pCompany):
        if pCompany == "inconnue":
            raise ValueError("404")
        return 12

    monkeypatch.setattr("job.company_pages.count_published_offers", count)
    for vPlatform in vPanel.edits:
        if vPlatform != "lever":
            vPanel.edits[vPlatform].clear()

    vPanel.check()

    assert "Lever · qonto : 12 offre(s)" in vPanel.result_label.text()
    assert "Lever · inconnue : introuvable" in vPanel.result_label.text()
    assert company_pages_panel.PLATFORMS
