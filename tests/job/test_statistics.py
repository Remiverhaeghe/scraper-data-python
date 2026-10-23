"""Tests des indicateurs communs au bureau et au web"""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from job.profile import EMPTY_PROFILE, save_profile
from job.settings import save_settings
from job.statistics import (
    MAX_PIE_SOURCES,
    build_source_cells,
    compare_sources,
    describe_useless_sources,
    get_source_shares,
    get_week_goal,
    trim_leading_empty_days,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers


def test_get_source_shares_groups_smallest_sources(tmp_path):
    """Vérifie les parts par source et le regroupement des plus petites."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vSources = (
        ["adzuna"] * 4
        + ["jooble"] * 2
        + [
            "jobicy",
            "himalayas",
            "remotive",
            "arbeitnow",
            "findwork",
        ]
    )

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": vSource, "source_id": str(vIndex)}
                for vIndex, vSource in enumerate(vSources)
            ]
        ),
        datetime(2026, 10, 10),
    )

    rShares = get_source_shares(vDatabaseFile)

    assert len(rShares) == MAX_PIE_SOURCES
    assert rShares[0] == {"label": "Adzuna", "count": 4, "percent": 36}
    assert rShares[-1]["label"] == "Autres"
    assert sum(vShare["count"] for vShare in rShares) == len(vSources)


def build_activity(pCounts):
    """Construit une série quotidienne à partir de valeurs, un jour par valeur."""

    rActivity = [
        (date(2026, 10, vDay + 1), vCount) for vDay, vCount in enumerate(pCounts)
    ]

    return rActivity


@pytest.mark.parametrize(
    "pOffers, pApplications, pExpectedDays",
    [
        ([0] * 10 + [5, 0, 0, 2], [0] * 14, 4),
        ([0, 0, 3] + [0] * 11, [0] * 14, 12),
        ([0] * 14, [0] * 12 + [1, 0], 2),
        ([0] * 14, [0] * 14, 1),
    ],
)
def test_trim_leading_empty_days(pOffers, pApplications, pExpectedDays):
    """Vérifie que l'activité démarre au premier jour actif, sans jour vide avant."""

    rActivity = trim_leading_empty_days(
        {
            "new_offers": build_activity(pOffers),
            "applications": build_activity(pApplications),
        }
    )

    assert len(rActivity["new_offers"]) == pExpectedDays
    assert len(rActivity["applications"]) == pExpectedDays


def test_week_goal_counts_applications_since_monday(tmp_path):
    """Vérifie l'objectif de la semaine, compté depuis lundi minuit."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 21, 15, 0)

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": str(vId), "title": "Dev"}
                for vId in range(3)
            ]
        ),
        vNow,
    )

    for vId, vDays in ((0, 3), (1, 1), (2, 0)):
        save_application(
            vDatabaseFile,
            "remotive",
            str(vId),
            "APPLIED",
            pNow=vNow - timedelta(days=vDays),
        )

    assert get_week_goal(vDatabaseFile, vNow)["share"] is None

    save_settings(vDatabaseFile, {"weekly_application_goal": "4"})

    assert get_week_goal(vDatabaseFile, vNow) == {"goal": 4, "sent": 2, "share": 50}


def test_compare_sources_ranks_useful_sources_first(tmp_path):
    """Vérifie les comptes par source sur la période et le tri par utilité."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 23, 12)

    initialize_database(vDatabaseFile)
    save_profile(
        vDatabaseFile, {**EMPTY_PROFILE, "skills": ["Python", "Django", "SQL"]}
    )

    # Trois compétences : le score est rapporté à trois au minimum.
    vOffers = [
        ("arbeitnow", "1", "Développeur Python", "Python, Django et Docker."),
        ("arbeitnow", "2", "Comptable", "Bilans et paie."),
        ("arbeitnow", "3", "Vendeur", "Magasin."),
        ("lever", "4", "Développeur Python", "Python, Django et SQL requis."),
    ]
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": vSource,
                    "source_id": vId,
                    "title": vTitle,
                    "description": vDescription,
                }
                for vSource, vId, vTitle, vDescription in vOffers
            ]
        ),
        vNow,
    )
    save_application(vDatabaseFile, "arbeitnow", "2", "IGNORED", pNow=vNow)
    save_application(vDatabaseFile, "lever", "4", "APPLIED", pNow=vNow)

    vRows = compare_sources(vDatabaseFile, vNow)

    assert [vRow["source"] for vRow in vRows] == ["lever", "arbeitnow"]
    assert vRows[1] | {"label": ""} == {
        "source": "arbeitnow",
        "label": "",
        "offers": 3,
        "good": 1,
        "kept": 0,
        "sent": 0,
        "ignored": 1,
        "good_rate": 33,
        "average_score": 67,
    }
    assert build_source_cells(vRows[0])[1:] == [
        "1",
        "1 (100 %)",
        "1",
        "1",
        "0",
        "100 %",
    ]
    assert compare_sources(vDatabaseFile, vNow + timedelta(days=31)) == []


def test_compare_sources_with_a_profile_and_offers_without_skills(tmp_path):
    """Vérifie qu'une offre sans compétences enregistrées (NaN) ne bloque rien."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 23, 12)

    initialize_database(vDatabaseFile)
    save_profile(vDatabaseFile, {**EMPTY_PROFILE, "skills": ["Java"]})
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "1", "title": "Dev Java"},
                {
                    "source": "lever",
                    "source_id": "2",
                    "title": "Dev",
                    "skills": ["Java"],
                },
            ]
        ),
        vNow,
    )

    assert compare_sources(vDatabaseFile, vNow)[0]["offers"] == 2


def test_compare_sources_without_profile_has_no_score(tmp_path):
    """Vérifie qu'un profil vide donne un score moyen absent, affiché par un tiret."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 23, 12)

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame([{"source": "lever", "source_id": "1", "title": "Dev"}]),
        vNow,
    )

    assert build_source_cells(compare_sources(vDatabaseFile, vNow)[0])[-1] == "—"


def test_useless_sources_need_a_profile_and_enough_offers():
    """Vérifie le conseil : assez d'offres, aucune utile, et un profil renseigné."""

    def build_row(pLabel, pOffers, pGood=0, pScore=10):
        return {
            "label": pLabel,
            "offers": pOffers,
            "good": pGood,
            "kept": 0,
            "sent": 0,
            "average_score": pScore,
        }

    vRows = [
        build_row("Arbeitnow", 120),
        build_row("Lever", 40, pGood=3),
        build_row("Jooble", 5),
    ]

    assert describe_useless_sources(vRows).endswith(": Arbeitnow (120 offres)")
    assert describe_useless_sources([build_row("Arbeitnow", 120, pScore=None)]) == ""
    assert describe_useless_sources(vRows[1:]) == ""
