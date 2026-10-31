"""Tests du planning de la semaine : tâches par jour, déplacements, révisions, agenda"""

from datetime import date, datetime

import pandas as pd
import pytest

from job.calendar import build_calendar
from job.weekly_planning import (
    add_revision,
    build_week,
    delete_revision,
    get_monday,
    load_planned_revisions,
    move_item,
)
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 28, 9, 0)


@pytest.fixture
def database_file(tmp_path):
    """Fournit une candidature avec une relance le mercredi et un entretien le jeudi."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Technicien",
                    "company": "Acme",
                }
            ]
        ),
        NOW,
    )
    save_application(
        rDatabaseFile,
        "remotive",
        "1",
        "APPLIED",
        pFollowUpDate=date(2026, 10, 28),
        pInterviewAt=datetime(2026, 10, 29, 14, 30),
        pNow=NOW,
    )

    return rDatabaseFile


def test_week_groups_tasks_by_day(database_file):
    """Vérifie la semaine du lundi au dimanche, les tâches du bon jour et les quêtes."""

    add_revision(database_file, date(2026, 10, 30), "  Schémas   électriques ")
    vWeek = build_week(database_file, date(2026, 10, 31), NOW)
    vLabels = [[vItem["label"] for vItem in vDay["items"]] for vDay in vWeek["days"]]

    assert get_monday(date(2026, 11, 1)) == vWeek["monday"] == date(2026, 10, 26)
    assert vLabels[2] == ["Relancer : Technicien – Acme"]
    assert vLabels[3] == ["Entretien : Technicien – Acme"]
    assert vWeek["days"][3]["items"][0]["time"] == "14:30"
    assert vLabels[4] == ["Réviser : Schémas électriques"]
    assert vWeek["days"][2]["today"] and vWeek["days"][0]["name"] == "lundi"
    assert all(vQuest["weekly"] for vQuest in vWeek["quests"])


def test_moving_tasks_changes_their_date_and_the_calendar(database_file):
    """Vérifie le déplacement d'une relance, d'un entretien à heure fixe et d'une révision."""

    add_revision(database_file, date(2026, 10, 30), "SQL")
    vRevision = load_planned_revisions(database_file)[0]

    move_item(database_file, "follow-up|remotive|1", date(2026, 10, 30))
    move_item(database_file, "interview|remotive|1", date(2026, 11, 2))
    move_item(database_file, f"revision|{vRevision['id']}", date(2026, 10, 27))

    vApplication = get_application(database_file, "remotive", "1")

    assert str(vApplication["follow_up_date"]).startswith("2026-10-30")
    assert vApplication["interview_at"] == "2026-11-02T14:30:00"

    vCalendar = build_calendar(database_file, NOW)

    assert "DTSTART;VALUE=DATE:20261027" in vCalendar
    assert "SUMMARY:Réviser : SQL" in vCalendar
    assert "DTSTART:20261102T143000" in vCalendar

    for vItemId in ("revision|absente", "inconnu|x", "follow-up|remotive|2"):
        with pytest.raises(ValueError):
            move_item(database_file, vItemId, date(2026, 10, 30))

    delete_revision(database_file, vRevision["id"])

    assert load_planned_revisions(database_file) == []

    with pytest.raises(ValueError):
        add_revision(database_file, date(2026, 10, 30), "   ")
