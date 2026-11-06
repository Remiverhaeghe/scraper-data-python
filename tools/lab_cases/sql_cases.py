"""Cas du bac à sable SQL : niveaux joués dans les deux dialectes."""

import json

from job.sql_levels import load_levels as load_sql_levels
from job.sql_levels import pick
from job.sql_levels import run_level as run_sql_level
from job.sql_sandbox import DIALECTS

# Requêtes jouées dans les deux dialectes sur le premier niveau SQL
SQL_QUERIES = (
    "",
    "-- rien",
    "SELECT * FROM machine",
    "select code, nom from machine order by 1;  -- fin",
    "SELECT code, nom FROM machine ORDER BY nom",
    "SELECT nom 'nom -- pas un commentaire' FROM machine /* note */",
    "SELECT 'L''atelier ; deux' AS texte",
    "SELECT * FROM machin",
    "SELECT id FROM intervention i JOIN machine m ON m.id = i.machine_id",
    "SELECT machine_id FROM intervention WHERE SUM(cout) > 5 GROUP BY machine_id",
    "SELECT machine_id FROM intervention HAVING COUNT(*) > 1",
    "SELECT nom FROM",
    "SELECT nom FROM machine WHERE",
    "SELECT TOP 3 code FROM machine ORDER BY code",
    "SELECT DISTINCT TOP (2) type FROM intervention ORDER BY type",
    "SELECT code FROM machine ORDER BY code LIMIT 3",
    "SELECT id FROM machine WHERE id IN (SELECT TOP 1 id FROM machine)",
    "SELECT ISNULL(atelier_id) FROM technicien",
    "SELECT ISNULL(atelier_id, 0), IFNULL(atelier_id, 0) FROM technicien",
    "SELECT LEN(nom), CHAR_LENGTH(nom), LENGTH(nom) FROM machine WHERE id = 2",
    "SELECT YEAR(debut), MONTH(debut), DAY(debut) FROM intervention WHERE id = 2",
    "SELECT NOW(), CURDATE(), GETDATE(), CURRENT_DATE, CURRENT_TIMESTAMP",
    "SELECT DATEDIFF(fin, debut), DATEDIFF(day, debut, fin) FROM intervention",
    "SELECT TIMESTAMPDIFF(HOUR, debut, fin), TIMESTAMPDIFF(MINUTE, debut, fin) "
    "FROM intervention",
    "SELECT DATEDIFF(hour, debut, fin), DATEDIFF(minute, debut, fin) FROM intervention",
    "SELECT DATEDIFF(month, debut, fin) FROM intervention",
    "SELECT TIMESTAMPDIFF(WEEK, debut, fin) FROM intervention",
    "SELECT DATEDIFF(nom, code) FROM machine",
    "SELECT [nom], `code` FROM machine",
    "SELECT nom || code FROM machine",
    "SELECT CONCAT(prenom, ' ', nom) FROM technicien",
    "SELECT AVG(cout), SUM(cout), MIN(cout), MAX(prix) FROM intervention, piece",
    "SELECT ROUND(prix * 1.05, 2), prix / 3, 1.0 / 8, 0.125, 2.675, -0.004 FROM piece",
    "SELECT COUNT(*) FROM intervention a, intervention b, piece c",
    "SELECT a.id, b.id FROM intervention a, intervention b",
    "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) "
    "SELECT count(*) FROM n",
    "SELECT 1; DROP TABLE machine",
    "SELECT 1;;",
    "ATTACH DATABASE 'copie.db' AS copie",
    "PRAGMA table_info(machine)",
    "SELECT * FROM pragma_table_info('machine')",
    "EXPLAIN SELECT 1",
    "DROP TABLE machine",
    "BEGIN",
    "SELECT name FROM sqlite_master",
    "SELECT zeroblob(10), random(), printf('%d', 1)",
    "SELECT load_extension('x')",
    "VALUES (1, 'a'), (2, 'b')",
    "REPLACE INTO atelier VALUES (9, 'Peinture 2')",
    "DELETE FROM machine",
    "UPDATE piece SET prix = prix * 2 RETURNING reference, prix",
    "INSERT INTO intervention (machine_id) VALUES (1)",
    "INSERT INTO atelier VALUES (1, 'double')",
    "INSERT INTO atelier VALUES (5)",
    "INSERT INTO atelier (id, nom) VALUES (5, 'a', 'b')",
    "SELECT nom FROM machine WHERE nom LIKE '%usinage%'",
    "SELECT CASE WHEN stock = 0 THEN 'rupture' END FROM piece",
    "SELECT hex('é'), upper('éà'), lower('ÉÀ'), length('été')",
    "SELECT typeof(1), typeof(1.5), typeof('x'), typeof(NULL)",
    "SELECT abs(-3), max(1, 2.5), min('a', 'b'), coalesce(NULL, 3)",
    "SELECT substr('maintenance', 1, 5), replace('a-b', '-', '+'), trim('  x  ')",
    "SELECT ROW_NUMBER() OVER (ORDER BY id), id FROM machine",
    "SELECT \x00",
    "SELECT '" + "x" * 300 + "' AS long_texte",
    "SELECT " + " + ".join(["1"] * 1500),
)


def build_sql_cases():
    """Retourne les cas SQL : solutions, départs, autre dialecte, requêtes variées."""

    rCases = []
    vLevels = list(load_sql_levels().values())

    for vIndex, vLevel in enumerate(vLevels):
        for vDialect in DIALECTS:
            vOther = "sqlserver" if vDialect == "mysql" else "mysql"
            vQueries = [
                ("solution", pick(vLevel, "solution", vDialect)),
                ("départ", vLevel["starter"]),
            ]

            if isinstance(vLevel["solution"], dict):
                vQueries.append(("autre dialecte", pick(vLevel, "solution", vOther)))

            if vIndex == 0:
                vQueries += [
                    (f"requête {vNumber}", vQuery)
                    for vNumber, vQuery in enumerate(SQL_QUERIES, 1)
                ]

            rCases += [
                {
                    "name": f"{vLevel['id']} : {vDialect}, {vName}",
                    "level": vLevel["id"],
                    "dialect": vDialect,
                    "query": vQuery,
                    "expected": json.loads(
                        json.dumps(run_sql_level(vLevel, vQuery, vDialect))
                    ),
                }
                for vName, vQuery in vQueries
            ]

    return rCases
