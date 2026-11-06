"""Tests des niveaux du bac à sable SQL : solutions, erreurs classiques, progression"""

from datetime import datetime

import pytest

from job.achievements import ACHIEVEMENTS
from job.progress import load_activity
from job.sql_levels import (
    build_sql_overview,
    get_expected,
    get_level,
    load_levels,
    load_sql_progress,
    pick,
    run_level,
    save_attempt,
    save_dialect,
)
from storage.database import initialize_database

OTHER_DIALECT = {"mysql": "sqlserver", "sqlserver": "mysql"}


@pytest.mark.parametrize("pDialect", ["mysql", "sqlserver"])
def test_every_solution_passes_and_starter_fails(pDialect):
    """Vérifie chaque niveau : solution réussie, point de départ refusé."""

    for vLevel in load_levels().values():
        vSolution = run_level(vLevel, pick(vLevel, "solution", pDialect), pDialect)
        vStarter = run_level(vLevel, vLevel["starter"], pDialect)

        assert vSolution["passed"], (vLevel["id"], vSolution["message"])
        assert not get_expected(vLevel["id"], pDialect)["error"]
        assert vSolution["expected"]["rows"], vLevel["id"]
        assert not vStarter["passed"], vLevel["id"]


@pytest.mark.parametrize("pLevelId", ["plus-cheres", "non-affecte", "depuis-combien"])
@pytest.mark.parametrize("pDialect", ["mysql", "sqlserver"])
def test_solution_of_the_other_dialect_is_refused(pLevelId, pDialect):
    """Vérifie qu'une écriture propre à l'autre dialecte échoue avec une explication."""

    vLevel = get_level(pLevelId)
    vRun = run_level(
        vLevel, pick(vLevel, "solution", OTHER_DIALECT[pDialect]), pDialect
    )

    assert not vRun["passed"]
    assert vRun["result"]["error"]


def test_hour_durations_depend_on_the_dialect():
    """Vérifie le niveau des durées : 18 heures en MySQL, 19 en SQL Server."""

    assert get_expected("duree-heures", "mysql")["rows"][0] == (2, 18)
    assert get_expected("duree-heures", "sqlserver")["rows"][0] == (2, 19)


@pytest.mark.parametrize(
    ("pLevelId", "pQuery", "pAdvice"),
    [
        (
            "en-cours",
            "SELECT id, machine_id, debut FROM intervention WHERE fin = NULL",
            "IS NULL",
        ),
        (
            "ateliers-machines",
            "SELECT a.nom, COUNT(*) FROM atelier a "
            "LEFT JOIN machine m ON m.atelier_id = a.id GROUP BY a.id",
            "COUNT(m.id)",
        ),
        (
            "sans-intervention",
            "SELECT nom, prenom FROM technicien "
            "WHERE id NOT IN (SELECT technicien_id FROM intervention)",
            "NOT EXISTS",
        ),
        (
            "sous-le-minimum",
            "SELECT reference, stock, stock_mini FROM piece WHERE stock <= stock_mini",
            "pas <=",
        ),
        (
            "machines-differentes",
            "SELECT technicien_id, COUNT(*), COUNT(machine_id) FROM intervention "
            "WHERE technicien_id IS NOT NULL GROUP BY technicien_id",
            "COUNT(DISTINCT machine_id)",
        ),
        (
            "cout-moyen",
            "SELECT type, ROUND(AVG(IFNULL(cout, 0)), 2) FROM intervention "
            "GROUP BY type",
            "AVG ignore déjà les NULL",
        ),
        (
            "binomes",
            "SELECT a.nom, b.nom, a.specialite FROM technicien a "
            "JOIN technicien b ON b.specialite = a.specialite AND a.id <> b.id",
            "a.id < b.id",
        ),
        (
            "categories-cout",
            "SELECT id, CASE WHEN cout < 100 THEN 'faible' WHEN cout < 500 "
            "THEN 'moyen' ELSE 'élevé' END FROM intervention ORDER BY id",
            "cout IS NULL",
        ),
        (
            "intervention-precedente",
            "SELECT machine_id, id, debut, LAG(debut) OVER (ORDER BY debut) "
            "FROM intervention ORDER BY machine_id, debut",
            "PARTITION BY machine_id",
        ),
        (
            "affecter-technicien",
            "UPDATE intervention SET technicien_id = 6 "
            "WHERE fin IS NULL AND technicien_id = NULL",
            "IS NULL",
        ),
        (
            "cloturer",
            "UPDATE intervention SET fin = NOW(), cout = 350",
            "id = 17",
        ),
    ],
)
def test_classic_mistakes_fail_with_advice(pLevelId, pQuery, pAdvice):
    """Vérifie les erreurs classiques : refusées, avec le conseil qui les explique."""

    vRun = run_level(get_level(pLevelId), pQuery, "mysql")

    assert not vRun["passed"]
    assert any(pAdvice in vAdvice for vAdvice in vRun["advice"])


def test_other_queries_with_the_same_rows_pass():
    """Vérifie qu'une autre écriture qui renvoie les mêmes lignes est acceptée."""

    assert run_level(
        get_level("sans-intervention"),
        "SELECT t.nom, t.prenom FROM technicien t "
        "LEFT JOIN intervention i ON i.technicien_id = t.id WHERE i.id IS NULL",
        "mysql",
    )["passed"]
    assert run_level(
        get_level("nouvelle-intervention"),
        "INSERT INTO intervention (machine_id, technicien_id, type, debut) "
        "VALUES (1, 1, 'preventive', NOW())",
        "mysql",
    )["passed"]
    assert run_level(
        get_level("tableau-croise"),
        "SELECT machine_id, COUNT(CASE WHEN type = 'preventive' THEN 1 END), "
        "COUNT(CASE WHEN type = 'corrective' THEN 1 END) FROM intervention "
        "GROUP BY machine_id ORDER BY machine_id",
        "sqlserver",
    )["passed"]
    assert run_level(
        get_level("part-atelier"),
        "SELECT a.nom, ROUND(100.0 * SUM(i.cout) / SUM(SUM(i.cout)) OVER (), 1) "
        "FROM intervention i JOIN machine m ON m.id = i.machine_id "
        "JOIN atelier a ON a.id = m.atelier_id GROUP BY a.id, a.nom",
        "mysql",
    )["passed"]
    assert run_level(
        get_level("cloturer"),
        "UPDATE intervention SET cout = 350, fin = '2026-06-30 08:00:00' "
        "WHERE id = 17",
        "sqlserver",
    )["passed"]


def test_write_levels_check_the_table_and_select_levels_refuse_writes():
    """Vérifie un UPDATE sans WHERE refusé et une écriture dans un niveau SELECT."""

    vUpdate = run_level(
        get_level("hausse-prix"), "UPDATE piece SET prix = prix * 1.05", "mysql"
    )
    vDelete = run_level(get_level("selection"), "DELETE FROM machine", "mysql")

    assert not vUpdate["passed"]
    assert vUpdate["result"]["changed"] == 11
    assert "attend une requête SELECT" in vDelete["message"]


def test_progress_dialect_and_points(tmp_path):
    """Vérifie dialecte enregistré, première réussite datée, XP et trophée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert build_sql_overview(vDatabaseFile)["dialect"] == "mysql"

    save_dialect(vDatabaseFile, "sqlserver")

    with pytest.raises(ValueError):
        save_dialect(vDatabaseFile, "oracle")

    vNow = datetime(2026, 10, 30, 9, 0)

    assert save_attempt(vDatabaseFile, "selection", "SELECT 1", False, vNow) is False
    assert save_attempt(vDatabaseFile, "selection", "SELECT code", True, vNow) is True
    assert save_attempt(vDatabaseFile, "selection", "SELECT nom", True, vNow) is False

    vProgress = load_sql_progress(vDatabaseFile)
    vOverview = build_sql_overview(vDatabaseFile)

    assert vProgress["dialect"] == "sqlserver"
    assert vProgress["levels"]["selection"]["query"] == "SELECT nom"
    assert vOverview["passed"] == 1
    assert vOverview["total"] == len(load_levels())
    assert vOverview["series"][0]["rows"][0]["query"] == "SELECT nom"
    vSecond = vOverview["series"][0]["rows"][1]

    assert vSecond["query"] == get_level(vSecond["id"])["starter"]
    assert load_activity(vDatabaseFile)[vNow.date()]["xp"] == 15
    assert {vEntry[0] for vEntry in ACHIEVEMENTS} >= {"sql-first", "sql-all"}
    assert [vEntry[5] for vEntry in ACHIEVEMENTS if vEntry[0] == "sql-all"] == [
        len(load_levels())
    ]


def test_expected_headers_do_not_give_the_answer():
    """Vérifie que seuls les noms de colonnes simples restent affichés."""

    vRun = run_level(get_level("ateliers-machines"), "SELECT 1", "mysql")

    assert vRun["expected"]["columns"] == ["nom", "colonne 2"]
