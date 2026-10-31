"""Tests du moteur du bac à sable SQL : dialectes, protections et comparaison"""

import pytest

from job.sql_sandbox import (
    SqlError,
    boundary_diff,
    compare_results,
    describe_schema,
    execute,
    timestamp_diff,
    translate,
)


def test_sql_server_top_becomes_limit():
    """Vérifie TOP déplacé en LIMIT, chaînes et commentaires respectés."""

    assert translate("SELECT TOP 3 id FROM machine ORDER BY id;", "sqlserver") == (
        "SELECT id FROM machine ORDER BY id LIMIT 3"
    )
    assert translate("SELECT DISTINCT TOP (2) type FROM intervention", "sqlserver") == (
        "SELECT DISTINCT type FROM intervention LIMIT 2"
    )
    assert "'GETDATE() -- texte'" in translate(
        "SELECT 'GETDATE() -- texte' FROM machine -- fin", "sqlserver"
    )

    with pytest.raises(SqlError, match="début de la requête"):
        translate(
            "SELECT id FROM machine WHERE id IN (SELECT TOP 1 id FROM machine)",
            "sqlserver",
        )


@pytest.mark.parametrize(
    ("pQuery", "pDialect", "pMessage"),
    [
        ("SELECT TOP 3 id FROM machine", "mysql", "MySQL n'a pas TOP"),
        ("SELECT id FROM machine LIMIT 3", "sqlserver", "n'a pas LIMIT"),
        ("SELECT ISNULL(nom, 'x') FROM technicien", "mysql", "IFNULL"),
        ("SELECT IFNULL(nom, 'x') FROM technicien", "sqlserver", "ISNULL"),
        ("SELECT GETDATE()", "mysql", "NOW()"),
        ("SELECT NOW()", "sqlserver", "GETDATE()"),
        (
            "SELECT DATEDIFF(day, debut, fin) FROM intervention",
            "mysql",
            "TIMESTAMPDIFF",
        ),
        ("SELECT DATEDIFF(debut, fin) FROM intervention", "sqlserver", "l'unité"),
        ("SELECT DATEDIFF(month, debut, fin) FROM intervention", "sqlserver", "month"),
        ("SELECT `nom` FROM machine", "sqlserver", "crochets"),
        ("SELECT [nom] FROM machine", "mysql", "accents graves"),
        ("-- rien", "mysql", "Écrivez une requête"),
    ],
)
def test_other_dialect_is_refused(pQuery, pDialect, pMessage):
    """Vérifie qu'une écriture de l'autre dialecte est signalée avant exécution."""

    vResult = execute(pQuery, pDialect)

    assert pMessage in vResult["error"]


@pytest.mark.parametrize(
    "pQuery",
    [
        "ATTACH DATABASE 'copie.db' AS copie",
        "PRAGMA table_info(machine)",
        "DROP TABLE machine",
        "CREATE TABLE essai (a)",
        "BEGIN",
        "EXPLAIN SELECT 1",
        "SELECT * FROM pragma_table_info('machine')",
    ],
)
def test_only_row_statements_are_allowed(pQuery):
    """Vérifie le refus de tout ce qui n'est pas lecture ou écriture de lignes."""

    assert "Seules les requêtes" in execute(pQuery, "mysql")["error"]


def test_limits_stop_dangerous_queries():
    """Vérifie l'arrêt d'une requête trop longue, d'une récursion, d'une valeur énorme."""

    assert (
        "2 secondes"
        in execute(
            "SELECT count(*) FROM intervention a, intervention b, intervention c, "
            "intervention d, intervention e, intervention f, intervention g",
            "mysql",
        )["error"]
    )
    assert (
        "récursives"
        in execute(
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) "
            "SELECT count(*) FROM n",
            "mysql",
        )["error"]
    )
    for vFunction in ("zeroblob(500000000)", "load_extension('x')", "random()"):
        assert execute(f"SELECT {vFunction}", "mysql")["error"].startswith(
            "Fonction non permise ici"
        )

    assert execute("SELECT CURRENT_DATE", "mysql")["rows"] == [("2026-06-30",)]
    assert (
        "Une seule requête"
        in execute("SELECT 1; DELETE FROM machine", "mysql")["error"]
    )


def test_each_query_gets_a_fresh_database():
    """Vérifie qu'une suppression ne survit pas à la requête suivante."""

    vDeleted = execute("DELETE FROM machine", "mysql", "SELECT COUNT(*) FROM machine")

    assert vDeleted["changed"] == 9
    assert vDeleted["rows"] == [(0,)]
    assert execute("SELECT COUNT(*) FROM machine", "mysql")["rows"] == [(9,)]


def test_errors_are_explained_in_french():
    """Vérifie la traduction des erreurs courantes de SQLite."""

    assert (
        execute("SELECT * FROM machin", "mysql")["error"] == "Table inconnue : machin."
    )
    assert (
        "HAVING"
        in execute(
            "SELECT machine_id FROM intervention "
            "WHERE SUM(cout) > 5 GROUP BY machine_id",
            "mysql",
        )["error"]
    )
    assert (
        "Colonne ambiguë : id"
        in execute(
            "SELECT id FROM intervention i JOIN machine m ON m.id = i.machine_id",
            "mysql",
        )["error"]
    )


def test_hour_counts_differ_between_dialects():
    """Vérifie heures entières en MySQL et changements d'heure en SQL Server."""

    assert timestamp_diff("hour", "2026-01-20 14:30:00", "2026-01-21 09:00:00") == 18
    assert boundary_diff("hour", "2026-01-20 14:30:00", "2026-01-21 09:00:00") == 19
    assert boundary_diff("day", "2026-06-29 23:00:00", "2026-06-30 01:00:00") == 1
    assert execute("SELECT DATEDIFF(NOW(), '2026-06-24')", "mysql")["rows"] == [(6,)]


def test_results_are_compared_by_value():
    """Vérifie nombres arrondis, ordre facultatif ou exigé, lignes manquantes."""

    vExpected = {"columns": ["a", "b"], "rows": [(1, 2.0), (3, None)]}

    assert (
        compare_results(
            {"columns": ["x", "y"], "rows": [(1.0, 1.999999)] + [(3, None)]},
            vExpected,
            True,
        )
        == ""
    )
    assert (
        compare_results(
            {"columns": ["a", "b"], "rows": [(3, None), (1, 2)]}, vExpected, False
        )
        == ""
    )
    assert "ORDER BY" in compare_results(
        {"columns": ["a", "b"], "rows": [(3, None), (1, 2)]}, vExpected, True
    )
    assert "1 colonne(s)" in compare_results(
        {"columns": ["a"], "rows": [(1,)]}, vExpected, False
    )
    assert "Ligne attendue absente : (3 | NULL)" in compare_results(
        {"columns": ["a", "b"], "rows": [(1, 2)]}, vExpected, False
    )


def test_schema_lists_tables_and_columns():
    """Vérifie la description de la base d'exemple."""

    vSchema = dict(describe_schema())

    assert list(vSchema) == [
        "atelier",
        "machine",
        "technicien",
        "intervention",
        "piece",
        "piece_utilisee",
    ]
    assert vSchema["intervention"][:3] == ("id", "machine_id", "technicien_id")
