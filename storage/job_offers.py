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

    # first_seen_at n'est pas mis à jour : il garde la date de découverte. Les
    # noms de colonnes viennent de JOB_COLUMNS, les valeurs passent en paramètres.
    rQuery = (
        f"INSERT INTO job_offer ({', '.join(vColumns)}) "  # nosec B608
        f"VALUES ({vPlaceholders}) "
        f"ON CONFLICT(source, source_id) DO UPDATE SET {vUpdates} "
        "RETURNING first_seen_at"
    )

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

# Offre probablement expirée : lien vérifié comme retiré, date limite passée, ou
# ni revue ni vérifiée disponible depuis le délai d'expiration. Une vérification
# réussie compte comme une apparition récente.
# COALESCE évite les valeurs NULL : en SQL, une comparaison avec NULL n'est ni
# vraie ni fausse, et NOT(NULL) masquerait aussi les offres disponibles.
EXPIRED_CONDITION = (
    "(COALESCE(o.availability, '') = 'expired'"
    " OR COALESCE(o.expires_at, '9999') < ?"
    " OR MAX(o.last_seen_at, CASE WHEN o.availability = 'available'"
    " THEN COALESCE(o.availability_checked_at, '') ELSE '' END) < ?)"
)

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
    pMaxNetSalary=None,
    pPublishedSince=None,
    pHasSalary=False,
    pKeys=None,
    pAvailability=None,
    pNow=None,
    pExpiredBefore=None,
    pFingerprint=None,
    pExcludedCompanies=None,
    pPreferredCompanies=None,
):
    """Construit les conditions SQL et leurs paramètres à partir des filtres.

    Les colonnes sont préfixées : o pour l'offre, a pour son suivi. pKeys
    restreint le résultat à une liste de couples (source, identifiant).
    """

    # Chaque valeur passe par un paramètre « ? », jamais par concaténation : une
    # saisie de l'utilisateur ne peut pas modifier la requête (injection SQL).
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

    # Une offre sans maximum est comparée sur son minimum, et inversement : une
    # fourchette partielle reste prise en compte par les filtres de salaire.
    if pMinNetSalary is not None:
        vConditions.append(
            "COALESCE(o.salary_net_monthly_max, o.salary_net_monthly_min) >= ?"
        )
        vParams.append(pMinNetSalary)

    if pMaxNetSalary is not None:
        vConditions.append(
            "COALESCE(o.salary_net_monthly_min, o.salary_net_monthly_max) <= ?"
        )
        vParams.append(pMaxNetSalary)

    if pHasSalary:
        vConditions.append(
            "COALESCE(o.salary_net_monthly_min, o.salary_net_monthly_max) IS NOT NULL"
        )

    # Sans date de publication fournie par la source, la découverte fait foi.
    if pPublishedSince is not None:
        vConditions.append("COALESCE(o.published_at, o.first_seen_at) >= ?")
        vParams.append(pPublishedSince.date().isoformat())

    # Une liste vide doit ne rien renvoyer : la condition « 0 » est toujours fausse,
    # alors que l'absence de condition renverrait toutes les offres.
    if pKeys is not None:
        if pKeys:
            vConditions.append(
                "(o.source, o.source_id) IN (VALUES "
                + ", ".join("(?, ?)" for _ in pKeys)
                + ")"
            )
            vParams += [str(vValue) for vKey in pKeys for vValue in vKey]
        else:
            vConditions.append("0")

    # pAvailability : available masque les offres probablement expirées, expired
    # ne montre qu'elles ; pNow et pExpiredBefore en fixent les dates.
    if pAvailability in ("available", "expired"):
        vCondition = EXPIRED_CONDITION

        if pAvailability == "available":
            vCondition = f"NOT {EXPIRED_CONDITION}"

        vConditions.append(vCondition)
        vParams += [pNow.isoformat(), pExpiredBefore.isoformat()]

    # Toutes les annonces d'une même offre, pour les comparer sur sa fiche
    if pFingerprint is not None:
        vConditions.append("o.fingerprint = ?")
        vParams.append(pFingerprint)

    # L'empreinte « titre|entreprise|ville » contient le nom normalisé de
    # l'entreprise, sans « | » ni joker LIKE : il est cherché entre ses séparateurs.
    if pExcludedCompanies:
        vConditions.append(
            "(o.fingerprint IS NULL OR NOT ("
            + " OR ".join("o.fingerprint LIKE ?" for _ in pExcludedCompanies)
            + "))"
        )
        vParams += [f"%|{vCompany}|%" for vCompany in pExcludedCompanies]

    if pPreferredCompanies is not None:
        vConditions.append(
            "("
            + (" OR ".join("o.fingerprint LIKE ?" for _ in pPreferredCompanies) or "0")
            + ")"
        )
        vParams += [f"%|{vCompany}|%" for vCompany in pPreferredCompanies]

    if pSeenSince is not None:
        vConditions.append("o.first_seen_at >= ?")
        vParams.append(pSeenSince.isoformat())

    # Les colonnes a.* viennent de la jointure gauche : une offre sans suivi a un
    # statut NULL, d'où le test explicite pour masquer les offres ignorées.
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


# Colonnes dont le taux de remplissage est mesuré par l'analyse de qualité ;
# la liste blanche protège la requête construite à partir de ces noms.
QUALITY_COLUMNS = (
    "title",
    "company",
    "location",
    "contract",
    "salary_net_monthly_min",
    "remote",
    "skills",
    "experience_level",
    "published_at",
    "description",
)


def count_filled_fields(pDatabaseFile):
    """Compte, par source, les offres et les valeurs renseignées de chaque colonne."""

    # Une valeur vide ou composée d'espaces compte comme absente.
    vCounts = ", ".join(
        f"SUM(CASE WHEN TRIM(COALESCE({vColumn}, '')) != '' THEN 1 ELSE 0 END)"
        for vColumn in QUALITY_COLUMNS
    )

    vConnection = connect_database(pDatabaseFile)

    try:
        # Colonnes issues de la liste blanche QUALITY_COLUMNS.
        vRows = vConnection.execute(
            f"SELECT source, COUNT(*), {vCounts} FROM job_offer "  # nosec B608
            "GROUP BY source ORDER BY COUNT(*) DESC, source"
        ).fetchall()

    finally:
        vConnection.close()

    rCounts = [
        (vRow[0], vRow[1], dict(zip(QUALITY_COLUMNS, vRow[2:]))) for vRow in vRows
    ]

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
        # Colonnes issues de la constante NET_SALARY_COLUMNS.
        vConnection.executemany(
            "UPDATE job_offer SET "  # nosec B608
            + ", ".join(f"{vColumn} = ?" for vColumn in NET_SALARY_COLUMNS)
            + " WHERE source = ? AND source_id = ?",
            vRows,
        )

        vConnection.commit()

    finally:
        vConnection.close()

    rCount = len(vRows)

    return rCount


def count_offers_by_contract(pDatabaseFile):
    """Compte les offres en base par type de contrat, du plus fréquent au moins fréquent."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rCounts = vConnection.execute("""
            SELECT contract, COUNT(*) AS offer_count
            FROM job_offer
            GROUP BY contract
            ORDER BY offer_count DESC
            """).fetchall()

    finally:
        vConnection.close()

    return rCounts


def set_availability(pDatabaseFile, pSource, pSourceId, pAvailability, pNow):
    """Enregistre le résultat de la vérification du lien d'une offre."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            "UPDATE job_offer SET availability = ?, availability_checked_at = ?"
            " WHERE source = ? AND source_id = ?",
            (pAvailability, pNow.isoformat(), pSource, str(pSourceId)),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Disponibilité vérifiée : %s %s, %s", pSource, pSourceId, pAvailability)


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


def get_fingerprints(pDatabaseFile):
    """Retourne les empreintes des offres en base, pour écarter les doublons."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT DISTINCT fingerprint FROM job_offer WHERE fingerprint IS NOT NULL"
        ).fetchall()

    finally:
        vConnection.close()

    rFingerprints = {vRow[0] for vRow in vRows}

    return rFingerprints


def count_offers_by_skill(pDatabaseFile):
    """Compte les offres en base qui citent chaque compétence."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT skills FROM job_offer WHERE skills IS NOT NULL"
        ).fetchall()

    finally:
        vConnection.close()

    rCounts = {}

    for (vSkills,) in vRows:
        try:
            vList = json.loads(vSkills)

        except ValueError:
            continue

        for vSkill in set(vList if isinstance(vList, list) else []):
            rCounts[vSkill] = rCounts.get(vSkill, 0) + 1

    return rCounts
