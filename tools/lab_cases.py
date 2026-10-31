"""Cas communs aux simulateurs Python et Dart : python -m tools.lab_cases

Écrit tests/fixtures/shared_lab_cases.json depuis les simulateurs de
référence. tests/job/test_shared_lab_cases.py vérifie que le fichier est à
jour, mobile/test/shared_lab_cases_test.dart que le téléphone donne les mêmes
résultats.
"""

import json
from dataclasses import asdict
from pathlib import Path

from job.mobile_labs import build_sql_rules
from job.sql_levels import load_levels as load_sql_levels
from job.sql_levels import pick
from job.sql_levels import run_level as run_sql_level
from job.sql_sandbox import DIALECTS, load_script
from job.devops_levels import load_levels as load_devops_levels
from job.devops_levels import play_step
from job.docker_sim import REGISTRY, new_host
from job.git_graph import render_graph
from job.git_levels import LEVELS as GIT_LEVELS
from job.git_levels import is_goal_reached
from job.git_sandbox import describe_worktree, replay, run_command
from job.ladder import parse_program, render_svg
from job.maven_sim import CENTRAL
from job.ladder_game import (
    Simulator,
    get_names,
    load_levels,
    render_chronogram,
    run_level,
)
from job.troubleshooting import load_scenarios, play_scenario

FIXTURE_FILE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "shared_lab_cases.json"
)
RESULT_KEYS = ("done", "wrong", "log", "minutes", "solved", "proven", "score", "stars")
RUN_KEYS = ("passed", "error", "line", "checks", "violations", "signals", "samples")
# Commandes Git jouées à la suite sur chaque niveau, bonnes ou fautives
GIT_COMMANDS = (
    "git status",
    "git log",
    "git diff",
    "git branch",
    "modifier notes.txt",
    "modifier réglages.yml",
    "git stash",
    "git stash list",
    "git stash pop",
    "git add notes.txt",
    "git restore --staged notes.txt",
    "git commit",
    "git commit -am 'premier jet'",
    'git commit -m "message \\"cité\\""',
    "git switch -c essai",
    "modifier notes.txt",
    "git commit -a",
    "git switch main",
    "git merge essai",
    "git merge --abort",
    "git rebase essai",
    "git cherry-pick essai",
    "git checkout --ours notes.txt",
    "git reset --soft HEAD~1",
    "git status",
    "git reset --hard HEAD~1",
    "git revert HEAD",
    "git checkout C0",
    "git switch --detach HEAD^",
    "git branch -f essai C1",
    "git branch -d essai",
    "git push",
    "git pull --rebase",
    "git fetch",
    "git bisect",
    "git commit --amend",
    "rm -rf /",
    'git commit -m "non fermé',
    "modifier ../secret",
    "git log --oneline",
    "git merge couleur",
    "git status",
    "git switch main",
    "git checkout --theirs app.py",
    "git add .",
    "git commit",
    "git rebase --continue",
    "git stash pop",
)
# Commandes Maven et Docker jouées à la suite sur chaque niveau
MAVEN_COMMANDS = (
    "mvn compile",
    "mvn test",
    "mvn package -DskipTests",
    "mvn dependency:tree",
    "mvn clean install",
    "mvn -q verify",
    "mvn deploy",
    "mvn",
    "ls -la",
    "mvn   validate",
)
DOCKER_COMMANDS = (
    "docker images",
    "docker ps",
    "docker build .",
    "docker build -t essai .",
    "docker run essai",
    "docker run -d --name a -p 8080:8080 -v donnees:/app/data -e DB_URL=x "
    "-e SERVER_PORT=9090 essai",
    "curl http://localhost:8080/",
    "curl localhost:9090/",
    "docker ps -a",
    "docker logs a",
    "docker logs inconnu",
    "docker stop a",
    "docker start a",
    "docker restart a",
    "docker rm a",
    "docker rm -f a",
    "docker volume ls",
    "docker volume create v1",
    "docker volume rm v1",
    "docker pull nginx:1.27",
    "docker pull inconnu",
    "docker run -d -p 80 nginx",
    "docker run -d -p 8081:80 nginx:1.27",
    "curl -X POST http://localhost:8081/mesures",
    "docker run --frob x",
    "docker run -p",
    "docker run -v data:relatif x",
    "docker exec a ls",
    "kubectl get pods",
    "curl ftp://x",
    'docker run "non fermé',
    "docker run -d --name b alpine:3.20",
    "docker logs b",
)
# Fichiers piégeux, joués avec mvn package sur le premier niveau Maven
POM_VARIANTS = (
    "<project>",
    "<project><a></b></project>",
    "<project>&foo;</project>",
    "<project>&#1114112;</project>",
    "<!DOCTYPE x><project/>",
    "<project/> en trop",
    "",
    "﻿<?xml version='1.0'?><!-- note --><p:project xmlns:p='x'>"
    "<p:modelVersion>4.0.0</p:modelVersion></p:project>",
    "<project><modelVersion>4.0.0</modelVersion><groupId>fr.a</groupId>"
    "<artifactId>&#233;t&#xE9;</artifactId><version><![CDATA[1.0]]></version>"
    "<properties><v>2</v></properties><dependencies><dependency>"
    "<groupId>org.apache.commons</groupId><artifactId>commons-lang3</artifactId>"
    "<version>${v}</version><scope>runtimme</scope></dependency><dependency>"
    "<groupId>x</groupId><artifactId>y</artifactId></dependency></dependencies>"
    "</project>",
    "<project><modelVersion>4.0.0</modelVersion><groupId>fr.a</groupId>"
    "<artifactId>a</artifactId><version>1</version><build><plugins><plugin>"
    "<artifactId>maven-compiler-plugin</artifactId><configuration>"
    "<release>1.8</release></configuration></plugin></plugins></build>"
    "<dependencies><dependency><groupId>x</groupId><artifactId>y</artifactId>"
    "<version>1</version></dependency></dependencies></project>",
    "<project " + "a='b' " * 2000 + "/>",
    "<project><groupId attr=sans-guillemets>x</groupId></project>",
)
# Dockerfiles piégeux, joués sur le premier niveau Docker
DOCKERFILE_VARIANTS = (
    "",
    "COPPY a b",
    "FROM inconnu",
    "FROM alpine:3.20\nRUN apt-get install x",
    "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n"
    "RUN pip install -r requirements.txt\nCMD python app.py",
    "FROM eclipse-temurin:21-jre\nCMD",
    "# image\nFROM eclipse-temurin:21-jre \\\n  AS base\nWORKDIR app\nWORKDIR ../srv\n"
    'ENV DB_URL "jdbc:x"\nENV SERVER_PORT=8080\nEXPOSE 80/tcp abc 8080\n'
    "COPY ./target/*.jar ./pom.xml /srv/\nENTRYPOINT java -jar\n"
    'CMD ["suivi-machines-1.0.0.jar"]',
    'FROM eclipse-temurin:21-jre\nCMD ["java", "-jar",',
    "FROM eclipse-temurin:21-jre\nCOPY target/ /app/\nCOPY src /code\n"
    "WORKDIR /app\nCMD java -jar suivi-machines-1.0.0.jar",
    "ARG V\nFROM eclipse-temurin:17-jre\nCOPY absent.jar app.jar",
    'FROM alpine:3.20\nCMD ["/bin/sh", "-c"]',
)
DOCKERFILE_COMMANDS = (
    "docker build -t v .",
    "docker run -d --name v -p 8080:8080 v",
    "docker logs v",
    "curl localhost:8080",
)
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
# Cycles joués avant de dessiner le ladder coloré, comme pendant une simulation
LIVE_CYCLES = 15
# Programmes fautifs, joués sur le premier niveau
WRONG_PROGRAMS = (
    "moteur = !(marche)",
    "marche = arret",
    "t = TON(marche, 0s)",
    "moteur = marche &",
    "SET = marche",
    "moteur = marche ¤ arret",
    "Moteur = marche",
    "lot = CTU(marche, 0)",
    "moteur = (marche | moteur) & arret arret",
    "# rien que des commentaires\n\n",
)

# Scénarios d'essai : arrondis à la moitié, où Python arrondit au pair
ROUNDING_SCENARIOS = (
    {
        "id": "essai-arrondi-bas",
        "best_minutes": 1,
        "checks": [
            {
                "id": "mesure",
                "label": "Mesure",
                "minutes": 8,
                "result": "ok",
                "evidence": True,
            }
        ],
        "causes": [{"id": "reparer", "label": "Réparer", "minutes": 0, "right": True}],
    },
    {
        "id": "essai-arrondi-haut",
        "best_minutes": 3,
        "checks": [
            {
                "id": "mesure",
                "label": "Mesure",
                "minutes": 8,
                "result": "ok",
                "evidence": True,
            }
        ],
        "causes": [{"id": "reparer", "label": "Réparer", "minutes": 0, "right": True}],
    },
)


def get_right_cause(pScenario):
    """Retourne la bonne réparation d'un scénario."""

    rCause = next(vCause for vCause in pScenario["causes"] if vCause.get("right"))

    return rCause


def build_paths(pScenario):
    """Retourne les parties à rejouer : (nom, actions)."""

    vChecks = {vCheck["id"]: vCheck for vCheck in pScenario["checks"]}
    vRight = f"repair:{get_right_cause(pScenario)['id']}"
    vEvidence = min(
        (vCheck for vCheck in pScenario["checks"] if vCheck.get("evidence")),
        key=lambda pCheck: pCheck["minutes"]
        + (vChecks[pCheck["requires"]]["minutes"] if pCheck.get("requires") else 0),
    )
    vShortest = (
        [f"check:{vEvidence['requires']}"] if vEvidence.get("requires") else []
    ) + [f"check:{vEvidence['id']}", vRight]
    vWrong = [
        f"repair:{vCause['id']}"
        for vCause in pScenario["causes"]
        if not vCause.get("right")
    ][:1]

    rPaths = [
        ("chemin le plus court", vShortest),
        ("réparation sans preuve", [vRight]),
        (
            "toutes les mesures, une erreur, puis une action ignorée",
            [f"check:{vCheck['id']}" for vCheck in pScenario["checks"]]
            + vWrong
            + vWrong
            + [vRight, f"check:{pScenario['checks'][0]['id']}"],
        ),
    ]

    return rPaths


def build_ladder_expected(pLevel, pProgram):
    """Retourne ce que le téléphone doit retrouver : test, dessins et chronogramme."""

    vRun = run_level(pLevel, pProgram)
    rExpected = {vKey: vRun[vKey] for vKey in RUN_KEYS if vKey in vRun}

    if vRun["error"]:
        return rExpected

    vInputs = set(get_names(pLevel, "input"))
    vRungs = parse_program(pProgram, vInputs)
    vSimulator = Simulator(pLevel, vRungs)

    for _ in range(LIVE_CYCLES):
        vSimulator.step()

    rExpected["ladder_svg"] = render_svg(vRungs)
    rExpected["live_svg"] = render_svg(vRungs, vSimulator.values)
    rExpected["chart_svg"] = render_chronogram(
        vRun["signals"], vRun["samples"], vInputs
    )

    return rExpected


def build_cases():
    """Retourne les cas de toutes les simulations portées sur le téléphone."""

    vCases = []

    for vScenario in [*load_scenarios().values(), *ROUNDING_SCENARIOS]:
        for vName, vActions in build_paths(vScenario):
            vState = play_scenario(vScenario, vActions)
            vCases.append(
                {
                    "name": f"{vScenario['id']} : {vName}",
                    "scenario": vScenario["id"],
                    "actions": vActions,
                    "expected": {vKey: vState[vKey] for vKey in RESULT_KEYS},
                }
            )

    vLadder = []

    for vIndex, vLevel in enumerate(load_levels().values()):
        vPrograms = [
            ("solution", vLevel["solution"]),
            ("départ", vLevel["starter"]),
            (
                "temporisations arrondies",
                vLevel["solution"].replace("2s", "0.25s").replace("1s", "350ms"),
            ),
        ]

        if vIndex == 0:
            vPrograms += [
                (f"faute {vNumber}", vText)
                for vNumber, vText in enumerate(WRONG_PROGRAMS, 1)
            ]

        for vName, vProgram in vPrograms:
            vLadder.append(
                {
                    "name": f"{vLevel['id']} : {vName}",
                    "level": vLevel["id"],
                    "program": vProgram,
                    "expected": build_ladder_expected(vLevel, vProgram),
                }
            )

    rCases = {
        "description": "Cas communs aux simulateurs Python et Dart, générés par "
        "python -m tools.lab_cases : ne pas modifier à la main.",
        "extra_scenarios": list(ROUNDING_SCENARIOS),
        "troubleshooting": vCases,
        "ladder": vLadder,
        "sql_content": {
            "levels": list(load_sql_levels().values()),
            "script": load_script(),
            "rules": build_sql_rules(),
        },
        "sql": build_sql_cases(),
        "devops_content": {
            "levels": list(load_devops_levels().values()),
            "central": CENTRAL,
            "registry": REGISTRY,
        },
        "devops": build_devops_cases(),
        "git_levels": [asdict(vLevel) for vLevel in GIT_LEVELS],
        "git": [
            build_git_case(vLevel, vName, vCommands)
            for vLevel in GIT_LEVELS
            for vName, vCommands in (
                ("solution", vLevel.solution),
                ("commandes variées", GIT_COMMANDS),
            )
        ],
    }

    return rCases


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


def build_devops_case(pLevel, pName, pSteps):
    """Joue des étapes (fichier, commande) : console, objectif, message, hôte final."""

    vHost = new_host(pLevel.get("setup", []))
    vSteps = []

    for vFile, vCommand in pSteps:
        vLines, vReached, vMessage = play_step(pLevel, vFile, vCommand, vHost)
        vSteps.append(
            {
                "file": vFile,
                "command": vCommand,
                "lines": vLines,
                "reached": vReached,
                "message": vMessage,
            }
        )

    rCase = {
        "name": f"{pLevel['id']} : {pName}",
        "level": pLevel["id"],
        "steps": vSteps,
        "host": vHost,
    }

    return rCase


def build_devops_cases():
    """Retourne les cas Maven et Docker : solution, départ, commandes, fichiers piégeux."""

    rCases = []
    vVariantsPlayed = set()

    for vLevel in load_devops_levels().values():
        vCommands = MAVEN_COMMANDS if vLevel["tool"] == "maven" else DOCKER_COMMANDS
        vSeries = [
            (
                "solution",
                [(vLevel["solution"], vCommand) for vCommand in vLevel["commands"]],
            ),
            ("départ", [(vLevel["file"], vCommand) for vCommand in vLevel["commands"]]),
            (
                "commandes variées",
                [(vLevel["solution"], vCommand) for vCommand in vCommands],
            ),
        ]

        if vLevel["tool"] not in vVariantsPlayed:
            vVariantsPlayed.add(vLevel["tool"])
            vSeries += [
                (
                    f"fichier piégeux {vIndex}",
                    [(vFile, vCommand) for vCommand in vPlayed],
                )
                for vIndex, (vFile, vPlayed) in enumerate(
                    (
                        [(vPom, ("mvn package",)) for vPom in POM_VARIANTS]
                        if vLevel["tool"] == "maven"
                        else [
                            (vText, DOCKERFILE_COMMANDS)
                            for vText in DOCKERFILE_VARIANTS
                        ]
                    ),
                    1,
                )
            ]

        rCases += [
            build_devops_case(vLevel, vName, vSteps) for vName, vSteps in vSeries
        ]

    return rCases


def build_git_case(pLevel, pName, pCommands):
    """Rejoue des commandes sur un niveau Git : message, fichiers, objectif, graphes."""

    vRepository = replay(pLevel.setup)
    vSteps = []

    for vCommand in pCommands:
        try:
            vStep = {"command": vCommand, "message": run_command(vRepository, vCommand)}

        except ValueError as vError:
            vStep = {"command": vCommand, "error": str(vError)}

        vStep["worktree"] = describe_worktree(vRepository)
        vStep["reached"] = is_goal_reached(pLevel, vRepository)
        vSteps.append(vStep)

    rCase = {
        "name": f"{pLevel.id} : {pName}",
        "level": pLevel.id,
        "steps": vSteps,
        "graph": render_graph(vRepository.local_view(), "Votre dépôt"),
        "server": (
            render_graph(vRepository.server_view(), "Serveur", pShowHead=False)
            if vRepository.remote
            else ""
        ),
        "goal": render_graph(
            replay(pLevel.setup + pLevel.solution).local_view(), "Objectif"
        ),
    }

    return rCase


def main():
    """Écrit le fichier des cas communs."""

    FIXTURE_FILE.write_text(
        json.dumps(build_cases(), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Cas écrits dans {FIXTURE_FILE}")


if __name__ == "__main__":
    main()
