"""Tests de la page d'accueil"""

from datetime import datetime

import pandas as pd

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QPushButton

from gui.home_page import HomePage, describe_activity
from gui.progress_widgets import GAME_MODE_SETTING
from job.statistics import CHART_DAYS, load_statistics
from gui.theme import COLORS
from scraper.history import HistoryEntry
from storage.database import initialize_database
from storage.history_repository import save_history
from storage.job_applications import save_application
from storage.job_offers import save_offers


def build_database(pTmpPath):
    """Crée une base avec trois offres, une candidature et une exécution."""

    rDatabaseFile = pTmpPath / "scraper.db"

    initialize_database(rDatabaseFile)

    vItems = pd.DataFrame(
        [
            {"source": "lever", "source_id": vId, "title": f"Offre {vId}"}
            for vId in "123"
        ]
    )

    save_offers(rDatabaseFile, vItems.iloc[:2], datetime(2026, 9, 1))
    save_offers(rDatabaseFile, vItems.iloc[2:], datetime(2026, 10, 9))

    save_application(rDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 1))
    save_application(rDatabaseFile, "lever", "2", "IGNORED")

    save_history(
        rDatabaseFile,
        HistoryEntry(
            started_at=datetime(2026, 10, 9, 8, 30),
            scraper_type="job",
            url="multi-source",
            page_count=2,
            item_count=42,
            duration_seconds=3.25,
            status="partial",
        ),
    )

    return rDatabaseFile


def test_load_statistics(tmp_path):
    """Vérifie le calcul des indicateurs de l'accueil."""

    rStatistics = load_statistics(build_database(tmp_path), datetime(2026, 10, 10))

    assert rStatistics["offers"] == 2
    assert rStatistics["new_offers"] == 1
    assert rStatistics["applications"] == 1
    assert rStatistics["follow_ups"] == 1
    assert [vEntry.item_count for vEntry in rStatistics["executions"]] == [42]
    assert [vRow["name"] for vRow in rStatistics["week_summary"]] == [
        "new_offers",
        "applications",
        "follow_ups",
        "responses",
    ]


def test_load_statistics_on_empty_database(tmp_path):
    """Vérifie que les indicateurs d'une base vide valent zéro."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    rStatistics = load_statistics(vDatabaseFile)

    assert rStatistics["offers"] == 0
    assert rStatistics["executions"] == []


def build_entry(**pValues):
    """Construit une exécution de recherche d'offres partielle."""

    vValues = {
        "started_at": datetime(2026, 10, 9, 8, 30),
        "scraper_type": "job",
        "url": "multi-source",
        "page_count": 2,
        "item_count": 42,
        "duration_seconds": 3.25,
        "status": "partial",
        "parameters": {"keyword": "Java", "sources": ["adzuna"]},
    }

    vValues.update(pValues)

    rEntry = HistoryEntry(**vValues)

    return rEntry


def test_describe_activity():
    """Vérifie la ligne d'activité d'une exécution."""

    vIcon, vColor, vTitle, vDetail, vSources, vResult = describe_activity(build_entry())

    assert vIcon == "circle-alert"
    assert vColor == COLORS["warning"]
    assert vTitle == "Java"
    assert vDetail == "09/10/2026 à 08:30 · Adzuna"
    assert vSources == "Adzuna"
    assert vResult == "42 offre(s)"


def test_describe_activity_counts_many_sources():
    """Vérifie qu'au-delà de trois sources, la ligne affiche leur nombre."""

    _, _, _, vDetail, vSources, _ = describe_activity(
        build_entry(
            parameters={"sources": ["adzuna", "jooble", "remotive", "himalayas"]}
        )
    )

    assert vDetail == "09/10/2026 à 08:30 · 4 sources"
    assert vSources == "Adzuna, Jooble, Remotive, Himalayas"


def test_describe_activity_without_parameters():
    """Vérifie une exécution réussie antérieure à l'enregistrement des paramètres."""

    vIcon, _, vTitle, vDetail, _, _ = describe_activity(
        build_entry(status="success", parameters=None)
    )

    assert vIcon == "circle-check"
    assert vTitle == "Recherche d'offres"
    assert vDetail == "09/10/2026 à 08:30"


def test_home_page_displays_statistics(qt_application, tmp_path):
    """Vérifie que la page affiche les indicateurs et l'activité lus en base."""

    vPage = HomePage(build_database(tmp_path))

    vPage.refresh()

    assert vPage.cards["offers"].value_label.text() == "2"
    assert vPage.activity_layout.count() == 1


def test_home_page_requests_navigation(qt_application, tmp_path):
    """Vérifie que la bannière demande l'ouverture de la page de recherche."""

    vTargets = []

    vPage = HomePage(build_database(tmp_path))
    vPage.navigation_requested.connect(vTargets.append)

    vPage.findChild(QPushButton, "bannerButton").click()

    assert vTargets == ["search"]


def test_statistic_card_requests_filtered_offers(qt_application, tmp_path):
    """Vérifie qu'un clic sur une carte demande les offres correspondantes."""

    vTargets = []

    vPage = HomePage(build_database(tmp_path))
    vPage.navigation_requested.connect(vTargets.append)

    vPage.cards["follow_ups"].clicked.emit()

    assert vTargets == ["follow_ups"]


def test_home_page_fills_chart(qt_application, tmp_path):
    """Vérifie que le graphique reçoit une valeur par jour et par activité."""

    vPage = HomePage(build_database(tmp_path))
    vPage.refresh()

    assert 1 <= len(vPage.chart.labels) <= CHART_DAYS
    assert [vName for vName, _, _ in vPage.chart.series] == [
        "Nouvelles offres",
        "Candidatures",
        "Relances",
    ]


def test_similar_offers_card_is_shown_only_with_offers(qt_application, tmp_path):
    """Vérifie la carte des offres proches, masquée sans offre retenue."""

    vPage = HomePage(build_database(tmp_path))
    vPage.refresh()

    assert vPage.similar_offers_card.isHidden()

    vPage.show_similar_offers(
        [
            {
                "source": "lever",
                "source_id": "3",
                "title": "Technicien",
                "company": "Acme",
                "similarity": 75,
                "reference_title": "Technicien de maintenance",
            }
        ]
    )

    assert not vPage.similar_offers_card.isHidden()
    assert vPage.similar_offers_layout.count() == 1


def test_checklist_card_opens_the_page_to_set(qt_application, tmp_path):
    """Vérifie la carte À faire : une ligne par réglage, qui ouvre sa page."""

    vPage = HomePage(build_database(tmp_path))
    vRequested = []
    vPage.navigation_requested.connect(vRequested.append)
    vPage.refresh()

    assert not vPage.checklist_card.isHidden()

    vPage.checklist_layout.itemAt(0).widget().click()
    vPage.show_checklist([])

    assert vRequested == ["profile"]
    assert vPage.checklist_card.isHidden()


def test_withdrawn_card_is_shown_only_with_offers(qt_application, tmp_path):
    """Vérifie la carte des offres suivies retirées, masquée sans elles."""

    vPage = HomePage(build_database(tmp_path))
    vPage.refresh()

    assert vPage.withdrawn_card.isHidden()

    vPage.show_withdrawn(
        [
            {
                "source": "lever",
                "source_id": "1",
                "title": "Dev",
                "company": "Acme",
                "status": "APPLIED",
            }
        ]
    )

    assert not vPage.withdrawn_card.isHidden()
    assert vPage.withdrawn_layout.count() == 1


def test_mascot_greets_unless_the_game_is_off(qt_application, tmp_path):
    """Vérifie la mascotte du bandeau, remplacée par les icônes sans jeu."""

    vPage = HomePage(build_database(tmp_path))
    vPage.refresh()

    assert not vPage.mascot.isHidden() and vPage.banner_icons.isHidden()
    assert vPage.mascot_bubble.text()

    QSettings().setValue(GAME_MODE_SETTING, "off")
    vPage.refresh()

    assert vPage.mascot.isHidden() and not vPage.banner_icons.isHidden()
