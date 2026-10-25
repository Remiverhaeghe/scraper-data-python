"""Tests des indicateurs communs au bureau et au web"""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from job.health import check_useful_sources
from job.profile import EMPTY_PROFILE, save_profile
from job.settings import save_settings
from job.statistics import (
    compare_saved_searches,
    build_month_summary,
    describe_interview_sources,
    find_hot_offers,
    load_source_review,
    run_due_source_review,
    MAX_PIE_SOURCES,
    build_source_cells,
    compare_sources,
    describe_useless_sources,
    get_source_shares,
    get_week_goal,
    summarize_week,
    trim_leading_empty_days,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers
from storage.saved_searches import save_search


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


def test_saved_searches_are_compared_on_their_criteria(tmp_path):
    """Vérifie la comparaison des recherches : offres qui répondent, suites données."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "1", "title": "Développeur JEE"},
                {"source": "lever", "source_id": "2", "title": "Technicien GMAO"},
                {"source": "lever", "source_id": "3", "title": "Comptable"},
            ]
        ),
        datetime.now(),
    )
    save_application(vDatabaseFile, "lever", "1", "APPLIED")
    save_search(vDatabaseFile, "Java", ["lever"], {"keyword": "java"}, datetime.now())
    save_search(
        vDatabaseFile,
        "Maintenance",
        ["lever"],
        {"keyword": "maintenance"},
        datetime.now(),
    )
    save_search(
        vDatabaseFile, "Pilote", ["lever"], {"keyword": "pilote"}, datetime.now()
    )

    vRows = compare_saved_searches(vDatabaseFile, datetime.now())

    # « JEE » répond à Java et « GMAO » à maintenance, par les synonymes.
    assert [(vRow["label"], vRow["offers"], vRow["sent"]) for vRow in vRows] == [
        ("Java", 1, 1),
        ("Maintenance", 1, 0),
    ]


def test_summarize_week_compares_with_previous_week():
    """Vérifie le bilan : 7 derniers jours, 7 précédents et évolution."""

    vFirstDay = date(2026, 10, 1)
    vDays = [vFirstDay + timedelta(days=vOffset) for vOffset in range(14)]

    rWeek = summarize_week(
        {
            "new_offers": [(vDay, 2) for vDay in vDays[:7]]
            + [(vDay, 3) for vDay in vDays[7:]],
            "applications": [(vDay, 1) for vDay in vDays[:7]]
            + [(vDay, 0) for vDay in vDays[7:]],
            "responses": [(vDay, 0) for vDay in vDays],
        }
    )

    assert [
        (vRow["label"], vRow["current"], vRow["previous"], vRow["trend"])
        for vRow in rWeek
    ] == [
        ("Nouvelles offres", 21, 14, "+7"),
        ("Candidatures", 0, 7, "−7"),
        ("Réponses reçues", 0, 0, "="),
    ]


def test_hot_offers_are_recent_well_matched_and_untouched(tmp_path):
    """Vérifie les offres à saisir vite : récentes, bien notées et sans statut."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 24, 12)
    initialize_database(vDatabaseFile)
    save_profile(
        vDatabaseFile, {**EMPTY_PROFILE, "skills": ["Python", "Django", "SQL"]}
    )
    vText = "Python, Django et SQL requis."
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Dev",
                    "description": vText,
                },
                {
                    "source": "lever",
                    "source_id": "2",
                    "title": "Dev",
                    "description": vText,
                },
                {
                    "source": "lever",
                    "source_id": "3",
                    "title": "Vendeur",
                    "description": "Magasin.",
                },
                {
                    "source": "lever",
                    "source_id": "4",
                    "title": "Dev",
                    "description": vText,
                    "published_at": "2026-09-01",
                },
            ]
        ),
        vNow,
    )
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "5",
                    "title": "Dev",
                    "description": vText,
                }
            ]
        ),
        vNow - timedelta(days=5),
    )
    save_application(vDatabaseFile, "lever", "2", "APPLIED", pNow=vNow)

    vHot = find_hot_offers(vDatabaseFile, vNow)

    assert [vOffer["source_id"] for vOffer in vHot] == ["1"]
    assert vHot[0]["match_score"] == 100


def test_source_review_is_done_once_a_day_and_shown_in_health(tmp_path):
    """Vérifie la revue quotidienne des sources, puis son rappel dans Santé."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime(2026, 10, 24, 12)
    initialize_database(vDatabaseFile)
    save_profile(vDatabaseFile, {**EMPTY_PROFILE, "skills": ["Python"]})

    assert check_useful_sources(vDatabaseFile)[1] == "muted"

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "arbeitnow",
                    "source_id": str(vId),
                    "title": "Développeur Java",
                    "description": "Java et Spring requis.",
                }
                for vId in range(25)
            ]
        ),
        vNow,
    )

    vReview = run_due_source_review(vDatabaseFile, vNow)

    assert vReview["advice"].endswith("Arbeitnow (25 offres)")
    assert load_source_review(vDatabaseFile) == vReview
    assert run_due_source_review(vDatabaseFile, vNow + timedelta(hours=3)) is None
    assert check_useful_sources(vDatabaseFile) == (vReview["advice"], "warning")


def test_month_summary_counts_interviews_by_source(tmp_path):
    """Vérifie le bilan du mois : séries comparées et entretiens par source."""

    vDatabaseFile = tmp_path / "scraper.db"
    vNow = datetime.now()
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "1", "title": "Dev"},
                {"source": "adzuna", "source_id": "2", "title": "Data"},
            ]
        ),
        vNow,
    )
    save_application(vDatabaseFile, "lever", "1", "INTERVIEW", pNow=vNow)

    vMonth = build_month_summary(vDatabaseFile, vNow)

    assert vMonth["rows"][0]["current"] == 2
    assert vMonth["rows"][0]["label"] == "Nouvelles offres"
    assert describe_interview_sources(vMonth["interview_sources"]) == (
        "Entretiens obtenus ce mois-ci : Lever 1"
    )
    assert describe_interview_sources([]).startswith("Aucun entretien")
