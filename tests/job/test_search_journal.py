"""Tests du journal de recherche d'emploi"""

from datetime import date, datetime

import pandas as pd

from job.application_tracking import mark_followed_up
from job.profile import build_profile, save_profile
from job.search_journal import (
    build_monthly_report,
    build_search_journal,
    parse_month,
    write_journal_csv,
)
from job.spontaneous_applications import save_spontaneous
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


def test_spontaneous_applications_are_in_the_journal(tmp_path):
    """Vérifie que l'envoi et la relance d'une candidature spontanée sont datés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_spontaneous(
        vDatabaseFile, "123456789", "Menuiserie Démo", "sent", date(2026, 10, 5)
    )
    save_spontaneous(
        vDatabaseFile, "123456789", "Menuiserie Démo", "followed_up", date(2026, 10, 20)
    )

    vRows = build_search_journal(
        vDatabaseFile, datetime(2026, 10, 1), datetime(2026, 10, 31)
    )

    assert [(vRow["step"], vRow["company"]) for vRow in vRows] == [
        ("Candidature spontanée", "Menuiserie Démo"),
        ("Relance", "Menuiserie Démo"),
    ]
    assert vRows[1]["status"] == "Relancée"


def test_monthly_report_counts_each_kind_of_step(tmp_path):
    """Vérifie le récapitulatif du mois : bornes, nombres par démarche et nom."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [{"source": "lever", "source_id": "1", "title": "Dev", "company": "Acme"}]
        ),
        datetime(2026, 9, 1),
    )
    save_application(
        vDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 31, 18)
    )
    mark_followed_up(vDatabaseFile, "lever", "1", datetime(2026, 11, 2))
    save_spontaneous(vDatabaseFile, "1", "Garage Démo", "sent", date(2026, 10, 1))
    save_profile(vDatabaseFile, build_profile("Camille Démo", "", "", "", ""))

    vReport = build_monthly_report(vDatabaseFile, date(2026, 10, 1))

    assert vReport["title"] == "Démarches d'octobre 2026"
    assert vReport["period"] == "Du 01/10/2026 au 31/10/2026"
    assert vReport["name"] == "Camille Démo"
    assert dict(vReport["counts"]) == {
        "Candidature envoyée": 1,
        "Candidature spontanée": 1,
        "Relance": 0,
        "Entretien": 0,
        "Réponse reçue": 0,
    }
    vDecember = build_monthly_report(vDatabaseFile, date(2026, 12, 1))

    assert vDecember["title"] == "Démarches de décembre 2026"
    assert vDecember["period"] == "Du 01/12/2026 au 31/12/2026"


def test_parse_month():
    """Vérifie la lecture du mois choisi dans le formulaire."""

    assert parse_month("2026-11") == date(2026, 11, 1)
    assert parse_month("") is None
    assert parse_month("novembre") is None
