"""Tests de la connexion et des migrations de la base SQLite"""

import sqlite3
from pathlib import Path

import pytest

from storage.database import (
    connect_database,
    count_by_day,
    get_database_version,
    get_schema_version,
    initialize_database,
)
from storage.migrations import (
    MIGRATIONS,
    migrate_to_v1,
    migrate_to_v27,
    migrate_to_v28,
    migrate_to_v29,
    migrate_to_v30,
    migrate_to_v31,
    migrate_to_v32,
    migrate_to_v33,
    migrate_to_v34,
)


def get_table_names(pDatabaseFile):
    """Retourne le nom des tables présentes dans la base."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )

        rTableNames = {vRow[0] for vRow in vCursor.fetchall()}

    finally:
        vConnection.close()

    return rTableNames


def test_connect_database_creates_database(tmp_path):
    """Vérifie qu'une base SQLite est correctement créée."""

    vDatabasePath = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabasePath)

    assert vDatabasePath.exists()
    assert isinstance(vConnection, sqlite3.Connection)

    vConnection.close()


def test_initialize_database_creates_tables(tmp_path):
    """Vérifie que l'initialisation crée toutes les tables de l'application."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vTableNames = get_table_names(vDatabaseFile)

    assert {"job_offer", "job_application", "history"} <= vTableNames
    assert "job_tracking" not in vTableNames


def test_initialize_database_sets_latest_version(tmp_path):
    """Vérifie que la base est à la dernière version après initialisation."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)

    finally:
        vConnection.close()

    assert vVersion == len(MIGRATIONS)


def test_initialize_database_can_run_twice(tmp_path):
    """Vérifie qu'une seconde initialisation ne rejoue pas les migrations."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    initialize_database(vDatabaseFile)

    assert "job_offer" in get_table_names(vDatabaseFile)


def test_failed_migration_keeps_previous_version(tmp_path):
    """Vérifie qu'une migration en échec ne laisse pas la base à moitié migrée."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        vConnection.execute("CREATE TABLE job_application (id INTEGER)")
        vConnection.commit()

    finally:
        vConnection.close()

    with pytest.raises(sqlite3.Error):
        initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)

    finally:
        vConnection.close()

    assert vVersion == 0
    assert "job_offer" not in get_table_names(vDatabaseFile)


def test_migration_to_v2_keeps_existing_history(tmp_path):
    """Vérifie qu'une base en version 1 passe en version 2 sans perdre de données."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        migrate_to_v1(vConnection)
        vConnection.execute("PRAGMA user_version = 1")
        vConnection.execute("""
            INSERT INTO history (
                started_at, scraper_type, url, page_count,
                item_count, duration_seconds, status
            )
            VALUES ('2026-10-01T08:00:00', 'job', 'multi-source', 2, 40, 3.5, 'success')
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vVersion = get_schema_version(vConnection)
        vRows = vConnection.execute(
            "SELECT item_count, parameters FROM history"
        ).fetchall()

    finally:
        vConnection.close()

    assert vVersion == len(MIGRATIONS)
    assert vRows == [(40, None)]


def test_migration_to_v3_keeps_last_follow_ups(tmp_path):
    """Vérifie que la dernière relance connue est reprise dans le journal."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:2]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 2")
        vConnection.execute("""
            INSERT INTO job_offer (source, source_id, first_seen_at, last_seen_at)
            VALUES ('lever', '1', '2026-10-01', '2026-10-01')
            """)
        vConnection.execute("""
            INSERT INTO job_application (
                source, source_id, status, follow_up_count, last_follow_up_at
            )
            VALUES ('lever', '1', 'APPLIED', 2, '2026-10-05T09:00:00')
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT source, source_id, followed_up_at FROM job_follow_up"
        ).fetchall()

    finally:
        vConnection.close()

    assert vRows == [("lever", "1", "2026-10-05T09:00:00")]


def test_migration_to_v5_repairs_saved_offers(tmp_path):
    """Vérifie la reprise des accents échappés et des en-têtes Hacker News."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:4]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 4")
        vConnection.executemany(
            """
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at,
                title, company, location, description
            )
            VALUES (?, ?, '2026-10-01', '2026-10-01', ?, ?, ?, ?)
            """,
            [
                ("adzuna", "1", "D\\u00e9veloppeur", "LCL", "Paris", "Syst\\u00e8mes"),
                (
                    "hackernews",
                    "2",
                    "Senior SWE | REMOTE (US) | Full-time | $170k",
                    "Sidekick",
                    "Sidekick | Senior SWE | REMOTE (US) | Full-time | $170k",
                    None,
                ),
                ("hackernews", "3", "Backend", "Acme", "Berlin", None),
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vRows = vConnection.execute("""
            SELECT title, location, description, contract_type, salary_label
            FROM job_offer
            ORDER BY source_id
            """).fetchall()

    finally:
        vConnection.close()

    assert vRows == [
        ("Développeur", "Paris", "Systèmes", None, None),
        ("Senior SWE", "REMOTE (US)", None, "Full-time", "$170k"),
        ("Backend", "Berlin", None, None, None),
    ]


def test_count_by_day_rejects_unknown_column(tmp_path):
    """Vérifie qu'une table ou une colonne non prévue est refusée."""

    with pytest.raises(ValueError, match="job_offer.title"):
        count_by_day(tmp_path / "scraper.db", "job_offer", "title", 7)


def test_migration_to_v7_enriches_saved_offers(tmp_path):
    """Vérifie que les offres en base sont complétées et leur net calculé."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:6]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 6")
        vConnection.execute("""
            INSERT INTO app_setting (key, value) VALUES ('net_salary_percent', '80')
            """)
        vConnection.execute("""
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at, title, description,
                experience_level
            )
            VALUES (
                'adzuna', '1', '2026-10-01', '2026-10-01', 'Développeur Python',
                'Full remote, 3 ans d''expérience, 48 000 € brut annuel', NULL
            )
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vRow = vConnection.execute("""
            SELECT remote, remote_type, skills, experience_level, salary_min,
                   salary_currency, salary_net_monthly_min
            FROM job_offer
            """).fetchone()

    finally:
        vConnection.close()

    # La colonne remote est de type TEXT depuis la version 1 du schéma.
    assert vRow == ("1", "full", '["Python"]', "3 ans", 48000.0, "EUR", 3200)


def test_migration_to_v9_computes_fingerprints(tmp_path):
    """Vérifie le calcul de l'empreinte des offres déjà en base."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:8]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 8")
        vConnection.execute("""
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at, title, company, location
            )
            VALUES ('adzuna', '1', '2026-10-01', '2026-10-01',
                    'Développeur Java H/F', 'Acme SAS', 'Lille (59)')
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vFingerprint = vConnection.execute(
            "SELECT fingerprint FROM job_offer"
        ).fetchone()[0]

    finally:
        vConnection.close()

    assert vFingerprint == "developpeur java|acme|lille"


def test_database_version_changes_with_each_write(tmp_path):
    """Vérifie que l'empreinte change après une écriture validée."""

    vDatabaseFile = tmp_path / "base.db"

    assert get_database_version(vDatabaseFile) is None

    initialize_database(vDatabaseFile)
    vBefore = get_database_version(vDatabaseFile)

    with connect_database(vDatabaseFile) as vConnection:
        vConnection.execute("CREATE TABLE essai (valeur TEXT)")
        vConnection.execute("INSERT INTO essai VALUES ('x')")

    assert get_database_version(vDatabaseFile) != vBefore


def test_migration_to_v21_removes_offers_the_parsers_now_reject(tmp_path):
    """Vérifie le retrait des anciens messages sans forme d'offre, sauf s'ils sont suivis."""

    vDatabaseFile = tmp_path / "scraper.db"
    vJunk = "there used to be 800+ posts here :("
    vHiring = "We're hiring software engineers at the IRS!"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:20]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 20")
        vConnection.executemany(
            """
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at, title, company
            )
            VALUES (?, ?, '2026-10-01', '2026-10-01', ?, ?)
            """,
            [
                ("hackernews", "1", vJunk, vJunk),
                ("hackernews", "2", vJunk, vJunk),
                ("hackernews", "3", vHiring, vHiring),
                ("hackernews", "4", "Founding Engineer", "exLabora"),
                ("findwork", "5", None, "Location: Bangalore"),
                ("findwork", "6", "Backend Developer", "Okta"),
            ],
        )
        vConnection.execute("""
            INSERT INTO interview_note (
                source, source_id, interviewed_at, questions, impressions
            )
            VALUES ('hackernews', '2', '2026-10-02', 'Questions', 'Impressions')
            """)
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT source_id, company FROM job_offer ORDER BY source_id"
        ).fetchall()

    finally:
        vConnection.close()

    assert vRows == [
        ("2", vJunk),
        ("3", None),
        ("4", "exLabora"),
        ("6", "Okta"),
    ]


def test_migration_to_v22_decodes_adzuna_html_and_finds_agency(tmp_path):
    """Vérifie le décodage des entités HTML et l'agence retrouvée dans le texte."""

    vDatabaseFile = tmp_path / "scraper.db"

    vConnection = connect_database(vDatabaseFile)

    try:
        for vMigration in MIGRATIONS[:21]:
            vMigration(vConnection)

        vConnection.execute("PRAGMA user_version = 21")
        vConnection.executemany(
            """
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at, title, company,
                description
            )
            VALUES (?, ?, '2026-10-01', '2026-10-01', ?, ?, ?)
            """,
            [
                (
                    "adzuna",
                    "1",
                    "&Eacute;lectricien H/F",
                    None,
                    "Votre agence d&rsquo;int&eacute;rim PROMAN recrute",
                ),
                ("adzuna", "2", "Soudeur", "Acme", "Soudure &amp; montage"),
                ("lever", "3", "Dev &amp; Ops", None, "x"),
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()

    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT title, company, description FROM job_offer ORDER BY source_id"
        ).fetchall()

    finally:
        vConnection.close()

    assert vRows == [
        ("Électricien H/F", "PROMAN", "Votre agence d’intérim PROMAN recrute"),
        ("Soudeur", "Acme", "Soudure & montage"),
        # Hors Adzuna, seul le titre est décodé, par la migration v27.
        ("Dev & Ops", None, "x"),
    ]


def test_offers_list_uses_the_discovery_date_index(tmp_path):
    """Vérifie que la liste des offres, triée par date, ne trie plus toute la table."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vConnection = connect_database(vDatabaseFile)

    try:
        vPlan = " ".join(vRow[3] for vRow in vConnection.execute("""
                EXPLAIN QUERY PLAN SELECT * FROM job_offer
                ORDER BY first_seen_at DESC, published_at DESC LIMIT 1000
                """))

    finally:
        vConnection.close()

    assert "idx_job_offer_first_seen" in vPlan
    assert "TEMP B-TREE" not in vPlan


def test_migration_to_v29_renames_country_codes(tmp_path):
    """Vérifie le pays « FR » enregistré par SmartRecruiters, renommé « France »."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vConnection = connect_database(vDatabaseFile)

    try:
        vConnection.executemany(
            "INSERT INTO job_offer (source, source_id, first_seen_at, last_seen_at,"
            " country) VALUES ('smartrecruiters', ?, '2026-10-01',"
            " '2026-10-01', ?)",
            [("1", "FR"), ("2", "France"), ("3", "Mars")],
        )
        migrate_to_v29(vConnection)
        vCountries = [
            vRow[0]
            for vRow in vConnection.execute(
                "SELECT country FROM job_offer ORDER BY source_id"
            )
        ]

    finally:
        vConnection.close()

    assert vCountries == ["France", "France", "Mars"]


def test_migration_to_v27_decodes_html_entities(tmp_path):
    """Vérifie le décodage des titres déjà enregistrés et le recalcul de l'empreinte."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vConnection = connect_database(vDatabaseFile)

    try:
        vConnection.execute("""
            INSERT INTO job_offer (
                source, source_id, first_seen_at, last_seen_at, title, company,
                fingerprint, detected_skills
            )
            VALUES (
                'findwork', '1', '2026-10-01', '2026-10-01',
                'Data &amp; Python', 'R&amp;D', 'ancienne', '["Python"]'
            )
            """)
        migrate_to_v27(vConnection)

        vRow = vConnection.execute(
            "SELECT title, company, fingerprint, detected_skills FROM job_offer"
        ).fetchone()

    finally:
        vConnection.close()

    assert vRow[:2] == ("Data & Python", "R&D")
    assert vRow[2] != "ancienne"
    assert vRow[3] is None


def test_migration_to_v30_forgets_unknown_places(tmp_path):
    """Vérifie que seuls les lieux introuvables sont oubliés, pour être recherchés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vConnection = connect_database(vDatabaseFile)

    try:
        vConnection.executemany(
            "INSERT INTO geo_cache (location_key, latitude, longitude, label,"
            " looked_up_at) VALUES (?, ?, ?, ?, '2026-10-01')",
            [("lille", 50.6, 3.0, "Lille"), ("lyon auvergne", None, None, None)],
        )
        migrate_to_v30(vConnection)
        vKeys = [
            vRow[0]
            for vRow in vConnection.execute("SELECT location_key FROM geo_cache")
        ]

    finally:
        vConnection.close()

    assert vKeys == ["lille"]


# Depuis cette version, chaque migration a son propre test dans ce fichier.
FIRST_NAMED_MIGRATION = 27


def build_database_at(pDatabaseFile, pVersion):
    """Ouvre une base au schéma de la version donnée, sans les migrations suivantes."""

    rConnection = connect_database(pDatabaseFile)

    for vMigration in MIGRATIONS[:pVersion]:
        vMigration(rConnection)

    return rConnection


def get_columns(pConnection, pTable):
    """Retourne les colonnes d'une table."""

    rColumns = [vRow[1] for vRow in pConnection.execute(f"PRAGMA table_info({pTable})")]

    return rColumns


def test_every_recent_migration_has_its_test():
    """Vérifie qu'une nouvelle migration n'est pas livrée sans test qui la nomme."""

    vTests = Path(__file__).read_text(encoding="utf-8")

    vUntested = [
        vVersion
        for vVersion in range(FIRST_NAMED_MIGRATION, len(MIGRATIONS) + 1)
        if f"migrate_to_v{vVersion}("
        not in vTests.replace(f"migrate_to_v{vVersion},", "")
    ]

    assert not vUntested, f"Migrations sans test : {vUntested}"


def test_migration_to_v28_adds_departments(tmp_path):
    """Vérifie les colonnes de département des lieux et des offres."""

    vConnection = build_database_at(tmp_path / "scraper.db", 27)

    try:
        migrate_to_v28(vConnection)

        assert "department" in get_columns(vConnection, "geo_cache")
        assert "french_department" in get_columns(vConnection, "job_offer")

    finally:
        vConnection.close()


def test_migration_to_v31_starts_status_history(tmp_path):
    """Vérifie l'historique amorcé par les candidatures puis suivi par déclencheur."""

    vConnection = build_database_at(tmp_path / "scraper.db", 30)

    try:
        vConnection.execute(
            "INSERT INTO job_application (source, source_id, status, applied_at)"
            " VALUES ('lever', '1', 'APPLIED', '2026-10-01T09:00:00')"
        )
        migrate_to_v31(vConnection)
        vConnection.execute(
            "UPDATE job_application SET status = 'INTERVIEW' WHERE source_id = '1'"
        )
        vHistory = [
            vRow[0]
            for vRow in vConnection.execute(
                "SELECT status FROM application_history ORDER BY id"
            )
        ]

    finally:
        vConnection.close()

    assert vHistory == ["APPLIED", "INTERVIEW"]


def test_migration_to_v34_adds_education_level_to_compute(tmp_path):
    """Vérifie la colonne du diplôme demandé, vide pour l'existant : à repérer."""

    vConnection = build_database_at(tmp_path / "scraper.db", 33)

    try:
        vConnection.execute(
            "INSERT INTO job_offer (source, source_id, first_seen_at, last_seen_at)"
            " VALUES ('lever', '1', '2026-10-29', '2026-10-29')"
        )
        migrate_to_v34(vConnection)
        vLevel = vConnection.execute("SELECT education_level FROM job_offer").fetchone()

    finally:
        vConnection.close()

    assert vLevel == (None,)


def test_migration_to_v32_adds_recruiter_address(tmp_path):
    """Vérifie la colonne de l'adresse du recruteur, vide pour l'existant."""

    vConnection = build_database_at(tmp_path / "scraper.db", 31)

    try:
        vConnection.execute(
            "INSERT INTO job_application (source, source_id, status)"
            " VALUES ('lever', '1', 'APPLIED')"
        )
        migrate_to_v32(vConnection)
        vAddress = vConnection.execute(
            "SELECT contact_email FROM job_application"
        ).fetchone()[0]

    finally:
        vConnection.close()

    assert vAddress is None


def test_migration_to_v33_reads_adzuna_hourly_salaries(tmp_path):
    """Vérifie qu'un taux horaire Adzuna présenté comme annuel retrouve son net."""

    vConnection = build_database_at(tmp_path / "scraper.db", 32)

    try:
        vConnection.executemany(
            "INSERT INTO job_offer (source, source_id, title, salary_min, salary_max,"
            " salary_period, first_seen_at, last_seen_at)"
            " VALUES ('adzuna', ?, 'Agent', ?, ?, 'year', '2026-10-01', '2026-10-01')",
            [("1", 12.0, 13.0), ("2", 90000.0, 120000.0)],
        )
        migrate_to_v33(vConnection)
        vRows = vConnection.execute(
            "SELECT source_id, salary_period, salary_net_monthly_min"
            " FROM job_offer ORDER BY source_id"
        ).fetchall()

    finally:
        vConnection.close()

    assert vRows == [("1", "hour", 1365), ("2", "year", None)]
