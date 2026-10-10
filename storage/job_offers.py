"""Enregistrement et lecture des offres d'emploi en base"""

import json
from datetime import datetime

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from storage.database import connect_database
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


def get_offers(pDatabaseFile):
    """Retourne les offres enregistrées, des plus récentes aux plus anciennes."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vOffers = pd.read_sql_query(
            "SELECT * FROM job_offer ORDER BY first_seen_at DESC",
            vConnection,
        )

    finally:
        vConnection.close()

    rOffers = vOffers

    return rOffers
