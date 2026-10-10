"""Tests de la page de recherche"""

import time
from types import SimpleNamespace

import pandas as pd
import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from gui.search_page import SearchPage
from gui.search_worker import SearchWorker
from job.sources.aggregator import ScrapingCancelled


@pytest.fixture
def search_page(qt_application, tmp_path):
    """Crée une page dont les réglages sont isolés dans un fichier temporaire."""

    rPage = SearchPage(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))

    return rPage


def wait_until(pCondition, pTimeout=5):
    """Traite les événements Qt jusqu'à ce que la condition soit remplie."""

    vDeadline = time.monotonic() + pTimeout

    while not pCondition() and time.monotonic() < vDeadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert pCondition()


class FakeController:
    """Simule une recherche sur deux sources, interruptible entre les deux."""

    def __init__(self, pResult):
        self.result = pResult

    def search_jobs(self, pSources, pCriteria, pOnProgress=None, pCancelEvent=None):
        pOnProgress(1, 2, "Adzuna")

        time.sleep(0.2)

        if pCancelEvent.is_set():
            raise ScrapingCancelled()

        pOnProgress(2, 2, "Remotive")

        return self.result


def use_fake_controller(pPage, pResult=None):
    """Remplace le traitement réel par le contrôleur simulé."""

    pPage.create_worker = lambda pSources, pCriteria: SearchWorker(
        pSources, pCriteria, FakeController(pResult)
    )


def select_only_remotive(pPage):
    """Sélectionne Remotive, qui ne demande aucune configuration."""

    pPage.check_sources(False)
    pPage.source_buttons["remotive"].setChecked(True)


def test_unavailable_source_cannot_be_selected(search_page):
    """Vérifie qu'une source indisponible n'est jamais transmise."""

    search_page.check_sources(True)

    assert not search_page.source_buttons["france-travail"].isEnabled()
    assert "france-travail" not in search_page.get_selected_sources()


def test_build_criteria_converts_empty_values(search_page):
    """Vérifie que les champs vides et les zéros deviennent des critères absents."""

    search_page.keyword_edit.setText("  Java  ")
    search_page.contract_combo.setCurrentIndex(
        search_page.contract_combo.findData("CDI")
    )
    search_page.min_salary_spin.setValue(2500)

    rCriteria = search_page.build_criteria()

    assert rCriteria["keyword"] == "Java"
    assert rCriteria["location"] is None
    assert rCriteria["contract"] == "CDI"
    assert rCriteria["min_salary"] == 2500
    assert rCriteria["remote"] is None
    assert rCriteria["max_pages"] is None
    assert rCriteria["max_distance_km"] is None


def test_settings_are_restored(qt_application, tmp_path):
    """Vérifie que les derniers critères sont proposés à la réouverture."""

    vSettings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)

    vPage = SearchPage(vSettings)
    vPage.keyword_edit.setText("Python")
    select_only_remotive(vPage)
    vPage.save_settings()

    vReopenedPage = SearchPage(vSettings)

    assert vReopenedPage.keyword_edit.text() == "Python"
    assert vReopenedPage.get_selected_sources() == ["remotive"]


def test_search_without_source_is_refused(search_page):
    """Vérifie qu'aucune recherche n'est lancée sans source."""

    search_page.check_sources(False)

    search_page.start_search()

    assert not search_page.is_running()
    assert search_page.status_label.text() == "Sélectionnez au moins une source."


def test_search_displays_result(search_page):
    """Vérifie le déroulement complet d'une recherche dans son thread."""

    vResult = SimpleNamespace(
        items=pd.DataFrame(
            {
                "title": ["A", "B"],
                "source": ["remotive", "jobicy"],
                "source_id": ["1", "2"],
                "is_new": [True, False],
            }
        ),
        error_message="Jooble : délai dépassé",
    )

    use_fake_controller(search_page, vResult)
    select_only_remotive(search_page)

    search_page.start_search()

    assert search_page.is_running()
    assert not search_page.start_button.isEnabled()

    wait_until(lambda: not search_page.is_running())

    assert search_page.progress_bar.value() == 100
    assert search_page.result_label.text() == (
        "2 offre(s) correspondent aux critères, dont 1 nouvelle(s)."
    )
    assert "Jooble" in search_page.warning_label.text()
    assert search_page.start_button.isEnabled()


def test_search_can_be_stopped(search_page):
    """Vérifie qu'un arrêt termine la recherche sans résultat."""

    use_fake_controller(search_page)
    select_only_remotive(search_page)

    search_page.start_search()
    search_page.stop_search()

    wait_until(lambda: not search_page.is_running())

    assert search_page.status_label.text() == (
        "Recherche arrêtée, aucune offre enregistrée"
    )
    assert search_page.progress_bar.value() == 0


def test_show_offers_sends_search_results(search_page):
    """Vérifie que « Voir les offres » transmet les seules offres trouvées."""

    vRequests = []

    search_page.show_offers_requested.connect(
        lambda pKeys, pDescription: vRequests.append((pKeys, pDescription))
    )

    search_page.show_result(
        SimpleNamespace(
            items=pd.DataFrame(
                {"source": ["remotive"], "source_id": ["7"], "is_new": [True]}
            ),
            error_message=None,
        )
    )
    search_page.show_offers_button.click()

    assert vRequests[0][0] == [("remotive", "7")]
    assert "1 offre(s), dont 1 nouvelle(s)" in vRequests[0][1]


def test_build_criteria_splits_word_lists(search_page):
    """Vérifie le découpage des compétences et des mots à exclure."""

    search_page.skills_edit.setText(" Java, Spring ,, SQL ")
    search_page.exclude_edit.setText("stage")
    search_page.max_salary_spin.setValue(4000)

    rCriteria = search_page.build_criteria()

    assert rCriteria["skills"] == ["Java", "Spring", "SQL"]
    assert rCriteria["exclude_keywords"] == ["stage"]
    assert rCriteria["max_salary"] == 4000
