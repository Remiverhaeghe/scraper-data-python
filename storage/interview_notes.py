"""Persistance du journal d'entretien : questions posées et impressions"""

import sqlite3

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def add_interview_note(
    pDatabaseFile, pSource, pSourceId, pInterviewedAt, pQuestions, pImpressions
):
    """Ajoute une entrée au journal d'une offre ; retourne son identifiant."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            """
            INSERT INTO interview_note (
                source, source_id, interviewed_at, questions, impressions
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                pSource,
                str(pSourceId),
                pInterviewedAt.isoformat(timespec="minutes"),
                pQuestions,
                pImpressions,
            ),
        )
        vConnection.commit()

        rNoteId = vCursor.lastrowid

    finally:
        vConnection.close()

    logger.info("Journal d'entretien complété : %s %s", pSource, pSourceId)

    return rNoteId


def get_interview_notes(pDatabaseFile, pSource=None, pSourceId=None):
    """Retourne les entrées du journal, d'une offre ou de toutes, récentes en tête."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vQuery = """
            SELECT n.id, n.source, n.source_id, n.interviewed_at, n.questions,
                n.impressions, o.title, o.company
            FROM interview_note n
            LEFT JOIN job_offer o ON o.source = n.source AND o.source_id = n.source_id
        """
        vParameters = ()

        if pSource is not None:
            vQuery += " WHERE n.source = ? AND n.source_id = ?"
            vParameters = (pSource, str(pSourceId))

        vRows = vConnection.execute(
            vQuery + " ORDER BY n.interviewed_at DESC, n.id DESC", vParameters
        ).fetchall()

    finally:
        vConnection.close()

    rNotes = [dict(vRow) for vRow in vRows]

    return rNotes


def delete_interview_note(pDatabaseFile, pNoteId):
    """Supprime une entrée du journal."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute("DELETE FROM interview_note WHERE id = ?", (pNoteId,))
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Entrée du journal d'entretien supprimée : %s", pNoteId)
