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


def test_company_is_added_from_a_career_site_address(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie l'ajout depuis une adresse collée, puis le refus d'une adresse inconnue."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    monkeypatch.delenv("LEVER_COMPANIES", raising=False)
    monkeypatch.setattr(
        "job.company_pages.count_published_offers", lambda pPlatform, pCompany: 7
    )
    vPanel = CompanyPagesPanel(vDatabaseFile)

    vPanel.url_edit.setText("https://jobs.lever.co/doctolib/123")
    vPanel.add_from_url()

    assert load_company_list("lever", vDatabaseFile).endswith(",doctolib")
    assert "doctolib ajoutée : 7 offre(s)" in vPanel.message_label.text()
    assert vPanel.url_edit.text() == ""

    vPanel.url_edit.setText("https://www.exemple.fr/carrieres")
    vPanel.add_from_url()

    assert "Adresse non reconnue" in vPanel.message_label.text()
