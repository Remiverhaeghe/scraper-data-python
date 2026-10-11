"""Tests de l'export des relances et des entretiens vers un agenda"""

from datetime import datetime

import pandas as pd

from job.calendar import build_calendar, escape_text, fold_line
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 11, 10, 0)


def test_escape_and_fold():
    """Vérifie l'échappement des caractères spéciaux et le repli des longues lignes."""

    assert escape_text("Dev, Java; ok\\\nsuite") == "Dev\\, Java\\; ok\\\\\\nsuite"

    vLines = fold_line("SUMMARY:" + "é" * 60)

    assert len(vLines) == 2
    assert all(len(vLine.encode("utf-8")) <= 75 for vLine in vLines)
    assert vLines[1].startswith(" ")


def test_build_calendar_lists_follow_ups_and_interviews(tmp_path):
    """Vérifie une relance sur la journée et un entretien d'une heure."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": vId,
                    "title": vTitle,
                    "company": "Acme",
                    "url": "https://acme.example",
                }
                for vId, vTitle in (("1", "Java"), ("2", "Python"), ("3", "Go"))
            ]
        ),
        NOW,
    )
    save_application(
        vDatabaseFile,
        "remotive",
        "1",
        "APPLIED",
        pFollowUpDate=datetime(2026, 10, 18),
        pNow=NOW,
    )
    save_application(
        vDatabaseFile,
        "remotive",
        "2",
        "INTERVIEW",
        pFollowUpDate=None,
        pNow=NOW,
        pInterviewAt=datetime(2026, 10, 20, 14, 30),
    )
    save_application(vDatabaseFile, "remotive", "3", "REJECTED", pNow=NOW)

    vText = build_calendar(vDatabaseFile, NOW)

    assert vText.startswith("BEGIN:VCALENDAR\r\n")
    assert vText.endswith("END:VCALENDAR\r\n")
    assert "DTSTART;VALUE=DATE:20261018\r\nDTEND;VALUE=DATE:20261019" in vText
    assert "SUMMARY:Relancer : Java – Acme" in vText
    assert "DTSTART:20261020T143000\r\nDTEND:20261020T153000" in vText
    assert "SUMMARY:Entretien : Python – Acme" in vText
    assert "Go" not in vText
