"""Tests du suivi des candidatures"""

from datetime import datetime
from pathlib import Path

import pytest

from storage.database import initialize_database
from storage.job_applications import (
    count_applications_by_day,
    count_follow_ups_by_day,
    create_application,
    delete_application,
    get_application,
    get_follow_ups,
    record_follow_up,
    save_application,
    update_application_status,
)


def test_create_application(tmp_path):
    """Vérifie qu'une candidature peut être créée."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    vAppliedAt = datetime(2026, 10, 1, 10, 0, 0)

    vFollowUpDate = datetime(2026, 10, 8, 10, 0, 0)

    create_application(
        vDatabaseFile,
        "lever",
        "123",
        pStatus="APPLIED",
        pAppliedAt=vAppliedAt,
        pFollowUpDate=vFollowUpDate,
        pNotes="Candidature envoyée",
    )

    import sqlite3

    vConnection = sqlite3.connect(vDatabaseFile)

    try:
        vRow = vConnection.execute(
            """
            SELECT
                source,
                source_id,
                status,
                applied_at,
                follow_up_date,
                follow_up_count,
                notes
            FROM job_application
            WHERE source = ?
            AND source_id = ?
            """,
            ("lever", "123"),
        ).fetchone()
    finally:
        vConnection.close()

    assert vRow[0] == "lever"
    assert vRow[1] == "123"
    assert vRow[2] == "APPLIED"
    assert vRow[3] == vAppliedAt.isoformat()
    assert vRow[4] == vFollowUpDate.isoformat()
    assert vRow[5] == 0
    assert vRow[6] == "Candidature envoyée"


def test_update_application_status(tmp_path):
    """Vérifie que le statut d'une candidature peut être modifié."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    create_application(vDatabaseFile, "lever", "123")

    update_application_status(vDatabaseFile, "lever", "123", "INTERVIEW")

    import sqlite3

    vConnection = sqlite3.connect(vDatabaseFile)

    try:
        vRow = vConnection.execute(
            """
            SELECT status
            FROM job_application
            WHERE source = ?
            AND source_id = ?
            """,
            ("lever", "123"),
        ).fetchone()
    finally:
        vConnection.close()

    assert vRow[0] == "INTERVIEW"


def test_record_follow_up(tmp_path):
    """Vérifie qu'une relance incrémente le compteur
    et mémorise la date de dernière relance.
    """

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    create_application(vDatabaseFile, "lever", "123", pStatus="APPLIED")

    vFollowUpDate = datetime(2026, 10, 8, 10, 0, 0)

    record_follow_up(vDatabaseFile, "lever", "123", pFollowUpDate=vFollowUpDate)

    import sqlite3

    vConnection = sqlite3.connect(vDatabaseFile)

    try:
        vRow = vConnection.execute(
            """
            SELECT
                follow_up_count,
                last_follow_up_at,
                follow_up_date
            FROM job_application
            WHERE source = ?
            AND source_id = ?
            """,
            ("lever", "123"),
        ).fetchone()
    finally:
        vConnection.close()

    assert vRow[0] == 1
    assert vRow[1] == vFollowUpDate.isoformat()
    assert vRow[2] == datetime(2026, 10, 15, 10, 0, 0).isoformat()


def test_record_multiple_follow_ups(tmp_path):
    """Vérifie que plusieurs relances sont correctement comptabilisées."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    create_application(vDatabaseFile, "lever", "123", pStatus="APPLIED")

    vFirstFollowUp = datetime(2026, 10, 8, 10, 0, 0)

    vSecondFollowUp = datetime(2026, 10, 15, 10, 0, 0)

    record_follow_up(vDatabaseFile, "lever", "123", pFollowUpDate=vFirstFollowUp)

    record_follow_up(vDatabaseFile, "lever", "123", pFollowUpDate=vSecondFollowUp)

    import sqlite3

    vConnection = sqlite3.connect(vDatabaseFile)

    try:
        vRow = vConnection.execute(
            """
            SELECT
                follow_up_count,
                last_follow_up_at
            FROM job_application
            WHERE source = ?
            AND source_id = ?
            """,
            ("lever", "123"),
        ).fetchone()
    finally:
        vConnection.close()

    assert vRow[0] == 2
    assert vRow[1] == vSecondFollowUp.isoformat()


def test_get_follow_ups(tmp_path):
    """Vérifie que les relances arrivées à échéance sont récupérées."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    vDueDate = datetime(2026, 10, 5, 10, 0, 0)

    vFutureDate = datetime(2026, 10, 15, 10, 0, 0)

    create_application(
        vDatabaseFile, "lever", "123", pStatus="APPLIED", pFollowUpDate=vDueDate
    )

    create_application(
        vDatabaseFile,
        "greenhouse",
        "456",
        pStatus="INTERVIEW",
        pFollowUpDate=vFutureDate,
    )

    vFollowUps = get_follow_ups(vDatabaseFile, pDate=datetime(2026, 10, 10, 10, 0, 0))

    assert len(vFollowUps) == 1
    assert vFollowUps[0][0] == "lever"
    assert vFollowUps[0][1] == "123"


def test_get_follow_ups_only_returns_active_statuses(tmp_path):
    """Vérifie qu'une candidature refusée n'est plus proposée
    dans les relances à effectuer.
    """

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    vFollowUpDate = datetime(2026, 10, 5, 10, 0, 0)

    create_application(
        vDatabaseFile, "lever", "123", pStatus="REJECTED", pFollowUpDate=vFollowUpDate
    )

    vFollowUps = get_follow_ups(vDatabaseFile, pDate=datetime(2026, 10, 10, 10, 0, 0))

    assert len(vFollowUps) == 0


def test_invalid_application_status(tmp_path):
    """Vérifie qu'un statut de candidature inconnu est refusé."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    with pytest.raises(ValueError):
        create_application(vDatabaseFile, "lever", "123", pStatus="UNKNOWN")


def test_same_application_is_not_duplicated(tmp_path):
    """Vérifie qu'une même candidature reste unique pour une source
    et un identifiant d'offre.
    """

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    create_application(vDatabaseFile, "lever", "123", pStatus="APPLIED")

    create_application(vDatabaseFile, "lever", "123", pStatus="INTERVIEW")

    import sqlite3

    vConnection = sqlite3.connect(vDatabaseFile)

    try:
        vRows = vConnection.execute(
            """
            SELECT
                source,
                source_id,
                status
            FROM job_application
            WHERE source = ?
            AND source_id = ?
            """,
            ("lever", "123"),
        ).fetchall()
    finally:
        vConnection.close()

    assert len(vRows) == 1
    assert vRows[0][2] == "INTERVIEW"


def test_save_application_sets_applied_date_and_default_follow_up(tmp_path):
    """Vérifie la date de candidature et la relance par défaut."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    vNow = datetime(2026, 10, 10, 9, 0, 0)

    save_application(vDatabaseFile, "adzuna", "1", "APPLIED", pNow=vNow)

    rApplication = get_application(vDatabaseFile, "adzuna", "1")

    assert rApplication["status"] == "APPLIED"
    assert rApplication["applied_at"] == vNow.isoformat()
    assert rApplication["follow_up_date"] == "2026-10-17T09:00:00"


def test_save_application_keeps_first_applied_date(tmp_path):
    """Vérifie que la date de candidature initiale est conservée."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    save_application(
        vDatabaseFile, "adzuna", "1", "APPLIED", pNow=datetime(2026, 10, 1)
    )
    save_application(
        vDatabaseFile,
        "adzuna",
        "1",
        "INTERVIEW",
        pNotes="Entretien technique",
        pNow=datetime(2026, 10, 9),
    )

    rApplication = get_application(vDatabaseFile, "adzuna", "1")

    assert rApplication["status"] == "INTERVIEW"
    assert rApplication["applied_at"] == datetime(2026, 10, 1).isoformat()
    assert rApplication["notes"] == "Entretien technique"


def test_save_application_without_follow_up_for_other_status(tmp_path):
    """Vérifie qu'une offre simplement intéressante n'a pas de relance."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    save_application(vDatabaseFile, "adzuna", "1", "INTERESTED")

    rApplication = get_application(vDatabaseFile, "adzuna", "1")

    assert rApplication["follow_up_date"] is None
    assert rApplication["applied_at"] is None


def test_delete_application(tmp_path):
    """Vérifie la suppression du suivi d'une offre."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    save_application(vDatabaseFile, "adzuna", "1", "IGNORED")

    delete_application(vDatabaseFile, "adzuna", "1")

    assert get_application(vDatabaseFile, "adzuna", "1") is None


def test_follow_ups_and_applications_are_counted_by_day(tmp_path):
    """Vérifie les décomptes quotidiens de candidatures et de relances."""

    vDatabaseFile = Path(tmp_path) / "scraper.db"

    initialize_database(vDatabaseFile)

    save_application(vDatabaseFile, "lever", "1", "APPLIED", pNow=datetime(2026, 10, 8))
    record_follow_up(vDatabaseFile, "lever", "1", datetime(2026, 10, 9, 10, 0))
    record_follow_up(vDatabaseFile, "lever", "1", datetime(2026, 10, 10, 10, 0))

    vNow = datetime(2026, 10, 10, 12, 0)

    assert [
        vCount for _, vCount in count_applications_by_day(vDatabaseFile, 3, vNow)
    ] == [1, 0, 0]
    assert [
        vCount for _, vCount in count_follow_ups_by_day(vDatabaseFile, 3, vNow)
    ] == [0, 1, 1]


def test_status_alone_keeps_notes_follow_up_and_interview(tmp_path):
    """Vérifie qu'un statut seul garde les champs saisis, et qu'un formulaire les vide."""

    database_file = tmp_path / "scraper.db"
    initialize_database(database_file)

    save_application(
        database_file,
        "adzuna",
        "1",
        "APPLIED",
        pFollowUpDate=datetime(2026, 11, 2),
        pNotes="Contact : la RH",
        pInterviewAt=datetime(2026, 11, 5, 10),
    )
    save_application(database_file, "adzuna", "1", "INTERVIEW")
    vKept = get_application(database_file, "adzuna", "1")

    save_application(
        database_file,
        "adzuna",
        "1",
        "INTERVIEW",
        pFollowUpDate=None,
        pNotes="",
        pInterviewAt=None,
    )
    vCleared = get_application(database_file, "adzuna", "1")

    assert vKept["notes"] == "Contact : la RH"
    assert vKept["follow_up_date"].startswith("2026-11-02")
    assert vKept["interview_at"] == "2026-11-05T10:00"
    assert (vCleared["notes"], vCleared["interview_at"]) == (None, None)
