"""Tests du tableau de bord des compétences"""

from datetime import datetime

import pandas as pd

from job.quiz import load_quiz
from job.skills_dashboard import (
    build_skill_rows,
    build_skills_dashboard,
    count_skill_demand,
    find_catalog_theme,
    get_skill_status,
    summarize_skills,
)
from storage.database import initialize_database
from storage.job_offers import save_offers

KNOWN = {"python": "Python", "aws": "AWS", "sql": "SQL"}

THEMES = [
    {
        "key": "python",
        "label": "Python",
        "domain": "Informatique",
        "subdomain": "Développement",
        "skills": ["Python"],
        "correct": 9,
        "total": 10,
    },
    {
        "key": "sql",
        "label": "SQL",
        "domain": "Informatique",
        "subdomain": "Données",
        "skills": ["SQL"],
        "correct": 1,
        "total": 10,
    },
]


def test_count_skill_demand_merges_case_and_ignores_tags():
    """Vérifie qu'une offre compte une fois par compétence, étiquettes inconnues exclues."""

    vCounts = count_skill_demand(
        [["Python", "python", "ai"], ["AWS", "fintech"], [], ["sql"]], KNOWN
    )

    assert vCounts == {"Python": 1, "AWS": 1, "SQL": 1}


def test_get_skill_status():
    """Vérifie les états selon l'existence de thèmes et le score."""

    assert get_skill_status([], 0) == "missing"
    assert get_skill_status(THEMES, 10) == "todo"
    assert get_skill_status(THEMES, 50) == "progress"
    assert get_skill_status(THEMES, 90) == "done"


def test_rows_and_summary():
    """Vérifie l'ordre, le score des thèmes, le profil, le catalogue et la synthèse."""

    vCatalog = [
        {
            "label": "Cloud et infrastructure",
            "domain": "Informatique",
            "subdomain": "Exploitation et DevOps",
            "skills": ("AWS", "Azure"),
        }
    ]
    vRows = build_skill_rows(
        {"SQL": 5, "Python": 8, "AWS": 6}, 20, THEMES, ["python"], vCatalog
    )

    assert [vRow["skill"] for vRow in vRows] == ["Python", "AWS", "SQL"]
    assert vRows[0]["share"] == 40
    assert vRows[0]["in_profile"]
    assert (vRows[0]["score"], vRows[0]["status"]) == (90, "done")
    assert (vRows[1]["status"], vRows[1]["catalog_label"]) == (
        "missing",
        "Cloud et infrastructure",
    )
    assert vRows[2]["themes"] == [("sql", "SQL")]
    assert find_catalog_theme(vCatalog, "Rust") is None
    assert vRows[1]["icon"] == "server"
    assert vRows[0]["icon"] == "code"

    assert summarize_skills(vRows) == {
        "skills": 3,
        "covered": 2,
        "in_profile": 1,
        "readiness": round((8 * 90 + 6 * 0 + 5 * 10) / 19),
        "priority": "AWS",
    }
    assert summarize_skills([])["priority"] is None


def test_build_skills_dashboard(tmp_path):
    """Vérifie le tableau de bord sur une base avec des offres enregistrées."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "a",
                    "source_id": "1",
                    "title": "Dev",
                    "skills": '["python"]',
                },
                {"source": "a", "source_id": "2", "title": "Dev", "skills": '["AWS"]'},
            ]
        ),
        datetime(2026, 10, 16),
    )

    vDashboard = build_skills_dashboard(vDatabaseFile, load_quiz())

    assert vDashboard["offer_count"] == 2
    assert {vRow["skill"] for vRow in vDashboard["rows"]} == {"Python", "AWS"}
    assert vDashboard["summary"]["covered"] == 1
