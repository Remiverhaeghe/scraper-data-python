"""Enregistrement et lecture des offres d'emploi en base"""

import json
import sqlite3
from datetime import datetime

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from storage.database import connect_database, count_by_day
from utils.logger import get_logger

logger = get_logger(__name__)

# Colonnes recopiées depuis la source ; les dates de suivi sont gérées à part.
CONTENT_COLUMNS = [
    vColumn
    for vColumn in JOB_COLUMNS
    if vColumn not in ("source", "source_id", "scraped_at", "first_seen_at")
]


def to_sql_value(pValue):
    """Convertit une valeur du DataFrame en valeur acceptée par SQLite."""

    rValue = pValue

    if isinstance(pValue, (list, dict)):
        rValue = json.dumps(pValue, ensure_ascii=False)

    elif pd.isna(pValue):
        rValue = None

    elif isinstance(pValue, datetime):
        rValue = pValue.isoformat()

    return rValue


def build_upsert_query():
    """Construit la requête d'insertion ou de mise à jour d'une offre."""

    vColumns = ["source", "source_id", "first_seen_at", "last_seen_at"]
    vColumns += CONTENT_COLUMNS

    vPlaceholders = ", ".join("?" for _ in vColumns)

    vUpdates = ",\n            ".join(
        f"{vColumn} = excluded.{vColumn}"
        for vColumn in ["last_seen_at"] + CONTENT_COLUMNS
    )

    # first_seen_at n'est pas mis à jour : il garde la date de découverte.
    rQuery = f"""
        INSERT INTO job_offer ({", ".join(vColumns)})
        VALUES ({vPlaceholders})
        ON CONFLICT(source, source_id) DO UPDATE SET
            {vUpdates}
        RETURNING first_seen_at
        """

    return rQuery


def save_offers(pDatabaseFile, pItems, pScrapedAt):
    """Enregistre les offres en base et indique celles qui sont nouvelles.

    Les offres sans source_id ne peuvent pas être suivies
    entre deux exécutions et ne sont pas enregistrées.
    """

    vItems = pItems.copy()

    vItems["scraped_at"] = pScrapedAt
    vItems["first_seen_at"] = None
    vItems["is_new"] = False

    for vColumn in CONTENT_COLUMNS:
        if vColumn not in vItems.columns:
            vItems[vColumn] = None

    vScrapedAt = pScrapedAt.isoformat()
    vQuery = build_upsert_query()
    vNewCount = 0
    vIgnoredCount = 0

    vConnection = connect_database(pDatabaseFile)

    try:
        for vIndex, vJob in zip(vItems.index, vItems.to_dict("records")):

            if pd.isna(vJob["source_id"]):
                vIgnoredCount += 1
                continue

            vValues = [vJob["source"], str(vJob["source_id"]), vScrapedAt, vScrapedAt]
            vValues += [to_sql_value(vJob[vColumn]) for vColumn in CONTENT_COLUMNS]

            vFirstSeenAt = vConnection.execute(vQuery, vValues).fetchone()[0]

            vIsNew = vFirstSeenAt == vScrapedAt

            if vIsNew:
                vNewCount += 1

            vItems.loc[vIndex, "first_seen_at"] = datetime.fromisoformat(vFirstSeenAt)
            vItems.loc[vIndex, "is_new"] = vIsNew

        vConnection.commit()

    except Exception:
        vConnection.rollback()
        logger.exception("Erreur lors de l'enregistrement des offres en base")
        raise

    finally:
        vConnection.close()

    if vIgnoredCount:
        logger.warning("%s offre(s) sans source_id non enregistrée(s)", vIgnoredCount)

    logger.info(
        "%s offre(s) enregistrée(s) en base, dont %s nouvelle(s)",
        len(vItems) - vIgnoredCount,
        vNewCount,
    )

    rItems = vItems

    return rItems


# Statuts pour lesquels une relance reste pertinente
FOLLOW_UP_STATUSES = ("APPLIED", "INTERVIEW")

OFFERS_WITH_APPLICATION = """
        FROM job_offer o
        LEFT JOIN job_application a
            ON a.source = o.source AND a.source_id = o.source_id
"""


def build_offer_conditions(
    pSearch=None,
    pSource=None,
    pContract=None,
    pRemote=False,
    pMinNetSalary=None,
    pSeenSince=None,
    pStatus=None,
    pFollowUpBefore=None,
    pHideIgnored=False,
):
    """Construit les conditions SQL et leurs paramètres à partir des filtres.

    Les colonnes sont préfixées : o pour l'offre, a pour son suivi.
    """

    vConditions = []
    vParams = []

    if pSearch:
        vConditions.append(
            "(o.title LIKE ? OR o.company LIKE ? OR o.location LIKE ?"
            " OR o.description LIKE ?)"
        )
        vParams += [f"%{pSearch}%"] * 4

    if pSource:
        vConditions.append("o.source = ?")
        vParams.append(pSource)

    if pContract:
        vConditions.append("o.contract = ?")
        vParams.append(pContract)

    if pRemote:
        vConditions.append("o.remote = 1")

    if pMinNetSalary is not None:
        vConditions.append(
            "COALESCE(o.salary_net_monthly_max, o.salary_net_monthly_min) >= ?"
        )
        vParams.append(pMinNetSalary)

    if pSeenSince is not None:
        vConditions.append("o.first_seen_at >= ?")
        vParams.append(pSeenSince.isoformat())

    if pStatus:
        vConditions.append("a.status = ?")
        vParams.append(pStatus)

    elif pHideIgnored:
        vConditions.append("(a.status IS NULL OR a.status != 'IGNORED')")

    if pFollowUpBefore is not None:
        vConditions.append(
            f"a.status IN ({', '.join('?' for _ in FOLLOW_UP_STATUSES)})"
            " AND a.follow_up_date <= ?"
        )
        vParams += [*FOLLOW_UP_STATUSES, pFollowUpBefore.isoformat()]

    rConditions = (vConditions, vParams)

    return rConditions


def get_offers(pDatabaseFile, pLimit=None, **pFilters):
    """Retourne les offres filtrées avec leur suivi, des plus récentes aux plus
    anciennes.
    """

    vConditions, vParams = build_offer_conditions(**pFilters)

    vQuery = f"""
        SELECT
            o.*,
            a.status AS application_status,
            a.applied_at,
            a.follow_up_date
        {OFFERS_WITH_APPLICATION}
        """

    if vConditions:
        vQuery += " WHERE " + " AND ".join(vConditions)

    vQuery += " ORDER BY o.first_seen_at DESC, o.published_at DESC"

    if pLimit is not None:
        vQuery += " LIMIT ?"
        vParams.append(pLimit)

    vConnection = connect_database(pDatabaseFile)

    try:
        vOffers = pd.read_sql_query(vQuery, vConnection, params=vParams)

    finally:
        vConnection.close()

    rOffers = vOffers

    return rOffers


def count_offers(pDatabaseFile, **pFilters):
    """Compte les offres correspondant aux mêmes filtres que get_offers."""

    vConditions, vParams = build_offer_conditions(**pFilters)

    vQuery = f"SELECT COUNT(*) {OFFERS_WITH_APPLICATION}"

    if vConditions:
        vQuery += " WHERE " + " AND ".join(vConditions)

    vConnection = connect_database(pDatabaseFile)

    try:
        rCount = vConnection.execute(vQuery, vParams).fetchone()[0]

    finally:
        vConnection.close()

    return rCount


def count_new_offers_by_day(pDatabaseFile, pDays, pNow=None):
    """Compte les offres découvertes chaque jour, jours sans offre compris."""

    rCounts = count_by_day(pDatabaseFile, "job_offer", "first_seen_at", pDays, pNow)

    return rCounts


def count_offers_by_source(pDatabaseFile):
    """Compte les offres en base par source, de la plus fournie à la moins fournie."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rCounts = vConnection.execute("""
            SELECT source, COUNT(*) AS offer_count
            FROM job_offer
            GROUP BY source
            ORDER BY offer_count DESC, source
            """).fetchall()

    finally:
        vConnection.close()

    return rCounts


# Colonnes de salaire net recalculées lorsque les réglages de calcul changent
NET_SALARY_COLUMNS = (
    "salary_net_monthly_min",
    "salary_net_monthly_max",
    "salary_net_after_tax_monthly_min",
    "salary_net_after_tax_monthly_max",
)


def get_salaries(pDatabaseFile):
    """Retourne le salaire brut de chaque offre, pour recalculer son net."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rSalaries = pd.read_sql_query(
            """
            SELECT source, source_id, salary_min, salary_max,
                   salary_period, salary_currency
            FROM job_offer
            """,
            vConnection,
        )

    finally:
        vConnection.close()

    return rSalaries


def update_net_salaries(pDatabaseFile, pSalaries):
    """Enregistre les salaires nets recalculés ; retourne le nombre d'offres mises à jour."""

    vRows = [
        (
            *(to_sql_value(vRow[vColumn]) for vColumn in NET_SALARY_COLUMNS),
            vRow["source"],
            vRow["source_id"],
        )
        for _, vRow in pSalaries.iterrows()
    ]

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            f"""
            UPDATE job_offer
            SET {", ".join(f"{vColumn} = ?" for vColumn in NET_SALARY_COLUMNS)}
            WHERE source = ? AND source_id = ?
            """,
            vRows,
        )

        vConnection.commit()

    finally:
        vConnection.close()

    rCount = len(vRows)

    return rCount


def get_offer(pDatabaseFile, pSource, pSourceId):
    """Retourne une offre sous forme de dictionnaire, ou None si elle n'existe pas."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vRow = vConnection.execute(
            "SELECT * FROM job_offer WHERE source = ? AND source_id = ?",
            (pSource, str(pSourceId)),
        ).fetchone()

    finally:
        vConnection.close()

    rOffer = dict(vRow) if vRow is not None else None

    return rOffer
