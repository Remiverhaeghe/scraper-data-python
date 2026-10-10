"""Gestion du suivi des candidatures et des relances"""

import sqlite3
from datetime import datetime, timedelta

from config import FOLLOW_UP_DAYS
from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

APPLICATION_STATUSES = (
    "IGNORED",
    "INTERESTED",
    "APPLIED",
    "INTERVIEW",
    "REJECTED",
    "ACCEPTED",
    "CLOSED",
)


def create_application(
    pDatabaseFile,
    pSource,
    pSourceId,
    pStatus="APPLIED",
    pAppliedAt=None,
    pFollowUpDate=None,
    pNotes=None,
):
    """Crée ou remplace le suivi d'une candidature."""

    if pStatus not in APPLICATION_STATUSES:
        raise ValueError("Statut de candidature invalide.")

    vConnection = connect_database(pDatabaseFile)

    try:
        vAppliedAt = pAppliedAt.isoformat() if pAppliedAt is not None else None

        vFollowUpDate = pFollowUpDate.isoformat() if pFollowUpDate is not None else None

        vConnection.execute(
            """
            INSERT INTO job_application (
                source,
                source_id,
                status,
                applied_at,
                follow_up_date,
                follow_up_count,
                last_follow_up_at,
                notes
            )
            VALUES (?, ?, ?, ?, ?, 0, NULL, ?)
            ON CONFLICT(source, source_id)
            DO UPDATE SET
                status = excluded.status,
                applied_at = excluded.applied_at,
                follow_up_date = excluded.follow_up_date,
                notes = excluded.notes
            """,
            (pSource, str(pSourceId), pStatus, vAppliedAt, vFollowUpDate, pNotes),
        )

        vConnection.commit()

    finally:
        vConnection.close()


def update_application_status(pDatabaseFile, pSource, pSourceId, pStatus):
    """Modifie le statut d'une candidature."""

    if pStatus not in APPLICATION_STATUSES:
        raise ValueError("Statut de candidature invalide.")

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            UPDATE job_application
            SET status = ?
            WHERE source = ?
            AND source_id = ?
            """,
            (pStatus, pSource, str(pSourceId)),
        )

        vConnection.commit()

    finally:
        vConnection.close()


def record_follow_up(pDatabaseFile, pSource, pSourceId, pFollowUpDate=None):
    """Enregistre une relance et programme la suivante."""

    vFollowUpAt = pFollowUpDate

    if vFollowUpAt is None:
        vFollowUpAt = datetime.now()

    vNextFollowUpAt = vFollowUpAt + timedelta(days=FOLLOW_UP_DAYS)

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            UPDATE job_application
            SET
                follow_up_count = follow_up_count + 1,
                last_follow_up_at = ?,
                follow_up_date = ?
            WHERE source = ?
            AND source_id = ?
            """,
            (
                vFollowUpAt.isoformat(),
                vNextFollowUpAt.isoformat(),
                pSource,
                str(pSourceId),
            ),
        )

        vConnection.commit()

    finally:
        vConnection.close()


def get_follow_ups(pDatabaseFile, pDate=None):
    """Récupère les candidatures dont une relance est nécessaire."""

    vDate = pDate if pDate is not None else datetime.now()

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            """
            SELECT
                source,
                source_id,
                status,
                applied_at,
                follow_up_date,
                follow_up_count,
                last_follow_up_at,
                notes
            FROM job_application
            WHERE follow_up_date IS NOT NULL
            AND follow_up_date <= ?
            AND status IN ('APPLIED', 'INTERVIEW')
            ORDER BY follow_up_date ASC
            """,
            (vDate.isoformat(),),
        )

        rApplications = vCursor.fetchall()

    finally:
        vConnection.close()

    return rApplications


def save_application(
    pDatabaseFile,
    pSource,
    pSourceId,
    pStatus,
    pFollowUpDate=None,
    pNotes=None,
    pNow=None,
):
    """Crée ou met à jour le suivi d'une offre depuis le tableau de bord.

    La date de candidature est fixée au premier passage au statut APPLIED.
    Une candidature envoyée sans date de relance en reçoit une par défaut.
    """

    if pStatus not in APPLICATION_STATUSES:
        raise ValueError("Statut de candidature invalide.")

    vNow = pNow or datetime.now()

    vAppliedAt = vNow.isoformat() if pStatus == "APPLIED" else None

    vFollowUpDate = pFollowUpDate

    if vFollowUpDate is None and pStatus == "APPLIED":
        vFollowUpDate = vNow + timedelta(days=FOLLOW_UP_DAYS)

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO job_application (
                source,
                source_id,
                status,
                applied_at,
                follow_up_date,
                follow_up_count,
                notes
            )
            VALUES (?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(source, source_id)
            DO UPDATE SET
                status = excluded.status,
                applied_at = COALESCE(job_application.applied_at, excluded.applied_at),
                follow_up_date = excluded.follow_up_date,
                notes = excluded.notes
            """,
            (
                pSource,
                str(pSourceId),
                pStatus,
                vAppliedAt,
                vFollowUpDate.isoformat() if vFollowUpDate else None,
                pNotes or None,
            ),
        )

        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Suivi enregistré : %s %s, statut %s", pSource, pSourceId, pStatus)


def delete_application(pDatabaseFile, pSource, pSourceId):
    """Supprime le suivi d'une offre."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            "DELETE FROM job_application WHERE source = ? AND source_id = ?",
            (pSource, str(pSourceId)),
        )

        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Suivi supprimé : %s %s", pSource, pSourceId)


def get_application(pDatabaseFile, pSource, pSourceId):
    """Retourne le suivi d'une offre sous forme de dictionnaire, ou None."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vRow = vConnection.execute(
            "SELECT * FROM job_application WHERE source = ? AND source_id = ?",
            (pSource, str(pSourceId)),
        ).fetchone()

    finally:
        vConnection.close()

    rApplication = dict(vRow) if vRow is not None else None

    return rApplication
