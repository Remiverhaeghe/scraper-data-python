"""Statistiques, contrôles de qualité et empreintes calculés sur les offres en base"""

import json
import sqlite3

from storage.database import connect_database, count_by_day


def count_empty_fields(pDatabaseFile, pSince):
    """Compte, par source, les offres découvertes depuis pSince et celles dont le
    titre, le lieu (hors télétravail) ou l'entreprise est vide.
    """

    vConnection = connect_database(pDatabaseFile)
    vConnection.row_factory = sqlite3.Row

    try:
        vRows = vConnection.execute(
            """
            SELECT source, COUNT(*) AS total,
                SUM(COALESCE(title, '') = '') AS title,
                SUM(COALESCE(location, '') = '' AND COALESCE(remote, 0) = 0)
                    AS location,
                SUM(COALESCE(company, '') = '') AS company
            FROM job_offer
            WHERE first_seen_at >= ?
            GROUP BY source
            ORDER BY source
            """,
            (pSince.isoformat(),),
        ).fetchall()

    finally:
        vConnection.close()

    rCounts = [dict(vRow) for vRow in vRows]

    return rCounts


def get_offers_to_check(pDatabaseFile):
    """Retourne les seuls champs contrôlés par la page Qualité, pour chaque offre.

    Sans pandas ni description complète : le contrôle de toutes les offres
    reste immédiat. description vaut 1 si elle est renseignée, 0 sinon.
    """

    vConnection = connect_database(pDatabaseFile)
    vConnection.row_factory = sqlite3.Row

    try:
        vRows = vConnection.execute("""
            SELECT source, source_id, title, company, location, remote,
                   salary_label, salary_min, salary_max, url,
                   (description IS NOT NULL AND description <> '') AS description
            FROM job_offer
            ORDER BY first_seen_at DESC, published_at DESC
            """).fetchall()

    finally:
        vConnection.close()

    rOffers = [dict(vRow) for vRow in vRows]

    return rOffers


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


def get_skill_lists(pDatabaseFile):
    """Retourne la liste des compétences de chaque offre, vide si elle n'en a pas."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute("SELECT skills FROM job_offer").fetchall()

    finally:
        vConnection.close()

    rLists = []

    for (vSkills,) in vRows:
        try:
            vList = json.loads(vSkills) if vSkills else []

        except ValueError:
            vList = []

        rLists.append(
            [vSkill for vSkill in vList if isinstance(vSkill, str)]
            if isinstance(vList, list)
            else []
        )

    return rLists


def get_offer_texts(pDatabaseFile):
    """Retourne le titre et la description de chaque offre, réunis en un texte."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rTexts = [
            f"{vTitle or ''} {vDescription or ''}"
            for vTitle, vDescription in vConnection.execute(
                "SELECT title, description FROM job_offer"
            )
        ]

    finally:
        vConnection.close()

    return rTexts


def get_salary_signature(pDatabaseFile):
    """Retourne une empreinte des offres et de leurs salaires nets : elle change avec
    les offres, et aussi quand les règles de calcul du net sont modifiées.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        rSignature = tuple(vConnection.execute("""
                SELECT COUNT(*), MAX(last_seen_at), TOTAL(salary_net_monthly_min),
                    TOTAL(salary_net_monthly_max)
                FROM job_offer
                """).fetchone())

    finally:
        vConnection.close()

    return rSignature


def get_offers_signature(pDatabaseFile):
    """Retourne le nombre d'offres et la dernière date vue : change avec les offres."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rSignature = tuple(
            vConnection.execute(
                "SELECT COUNT(*), MAX(last_seen_at) FROM job_offer"
            ).fetchone()
        )

    finally:
        vConnection.close()

    return rSignature
