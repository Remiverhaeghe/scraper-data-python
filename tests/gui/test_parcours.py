"""Parcours de bout en bout du bureau, d'une page à l'autre par la fenêtre principale"""

from datetime import datetime

import pandas as pd
import pytest

import gui.offer_assistant as offer_assistant
from gui.main_window import MainWindow
from job.quiz_exam import load_exam, load_exam_results
from storage.database import initialize_database
from storage.job_applications import get_application
from storage.job_offers import save_offers

OFFER_KEY = ("remotive", "1")


@pytest.fixture
def database_file(tmp_path):
    """Crée une base contenant une offre Python."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": OFFER_KEY[0],
                    "source_id": OFFER_KEY[1],
                    "title": "Développeur Python",
                    "company": "Acme",
                    "description": "API Python et base SQL.",
                }
            ]
        ),
        datetime.now(),
    )

    return rDatabaseFile


@pytest.fixture
def window(qt_application, database_file):
    """Ouvre la fenêtre principale sur cette base."""

    rWindow = MainWindow(database_file, "Test")

    return rWindow


def open_page(pWindow, pKey):
    """Ouvre une page comme un clic dans le menu latéral."""

    pWindow.navigation.setCurrentRow(pWindow.page_rows[pKey])


def get_page(pWindow, pKey):
    """Retourne la page d'une entrée du menu latéral."""

    rPage = pWindow.pages.widget(pWindow.page_rows[pKey])

    return rPage


def test_offer_application_then_follow_up(window, database_file):
    """De l'offre suivie à la relance notée depuis la page Candidatures."""

    open_page(window, "offers")
    window.offers_page.select_offer(OFFER_KEY)

    vApplication = window.offers_page.detail_panel.application
    vApplication.status_combo.setCurrentIndex(
        vApplication.status_combo.findData("APPLIED")
    )
    vApplication.save()

    open_page(window, "applications")
    vPage = window.applications_page

    assert vPage.statistic_cards["sent"].value_label.text() == "1"
    assert [vFollowUp["title"] for vFollowUp in vPage.follow_ups_panel.follow_ups] == [
        "Développeur Python"
    ]

    vPage.follow_ups_panel.mark_done(vPage.follow_ups_panel.follow_ups[0])

    assert get_application(database_file, *OFFER_KEY)["follow_up_count"] == 1


def test_profile_feeds_search_suggestions(window):
    """Du profil enregistré au mot-clé proposé sur la page Recherche."""

    open_page(window, "profile")
    vProfile = get_page(window, "profile")
    vProfile.skills_edit.setText("Python, SQL")
    vProfile.experiences_edit.setPlainText("Data engineer | Python | Flux fiables")
    vProfile.save()

    open_page(window, "search")
    vSearch = window.search_page
    vButton = vSearch.suggestions.chips_layout.itemAt(0).widget()

    assert vButton.text() == "Data engineer"

    vButton.click()

    assert vSearch.keyword_edit.text() == "Data engineer"


def test_offer_mock_exam_is_graded_and_kept(window, database_file, monkeypatch):
    """De l'examen blanc d'une offre à sa note, rappelée sur la fiche."""

    monkeypatch.setattr(
        offer_assistant.OfferAssistantPanel, "ask_exam_kind", lambda *pArgs: "all"
    )

    open_page(window, "offers")
    window.offers_page.select_offer(OFFER_KEY)
    window.offers_page.detail_panel.assistant.request_exam()

    vQuiz = window.quiz_page

    assert window.pages.currentWidget() is vQuiz
    assert vQuiz.exam_timer.isActive()

    for _ in range(len(load_exam(database_file)["ids"])):
        next(
            vButton
            for vButton in vQuiz.choices_group.buttons()
            if vQuiz.choices_group.id(vButton) == vQuiz.question["answer"]
        ).setChecked(True)
        vQuiz.validate()
        vQuiz.next_button.click()

    assert vQuiz.meta_label.text() == "Examen terminé"
    assert "Examens blancs : meilleure note 100 %" in vQuiz.question_label.text()
    assert load_exam_results(database_file, OFFER_KEY)[0]["score"] == 100

    open_page(window, "offers")
    window.offers_page.select_offer(OFFER_KEY)

    assert (
        window.offers_page.detail_panel.assistant.exam_results_label.text().startswith(
            "Examens blancs : meilleure note 100 %"
        )
    )
