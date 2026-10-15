"""Gestion de la connexion et des migrations de la base SQLite"""

import json
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from storage.backup import backup_database
from utils.logger import get_logger

logger = get_logger(__name__)


def connect_database(pDatabasePath):
    """Ouvre une connexion vers la base SQLite."""

    vDatabasePath = Path(pDatabasePath)

    vDatabasePath.parent.mkdir(parents=True, exist_ok=True)

    # Une connexion par opération, fermée aussitôt : le bureau, le web et le
    # planificateur peuvent partager le même fichier. « database is locked »
    # signale une écriture longue d'un autre processus, à relancer.
    vConnection = sqlite3.connect(vDatabasePath)

    rConnection = vConnection

    return rConnection


def migrate_to_v1(pConnection):
    """Crée les tables des offres, des candidatures et de l'historique."""

    # Toute évolution de ce schéma passe par une nouvelle migration.
    pConnection.execute("""
        CREATE TABLE job_offer (
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            title TEXT,
            company TEXT,
            company_id TEXT,
            url TEXT,
            location TEXT,
            city TEXT,
            postal_code TEXT,
            country TEXT,
            distance_km REAL,
            contract TEXT,
            contract_type TEXT,
            employment_type TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_currency TEXT,
            salary_period TEXT,
            salary_label TEXT,
            salary_net_monthly_min REAL,
            salary_net_monthly_max REAL,
            salary_net_after_tax_monthly_min REAL,
            salary_net_after_tax_monthly_max REAL,
            has_13th_month INTEGER,
            has_bonus INTEGER,
            has_profit_sharing INTEGER,
            has_savings_plan INTEGER,
            remote TEXT,
            remote_days INTEGER,
            remote_type TEXT,
            nearest_metro TEXT,
            metro_distance_km REAL,
            date TEXT,
            published_at TEXT,
            updated_at TEXT,
            description TEXT,
            missions TEXT,
            requirements TEXT,
            education TEXT,
            skills TEXT,
            department TEXT,
            experience_level TEXT,
            job_type TEXT,
            PRIMARY KEY (source, source_id)
        )
        """)

    pConnection.execute("""
        CREATE TABLE job_application (
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT NOT NULL,
            applied_at TEXT,
            follow_up_date TEXT,
            follow_up_count INTEGER NOT NULL DEFAULT 0,
            last_follow_up_at TEXT,
            notes TEXT,
            PRIMARY KEY (source, source_id),
            FOREIGN KEY (source, source_id)
                REFERENCES job_offer(source, source_id)
        )
        """)

    pConnection.execute("""
        CREATE TABLE history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            scraper_type TEXT NOT NULL,
            url TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            item_count INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT
        )
        """)


def migrate_to_v2(pConnection):
    """Ajoute à l'historique les paramètres de chaque exécution."""

    # Paramètres au format JSON, absents pour les exécutions antérieures.
    pConnection.execute("ALTER TABLE history ADD COLUMN parameters TEXT")


def migrate_to_v3(pConnection):
    """Conserve chaque relance pour pouvoir les compter jour par jour."""

    pConnection.execute("""
        CREATE TABLE job_follow_up (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            followed_up_at TEXT NOT NULL,
            FOREIGN KEY (source, source_id)
                REFERENCES job_offer(source, source_id)
        )
        """)

    # Avant cette version, seule la dernière relance de chaque candidature est connue.
    pConnection.execute("""
        INSERT INTO job_follow_up (source, source_id, followed_up_at)
        SELECT source, source_id, last_follow_up_at
        FROM job_application
        WHERE last_follow_up_at IS NOT NULL
        """)


def migrate_to_v4(pConnection):
    """Ajoute les réglages modifiables depuis les interfaces."""

    pConnection.execute("""
        CREATE TABLE app_setting (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)


def migrate_to_v5(pConnection):
    """Reprend les offres enregistrées avant deux corrections de parsing.

    Adzuna renvoyait parfois ses accents échappés (\\u00e9) ; Hacker News rangeait
    tout l'en-tête de l'annonce dans le lieu et le titre.
    """

    # Imports locaux : la reprise réutilise le parsing métier sans que le
    # stockage en dépende pour son fonctionnement courant.
    # pylint: disable=import-outside-toplevel
    from job.sources.hackernews.parser import parse_header
    from utils.helpers import decode_unicode_escapes

    vEscapedRows = pConnection.execute(r"""
        SELECT source, source_id, title, description
        FROM job_offer
        WHERE title LIKE '%\u%' OR description LIKE '%\u%'
        """).fetchall()

    pConnection.executemany(
        "UPDATE job_offer SET title = ?, description = ? "
        "WHERE source = ? AND source_id = ?",
        [
            (
                decode_unicode_escapes(vTitle),
                decode_unicode_escapes(vDescription),
                vSource,
                vSourceId,
            )
            for vSource, vSourceId, vTitle, vDescription in vEscapedRows
        ],
    )

    # L'ancien découpage conservait l'en-tête complet, entreprise en tête, dans le lieu.
    vHeaderRows = [
        (vSourceId, vLocation)
        for vSourceId, vCompany, vLocation in pConnection.execute("""
            SELECT source_id, company, location
            FROM job_offer
            WHERE source = 'hackernews' AND company IS NOT NULL
            """)
        if vLocation and vLocation.startswith(vCompany)
    ]

    vUpdates = []

    for vSourceId, vHeader in vHeaderRows:
        vDetails = parse_header(vHeader)
        vUpdates.append(
            (
                vDetails["title"],
                vDetails["location"],
                vDetails["employment"],
                vDetails["employment"],
                vDetails["salary"],
                vSourceId,
            )
        )

    pConnection.executemany(
        """
        UPDATE job_offer
        SET title = ?, location = ?, contract_type = ?, employment_type = ?,
            salary_label = ?
        WHERE source = 'hackernews' AND source_id = ?
        """,
        vUpdates,
    )

    logger.info(
        "Reprise des offres : %s texte(s) décodé(s), %s en-tête(s) Hacker News "
        "redécoupé(s)",
        len(vEscapedRows),
        len(vUpdates),
    )


def migrate_to_v6(pConnection):
    """Ajoute les recherches enregistrées, réutilisables depuis la page Recherche."""

    # Sources et critères sont stockés en JSON, comme dans l'historique.
    pConnection.execute("""
        CREATE TABLE saved_search (
            name TEXT PRIMARY KEY,
            sources TEXT NOT NULL,
            criteria TEXT NOT NULL,
            saved_at TEXT NOT NULL
        )
        """)


def migrate_to_v7(pConnection):
    """Complète les offres déjà en base à partir de leur description.

    Même enrichissement que les nouvelles recherches : télétravail, compétences,
    expérience et salaire, uniquement pour les champs encore vides. Le net des
    salaires trouvés est calculé avec les règles enregistrées. Tout passe par la
    connexion de la migration : une seconde connexion attendrait son verrou.
    """

    # pylint: disable=import-outside-toplevel
    import pandas as pd

    from job.enrichment import ENRICHED_COLUMNS, TEXT_COLUMNS, enrich_offer
    from config import NET_SALARY_RATIO
    from job.salary import add_net_salary, get_income_tax_rate

    vColumns = ["source", "source_id", *TEXT_COLUMNS, *ENRICHED_COLUMNS]
    vColumns = list(dict.fromkeys(vColumns))
    # Colonnes issues des constantes TEXT_COLUMNS et ENRICHED_COLUMNS.
    vCursor = pConnection.execute(
        f"SELECT {', '.join(vColumns)} FROM job_offer"  # nosec B608
    )
    vOffers = [dict(zip(vColumns, vRow)) for vRow in vCursor.fetchall()]

    vUpdated = []

    for vOffer in vOffers:
        vText = " ".join(str(vOffer.get(vColumn) or "") for vColumn in TEXT_COLUMNS)

        if enrich_offer(vOffer, vText):
            vUpdated.append(vOffer)

    if vUpdated:
        # Réglages lus directement : passer par job.settings créerait une
        # dépendance circulaire entre le stockage et le métier.
        vValues = dict(pConnection.execute("SELECT key, value FROM app_setting"))
        vNetPercent = float(vValues.get("net_salary_percent", NET_SALARY_RATIO * 100))
        vTaxRate = float(vValues.get("income_tax_rate", get_income_tax_rate() or 0))

        vItems = add_net_salary(
            pd.DataFrame(vUpdated),
            pNetRatio=vNetPercent / 100,
            pTaxRate=vTaxRate or None,
        )

        vSetColumns = [*ENRICHED_COLUMNS, *NET_COLUMNS]

        pConnection.executemany(
            "UPDATE job_offer SET "  # nosec B608
            + ", ".join(f"{vColumn} = ?" for vColumn in vSetColumns)
            + " WHERE source = ? AND source_id = ?",
            [
                (
                    *(to_storage(vRow[vColumn]) for vColumn in vSetColumns),
                    vRow["source"],
                    vRow["source_id"],
                )
                for vRow in vItems.to_dict("records")
            ],
        )

    logger.info("Reprise des offres : %s offre(s) complétée(s)", len(vUpdated))


def migrate_to_v8(pConnection):
    """Ajoute la date limite fournie par la source et la vérification du lien."""

    # availability : NULL tant que le lien n'a pas été vérifié, puis available ou
    # expired selon la réponse du site de l'offre.
    for vColumn in ("expires_at", "availability", "availability_checked_at"):
        pConnection.execute(f"ALTER TABLE job_offer ADD COLUMN {vColumn} TEXT")


def migrate_to_v9(pConnection):
    """Ajoute l'empreinte des offres et les décisions sur les offres multi-sources."""

    # pylint: disable=import-outside-toplevel
    from job.fingerprint import build_fingerprint

    pConnection.execute("ALTER TABLE job_offer ADD COLUMN fingerprint TEXT")
    pConnection.execute(
        "CREATE INDEX idx_job_offer_fingerprint ON job_offer(fingerprint)"
    )

    # Décision prise sur un groupe d'annonces : merged pour une seule offre
    # malgré leurs différences, separate pour les garder distinctes.
    pConnection.execute("""
        CREATE TABLE duplicate_decision (
            fingerprint TEXT PRIMARY KEY,
            decision TEXT NOT NULL,
            decided_at TEXT NOT NULL
        )
        """)

    vRows = pConnection.execute(
        "SELECT source, source_id, title, company, location FROM job_offer"
    ).fetchall()

    pConnection.executemany(
        "UPDATE job_offer SET fingerprint = ? WHERE source = ? AND source_id = ?",
        [
            (
                build_fingerprint(
                    {"title": vTitle, "company": vCompany, "location": vLocation}
                ),
                vSource,
                vSourceId,
            )
            for vSource, vSourceId, vTitle, vCompany, vLocation in vRows
        ],
    )


# Colonnes de salaire net calculées par add_net_salary
NET_COLUMNS = (
    "salary_net_monthly_min",
    "salary_net_monthly_max",
    "salary_net_after_tax_monthly_min",
    "salary_net_after_tax_monthly_max",
)


def _is_missing(pValue):
    """Indique si une valeur est un NaN de pandas, qui n'a pas sa place en base."""

    rMissing = isinstance(pValue, float) and math.isnan(pValue)

    return rMissing


def to_storage(pValue):
    """Convertit une valeur enrichie pour SQLite : liste en JSON, NaN en NULL."""

    rValue = pValue

    if isinstance(pValue, list):
        rValue = json.dumps(pValue, ensure_ascii=False)
    elif _is_missing(pValue):
        rValue = None

    return rValue


# Colonnes de date sur lesquelles un décompte quotidien est autorisé
DAILY_COUNT_COLUMNS = {
    ("job_offer", "first_seen_at"),
    ("job_application", "applied_at"),
    ("job_follow_up", "followed_up_at"),
}


def count_by_day(pDatabasePath, pTable, pDateColumn, pDays, pNow=None):
    """Compte les lignes datées de chacun des derniers jours, jours vides compris.

    La table et la colonne sont insérées dans la requête : seules celles de
    DAILY_COUNT_COLUMNS sont acceptées.
    """

    if (pTable, pDateColumn) not in DAILY_COUNT_COLUMNS:
        raise ValueError(f"Décompte quotidien non autorisé : {pTable}.{pDateColumn}")

    vToday = (pNow or datetime.now()).date()
    vFirstDay = vToday - timedelta(days=pDays - 1)

    vConnection = connect_database(pDatabasePath)

    try:
        # Table et colonne vérifiées contre DAILY_COUNT_COLUMNS ci-dessus.
        vRows = vConnection.execute(
            f"SELECT substr({pDateColumn}, 1, 10) AS day, COUNT(*) "  # nosec B608
            f"FROM {pTable} WHERE {pDateColumn} >= ? GROUP BY day",
            (vFirstDay.isoformat(),),
        ).fetchall()

    finally:
        vConnection.close()

    vCounts = dict(vRows)

    rCounts = [
        (vDay, vCounts.get(vDay.isoformat(), 0))
        for vDay in (vFirstDay + timedelta(days=vOffset) for vOffset in range(pDays))
    ]

    return rCounts


def migrate_to_v10(pConnection):
    """Ajoute les pièces jointes des candidatures (CV envoyé, lettre)."""

    # Le fichier est rangé sous stored_name, un nom aléatoire : le nom choisi par
    # l'utilisateur (file_name) ne sert qu'à l'affichage et au téléchargement.
    pConnection.execute("""
        CREATE TABLE job_attachment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            stored_name TEXT NOT NULL UNIQUE,
            size INTEGER NOT NULL,
            added_at TEXT NOT NULL,
            FOREIGN KEY (source, source_id)
                REFERENCES job_offer(source, source_id)
        )
        """)
    pConnection.execute(
        "CREATE INDEX idx_job_attachment_offer ON job_attachment(source, source_id)"
    )


def migrate_to_v11(pConnection):
    """Ajoute l'historique des réponses aux questions de révision."""

    # Une ligne par réponse : la dernière réponse à une question dit si elle est
    # acquise ou à revoir, les précédentes gardent la progression.
    pConnection.execute("""
        CREATE TABLE quiz_answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL,
            theme TEXT NOT NULL,
            correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL
        )
        """)
    pConnection.execute(
        "CREATE INDEX idx_quiz_answer_question ON quiz_answer(question_id)"
    )


def migrate_to_v12(pConnection):
    """Ajoute la date d'entretien et complète le pays et la ville des offres."""

    # pylint: disable=import-outside-toplevel
    from job.location import detect_location

    pConnection.execute("ALTER TABLE job_application ADD COLUMN interview_at TEXT")

    vRows = pConnection.execute(
        "SELECT source, source_id, location, country, city FROM job_offer"
    ).fetchall()

    vUpdates = []

    for vSource, vSourceId, vLocation, vCountry, vCity in vRows:
        vFoundCountry, vFoundCity = detect_location(vLocation, vCountry)

        if (vFoundCountry and not vCountry) or (vFoundCity and not vCity):
            vUpdates.append(
                (vCountry or vFoundCountry, vCity or vFoundCity, vSource, vSourceId)
            )

    pConnection.executemany(
        "UPDATE job_offer SET country = ?, city = ? WHERE source = ? AND source_id = ?",
        vUpdates,
    )

    logger.info(
        "Reprise des offres : pays ou ville complété pour %s offre(s)", len(vUpdates)
    )


def migrate_to_v13(pConnection):
    """Crée la table des questions de révision importées par l'utilisateur."""

    # Le contenu de la question est gardé en JSON, au format des fichiers livrés.
    pConnection.execute("""
        CREATE TABLE quiz_question (
            question_id TEXT PRIMARY KEY,
            theme TEXT NOT NULL,
            theme_label TEXT NOT NULL,
            content TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
        """)


def migrate_to_v14(pConnection):
    """Ajoute les thèmes, schémas et guides importés avec les questions de révision."""

    pConnection.execute("""
        CREATE TABLE quiz_theme (
            theme TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            skills TEXT NOT NULL
        )
        """)
    # Schéma SVG d'une question, déjà vérifié sans script à l'import
    pConnection.execute("""
        CREATE TABLE quiz_asset (
            name TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
        """)
    # Guide en Markdown, rattaché au thème de même nom quand il existe
    pConnection.execute("""
        CREATE TABLE quiz_guide (
            name TEXT PRIMARY KEY,
            theme TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
        """)


def migrate_to_v15(pConnection):
    """Ajoute le domaine et le sous-domaine indiqués par un pack de révision."""

    pConnection.execute("ALTER TABLE quiz_theme ADD COLUMN domain TEXT")
    pConnection.execute("ALTER TABLE quiz_theme ADD COLUMN subdomain TEXT")


def migrate_to_v16(pConnection):
    """Ajoute l'identifiant des réponses envoyées par l'application mobile."""

    # Identifiant choisi par le téléphone : un envoi relancé après une coupure
    # ne crée pas de doublon. Les réponses faites ici n'en ont pas.
    pConnection.execute("ALTER TABLE quiz_answer ADD COLUMN client_id TEXT")
    pConnection.execute(
        "CREATE UNIQUE INDEX idx_quiz_answer_client ON quiz_answer(client_id) "
        "WHERE client_id IS NOT NULL"
    )


def migrate_to_v17(pConnection):
    """Ajoute les défis de programmation : graines des données et tentatives."""

    # Une graine par défi : les données personnelles restent les mêmes d'une
    # session à l'autre, comme la réponse attendue.
    pConnection.execute("""
        CREATE TABLE challenge_seed (
            challenge TEXT PRIMARY KEY,
            seed INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
    pConnection.execute("""
        CREATE TABLE challenge_attempt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge TEXT NOT NULL,
            part INTEGER NOT NULL,
            answer TEXT NOT NULL,
            correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL
        )
        """)
    pConnection.execute(
        "CREATE INDEX idx_challenge_attempt ON challenge_attempt(challenge, part)"
    )


MIGRATIONS = [
    migrate_to_v1,
    migrate_to_v2,
    migrate_to_v3,
    migrate_to_v4,
    migrate_to_v5,
    migrate_to_v6,
    migrate_to_v7,
    migrate_to_v8,
    migrate_to_v9,
    migrate_to_v10,
    migrate_to_v11,
    migrate_to_v12,
    migrate_to_v13,
    migrate_to_v14,
    migrate_to_v15,
    migrate_to_v16,
    migrate_to_v17,
]


def get_schema_version(pConnection):
    """Retourne la version du schéma enregistrée dans la base."""

    vCursor = pConnection.execute("PRAGMA user_version")

    rVersion = vCursor.fetchone()[0]

    return rVersion


def initialize_database(pDatabasePath):
    """Applique les migrations manquantes à la base."""

    vConnection = connect_database(pDatabasePath)

    try:
        # La version du schéma est stockée dans la base elle-même (PRAGMA
        # user_version) : seules les migrations plus récentes s'appliquent. Pour
        # diagnostiquer, ouvrir la base avec un outil SQLite et lire cette valeur.
        vCurrentVersion = get_schema_version(vConnection)

        # Une base déjà remplie est copiée avant d'être modifiée ; sans copie
        # réussie, l'exception interrompt le lancement et la base reste intacte.
        if 0 < vCurrentVersion < len(MIGRATIONS):
            backup_database(pDatabasePath, datetime.now(), f"avant-v{len(MIGRATIONS)}")

        for vVersion in range(vCurrentVersion + 1, len(MIGRATIONS) + 1):

            logger.info("Migration de la base vers la version %s", vVersion)

            # Chaque migration est atomique : en cas d'échec, la base reste
            # dans la version précédente.
            vConnection.execute("BEGIN")

            try:
                MIGRATIONS[vVersion - 1](vConnection)

                vConnection.execute(f"PRAGMA user_version = {vVersion}")

                vConnection.commit()

            except sqlite3.Error:
                vConnection.rollback()
                logger.exception("Échec de la migration vers la version %s", vVersion)
                raise

    finally:
        vConnection.close()
