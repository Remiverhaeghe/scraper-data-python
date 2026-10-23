"""Tests du journal de recherche d'emploi"""

from datetime import datetime

import pandas as pd

from job.application_tracking import mark_followed_up
from job.search_journal import build_search_journal, write_journal_csv
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers


def test_journal_lists_dated_steps_of_the_period(tmp_path):
    """Vérifie les démarches datées de la période, et la formule neutralisée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "lever",
                    "source_id": "1",
                    "title": "Dev",
                    "company": "=Acme",
                },
                {
                    "source": "lever",
                    "source_id": "2",
                    "title": "Ops",
                    "company": "Beta",
                },
            ]
        ),
        datetime(2026, 9, 1),
    )
    save_application(vDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 2))
    mark_followed_up(vDatabaseFile, "lever", "1", datetime(2026, 10, 10))
    save_application(vDatabaseFile, "lever", "2", "INTERESTED")

    vRows = build_search_journal(
        vDatabaseFile, datetime(2026, 10, 1), datetime(2026, 10, 10)
    )
    vCsv = write_journal_csv(vRows).decode("utf-8-sig")

    assert [vRow["step"] for vRow in vRows] == ["Candidature envoyée", "Relance"]
    assert vCsv.splitlines()[0].startswith("Date;Démarche;Entreprise")
    assert "02/10/2026" in vCsv
    assert ";'=Acme;" in vCsv
    assert (
        build_search_journal(
            vDatabaseFile, datetime(2026, 10, 3), datetime(2026, 10, 9)
        )
        == []
    )
