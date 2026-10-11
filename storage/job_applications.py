"""Gestion du suivi des candidatures et des relances"""

import sqlite3
from datetime import datetime, timedelta

from config import FOLLOW_UP_DAYS
from storage.database import connect_database, count_by_day
from storage.job_offers import FOLLOW_UP_STATUSES
from utils.logger import get_logger

logger = get_logger(__name__)

# Statuts stockés en base ; leurs libellés affichés sont dans job/presentation.py
# (STATUS_LABELS). Un nouveau statut doit être ajouté aux deux endroits.
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


def update_application_status(
    pDatabaseFile, pSource, pSourceId, pStatus, pNow=None, pFollowUpDays=FOLLOW_UP_DAYS
):
    """Modifie le statut d'une candidature, notes et dates déjà saisies conservées.

    Au passage au statut APPLIED, la date de candidature et la relance par défaut
    sont fixées si elles manquent, comme dans save_application.
    """

    if pStatus not in APPLICATION_STATUSES:
        raise ValueError("Statut de candidature invalide.")

    vNow = pNow or datetime.now()
    vApplied = pStatus == "APPLIED"

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            UPDATE job_application
            SET status = ?,
                applied_at = COALESCE(applied_at, ?),
                follow_up_date = COALESCE(follow_up_date, ?)
            WHERE source = ?
            AND source_id = ?
            """,
            (
                pStatus,
                vNow.isoformat() if vApplied else None,
                (
                    (vNow + timedelta(days=pFollowUpDays)).isoformat()
                    if vApplied
                    else None
                ),
                pSource,
                str(pSourceId),
            ),
        )

        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Statut modifié : %s %s, statut %s", pSource, pSourceId, pStatus)


def record_follow_up(
    pDatabaseFile,
    pSource,
    pSourceId,
    pFollowUpDate=None,
    pFollowUpDays=FOLLOW_UP_DAYS,
):
    """Enregistre une relance et programme la suivante."""

    vFollowUpAt = pFollowUpDate

    if vFollowUpAt is None:
        vFollowUpAt = datetime.now()

    vNextFollowUpAt = vFollowUpAt + timedelta(days=pFollowUpDays)

    vConnection = connect_database(pDatabaseFile)

    try:
        # La relance est ajoutée au journal job_follow_up, qui alimente le graphique
        # jour par jour, puis la candidature reçoit la date de la relance suivante :
        # les deux écritures sont validées ensemble par le même commit.
        vConnection.execute(
            """
            INSERT INTO job_follow_up (source, source_id, followed_up_at)
            VALUES (?, ?, ?)
            """,
            (pSource, str(pSourceId), vFollowUpAt.isoformat()),
        )

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
    pFollowUpDays=FOLLOW_UP_DAYS,
):
    """Crée ou met à jour le suivi d'une offre depuis le tableau de bord.

    La date de candidature est fixée au premier passage au statut APPLIED.
    Une candidature envoyée sans date de relance en reçoit une par défaut.
    """

    if pStatus not in APPLICATION_STATUSES:
        raise ValueError("Statut de candidature invalide.")

    vNow = pNow or datetime.now()

    # Les dates sont stockées au format ISO : comparées comme du texte, elles
    # restent triées dans l'ordre chronologique.
    vAppliedAt = vNow.isoformat() if pStatus == "APPLIED" else None

    vFollowUpDate = pFollowUpDate

    if vFollowUpDate is None and pStatus == "APPLIED":
        vFollowUpDate = vNow + timedelta(days=pFollowUpDays)

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
                -- COALESCE garde la première date de candidature : repasser une offre au
                -- statut APPLIED ne la remplace pas.
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


# Statuts d'une candidature envoyée, qu'elle soit en cours ou terminée
SENT_STATUSES = ("APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED")


def get_company_applications(pDatabaseFile, pCompanyKey, pExcludedKey=None):
    """Retourne les candidatures envoyées à une entreprise, la plus récente en tête.

    pCompanyKey est le nom normalisé de l'entreprise (job.fingerprint) ;
    pExcludedKey écarte l'offre consultée, sous la forme (source, identifiant).
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        # Le nom normalisé ne contient ni « | » ni joker LIKE.
        vRows = vConnection.execute(
            f"""
            SELECT o.source, o.source_id, o.title, o.company, a.status, a.applied_at
            FROM job_application a
            JOIN job_offer o ON o.source = a.source AND o.source_id = a.source_id
            WHERE o.fingerprint LIKE ?
                AND a.status IN ({", ".join("?" for _ in SENT_STATUSES)})
            ORDER BY COALESCE(a.applied_at, '') DESC
            """,  # nosec B608
            (f"%|{pCompanyKey}|%", *SENT_STATUSES),
        ).fetchall()

    finally:
        vConnection.close()

    rApplications = [
        dict(vRow)
        for vRow in vRows
        if (vRow["source"], vRow["source_id"]) != pExcludedKey
    ]

    return rApplications


def count_applications_by_day(pDatabaseFile, pDays, pNow=None):
    """Compte les candidatures envoyées chaque jour, jours vides compris."""

    rCounts = count_by_day(pDatabaseFile, "job_application", "applied_at", pDays, pNow)

    return rCounts


def count_follow_ups_by_day(pDatabaseFile, pDays, pNow=None):
    """Compte les relances effectuées chaque jour, jours vides compris."""

    rCounts = count_by_day(
        pDatabaseFile, "job_follow_up", "followed_up_at", pDays, pNow
    )

    return rCounts


def get_upcoming_follow_ups(pDatabaseFile, pLimit):
    """Retourne les prochaines relances prévues, les plus proches en premier."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        # Seuls des « ? » sont insérés : les statuts passent en paramètres.
        vRows = vConnection.execute(
            "SELECT a.source, a.source_id, a.status, a.follow_up_date,"
            " o.title, o.company"
            " FROM job_application a"
            " JOIN job_offer o ON o.source = a.source AND o.source_id = a.source_id"
            " WHERE a.follow_up_date IS NOT NULL"
            f" AND a.status IN ({', '.join('?' for _ in FOLLOW_UP_STATUSES)})"  # nosec B608
            " ORDER BY a.follow_up_date LIMIT ?",
            (*FOLLOW_UP_STATUSES, pLimit),
        ).fetchall()

    finally:
        vConnection.close()

    rFollowUps = [dict(vRow) for vRow in vRows]

    return rFollowUps


def get_applications_with_offers(pDatabaseFile, pStatuses):
    """Retourne les candidatures des statuts donnés avec leur offre, récentes en tête."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        # Les marqueurs « ? » sont générés à partir du nombre de statuts.
        vRows = vConnection.execute(
            f"""
            SELECT
                o.source, o.source_id, o.title, o.company, o.location, o.contract,
                o.url, a.status, a.applied_at, a.follow_up_date, a.follow_up_count
            FROM job_application a
            JOIN job_offer o ON o.source = a.source AND o.source_id = a.source_id
            WHERE a.status IN ({", ".join("?" for _ in pStatuses)})
            ORDER BY COALESCE(a.applied_at, o.first_seen_at) DESC
            """,  # nosec B608
            tuple(pStatuses),
        ).fetchall()

    finally:
        vConnection.close()

    rApplications = [dict(vRow) for vRow in vRows]

    return rApplications
