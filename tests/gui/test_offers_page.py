"""Tests de la page des offres et du panneau de suivi"""

from datetime import datetime

import pandas as pd
import pytest

from gui.offer_detail import describe_application, summarize_values
from gui.offers_page import OffersPage
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import save_offers


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec trois offres Lever, dont une ignorée."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    vItems = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "1",
                "title": "Développeur Java",
                "contract": "CDI",
                "url": "https://example.com/1",
            },
            {
                "source": "lever",
                "source_id": "2",
                "title": "Data Engineer",
                "contract": "CDD",
            },
            {"source": "lever", "source_id": "3", "title": "Offre ignorée"},
        ]
    )

    save_offers(rDatabaseFile, vItems, datetime.now())
    save_application(rDatabaseFile, "lever", "3", "IGNORED")

    return rDatabaseFile


@pytest.fixture
def offers_page(qt_application, database_file):
    """Crée la page des offres chargée depuis la base de test."""

    rPage = OffersPage(database_file)
    rPage.refresh()

    return rPage


def get_titles(pPage):
    """Retourne les titres affichés, dans l'ordre du modèle."""

    rTitles = sorted(vOffer["title"] for vOffer in pPage.model.offers)

    return rTitles


def test_page_lists_active_offers(offers_page):
    """Vérifie que les offres ignorées sont masquées par défaut."""

    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]
    assert offers_page.count_label.text().startswith("2 offre(s)")


def test_page_applies_filters(offers_page):
    """Vérifie que les filtres de la page sont transmis à la requête."""

    offers_page.contract_combo.setCurrentIndex(
        offers_page.contract_combo.findData("CDI")
    )

    assert get_titles(offers_page) == ["Développeur Java"]

    offers_page.status_combo.setCurrentIndex(
        offers_page.status_combo.findData("IGNORED")
    )
    offers_page.contract_combo.setCurrentIndex(0)

    assert get_titles(offers_page) == ["Offre ignorée"]


def test_selection_displays_offer(offers_page):
    """Vérifie que la sélection d'une ligne remplit le panneau de détail."""

    offers_page.select_offer(("lever", "1"))

    assert offers_page.detail_panel.title_label.text() == "Développeur Java"
    assert offers_page.detail_panel.open_button.isEnabled()


def test_saving_application_keeps_selection(offers_page, database_file):
    """Vérifie l'enregistrement du suivi puis le maintien de la sélection."""

    offers_page.select_offer(("lever", "1"))

    vPanel = offers_page.detail_panel
    vPanel.status_combo.setCurrentIndex(vPanel.status_combo.findData("APPLIED"))
    vPanel.notes_edit.setPlainText("Contact : RH")
    vPanel.save()

    vApplication = get_application(database_file, "lever", "1")

    assert vApplication["status"] == "APPLIED"
    assert vApplication["notes"] == "Contact : RH"
    assert vApplication["follow_up_date"] is not None
    assert vPanel.offer["source_id"] == "1"
    assert vPanel.follow_up_button.isVisibleTo(vPanel)


def test_removing_status_deletes_application(offers_page, database_file):
    """Vérifie que « Aucun suivi » supprime le suivi existant."""

    save_application(database_file, "lever", "2", "INTERESTED")

    offers_page.select_offer(("lever", "2"))
    offers_page.detail_panel.status_combo.setCurrentIndex(0)
    offers_page.detail_panel.save()

    assert get_application(database_file, "lever", "2") is None


def test_describe_application():
    """Vérifie le résumé des dates de candidature et de relance."""

    vApplication = {
        "applied_at": "2026-10-01T09:00:00",
        "follow_up_count": 2,
        "last_follow_up_at": "2026-10-08T10:00:00",
    }

    assert describe_application(vApplication) == (
        "Candidature envoyée le 01/10/2026. 2 relance(s), la dernière le 08/10/2026."
    )
    assert describe_application(None) == ""


def test_empty_result_shows_empty_state(offers_page):
    """Vérifie l'état vide lorsqu'aucune offre ne correspond aux filtres."""

    offers_page.search_edit.setText("introuvable")
    offers_page.refresh()

    assert offers_page.detail_panel.stack.currentIndex() == 0
    assert offers_page.detail_panel.offer is None


def test_first_offer_is_selected_by_default(offers_page):
    """Vérifie qu'une offre est affichée sans action de l'utilisateur."""

    assert offers_page.detail_panel.stack.currentIndex() == 1
    assert offers_page.detail_panel.offer is not None


def test_apply_preset_resets_other_filters(offers_page):
    """Vérifie qu'un préréglage repart de filtres vierges."""

    offers_page.contract_combo.setCurrentIndex(
        offers_page.contract_combo.findData("CDD")
    )

    offers_page.apply_preset("new_offers")

    assert offers_page.contract_combo.currentData() is None
    assert offers_page.new_check.isChecked()
    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]


def test_export_uses_current_filters(offers_page, tmp_path):
    """Vérifie que l'export reprend les filtres affichés."""

    offers_page.contract_combo.setCurrentIndex(
        offers_page.contract_combo.findData("CDI")
    )

    assert offers_page.export_to(tmp_path / "offres.json") == 1


def test_empty_information_is_hidden(offers_page):
    """Vérifie qu'une information absente n'est pas affichée."""

    offers_page.select_offer(("lever", "1"))

    vRows = offers_page.detail_panel.info_rows

    assert not vRows["salary"][0].isVisibleTo(offers_page.detail_panel)
    assert vRows["contract"][0].isVisibleTo(offers_page.detail_panel)
    assert vRows["contract"][1].text() == "CDI"


def test_search_results_are_shown_alone(offers_page):
    """Vérifie l'affichage des seuls résultats d'une recherche, puis le retour."""

    offers_page.apply_preset("offers", [("lever", "2")], "Résultats de la recherche")

    assert get_titles(offers_page) == ["Data Engineer"]
    assert offers_page.results_banner.isVisibleTo(offers_page)

    offers_page.apply_preset("offers")

    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]
    assert not offers_page.results_banner.isVisibleTo(offers_page)


def test_salary_and_publication_filters(offers_page):
    """Vérifie que les nouveaux filtres sont transmis à la requête."""

    offers_page.max_salary_spin.setValue(2500)
    offers_page.salary_check.setChecked(True)
    offers_page.published_combo.setCurrentIndex(2)

    vFilters = offers_page.build_filters(datetime.now(), 3)

    assert vFilters["pMaxNetSalary"] == 2500
    assert vFilters["pHasSalary"] is True
    assert vFilters["pPublishedSince"] is not None


@pytest.mark.parametrize(
    "pValues, pExpected",
    [
        (None, ""),
        (["Java", "SQL"], "Java, SQL"),
        (["A", "B", "C", "D", "E", "F"], "A, B, C, D +2"),
    ],
)
def test_summarize_values(pValues, pExpected):
    """Vérifie qu'une longue liste est abrégée pour tenir dans le panneau."""

    assert summarize_values(pValues) == pExpected
