"""Tests des simulateurs Maven et Docker et de leurs niveaux"""

from datetime import datetime

import pytest

from job.devops_levels import (
    build_devops_overview,
    check_maven_goal,
    get_level_view,
    load_levels,
    reset_level,
    run_level_command,
)
from job.docker_sim import DockerError, is_goal_reached, new_host, run_docker
from job.maven_sim import parse_pom, run_maven
from job.progress import load_activity
from storage.database import initialize_database

LEVELS = load_levels()


def play(pLevel, pFile, pCommands):
    """Joue des commandes sur un niveau ; retourne (objectif atteint, dernière sortie)."""

    vHost = new_host(pLevel.get("setup", []))
    vReport = None
    vLines = []

    for vCommand in pCommands:
        if pLevel["tool"] == "maven":
            vLines, vReport = run_maven(pLevel["project"], pFile, vCommand)
            continue

        try:
            vLines = run_docker(vHost, pLevel, pFile, vCommand)

        except DockerError as vError:
            vLines = [str(vError)]

    vReached = (
        check_maven_goal(pLevel["target"], vReport)[0]
        if pLevel["tool"] == "maven"
        else is_goal_reached(vHost, pLevel["target"])
    )

    return (vReached, vLines)


@pytest.mark.parametrize("pLevel", list(LEVELS.values()))
def test_every_solution_reaches_its_goal(pLevel):
    """Vérifie que le fichier et les commandes de la solution atteignent l'objectif."""

    assert play(pLevel, pLevel["solution"], pLevel["commands"])[0]


@pytest.mark.parametrize(
    ("pLevelId", "pCommands", "pMessage"),
    [
        ("maven-coordonnees", ["mvn package"], "'artifactId' is missing"),
        ("maven-dependance", ["mvn package"], "BUILD FAILURE"),
        ("maven-java", ["mvn compile"], "BUILD FAILURE"),
        ("maven-surefire", ["mvn package"], "BUILD SUCCESS"),
        ("maven-conflit", ["mvn test"], "There are test failures."),
        (
            "docker-premier",
            ["docker build -t atelier:1.0 .", "curl localhost:8080"],
            "refused",
        ),
        (
            "docker-arret",
            ["docker build -t a:1 .", "docker run -d --name a a:1", "docker logs a"],
            "Unable to access jarfile app.jar",
        ),
        (
            "docker-port-pris",
            ["docker build -t a:1 .", "docker run -d -p 8080:8080 a:1"],
            "port is already allocated",
        ),
        (
            "docker-python",
            ["docker build -t c:1 ."],
            "Could not open requirements file",
        ),
        (
            "docker-variable",
            ["docker build -t a:1 .", "docker run -d --name a a:1", "docker logs a"],
            "DB_URL",
        ),
        (
            "docker-volume",
            [
                "docker build -t a:1 .",
                "docker run -d --name a -p 8080:8080 a:1",
                "curl -X POST localhost:8080/mesures",
                "docker rm -f a",
                "docker run -d --name a -p 8080:8080 a:1",
                "curl localhost:8080/mesures",
            ],
            '"mesures": 0',
        ),
    ],
)
def test_starting_point_fails_like_the_real_tool(pLevelId, pCommands, pMessage):
    """Vérifie l'erreur typique du départ de chaque niveau, et l'objectif non atteint."""

    vLevel = LEVELS[pLevelId]
    vReached, vLines = play(vLevel, vLevel["file"], pCommands)

    assert not vReached
    assert any(pMessage in vLine for vLine in vLines)


def test_pom_details_and_dependency_tree():
    """Vérifie les propriétés, le pom illisible et l'arbre avec la version écartée."""

    vLevel = LEVELS["maven-conflit"]
    vTree = run_maven(vLevel["project"], vLevel["file"], "mvn dependency:tree")[0]

    assert parse_pom(LEVELS["maven-java"]["file"])["properties"] == {
        "maven.compiler.release": "8"
    }
    assert "Non-parseable POM" in run_maven({}, "<project>", "mvn package")[0][1]
    assert any("omitted for conflict with 2.9.10" in vLine for vLine in vTree)
    assert "Unknown lifecycle phase" in run_maven({}, "", "mvn deploy-all")[0][0]


def test_docker_commands_keep_a_coherent_host():
    """Vérifie conteneur en double, suppression refusée, ps et ports publiés."""

    vLevel = LEVELS["docker-premier"]
    vHost = new_host()
    run_docker(vHost, vLevel, vLevel["solution"], "docker build -t atelier:1.0 .")
    run_docker(vHost, vLevel, "", "docker run -d --name a -p 8080:8080 atelier:1.0")

    with pytest.raises(DockerError, match="already in use"):
        run_docker(vHost, vLevel, "", "docker run -d --name a atelier:1.0")

    with pytest.raises(DockerError, match="force remove"):
        run_docker(vHost, vLevel, "", "docker rm a")

    assert "0.0.0.0:8080->8080/tcp" in run_docker(vHost, vLevel, "", "docker ps")[1]
    assert run_docker(vHost, vLevel, "", "curl http://localhost:8080/") == [
        '{"application": "suivi-machines", "statut": "ok"}'
    ]

    with pytest.raises(DockerError, match="unknown instruction: COPPY"):
        run_docker(
            vHost, vLevel, "FROM alpine:3.20\nCOPPY a b\n", "docker build -t x ."
        )


def test_progress_keeps_the_file_console_and_success(tmp_path):
    """Vérifie l'état gardé entre deux commandes, la réussite datée et la remise à zéro."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vLevel = LEVELS["docker-premier"]
    vNow = datetime(2026, 10, 30, 9, 0)

    for vCommand in vLevel["commands"][:-1]:
        assert not run_level_command(
            vDatabaseFile, vLevel["id"], vLevel["solution"], vCommand, vNow
        )["reached"]

    vRun = run_level_command(
        vDatabaseFile, vLevel["id"], vLevel["solution"], vLevel["commands"][-1], vNow
    )
    vView = get_level_view(vDatabaseFile, vLevel["id"])

    assert vRun["reached"] and vRun["first"]
    assert vView["file"] == vLevel["solution"]
    assert vView["console"][0] == "$ docker build -t atelier:1.0 ."
    assert build_devops_overview(vDatabaseFile)["passed"] == 1
    assert load_activity(vDatabaseFile)[vNow.date()]["xp"] == 20

    reset_level(vDatabaseFile, vLevel["id"])

    assert get_level_view(vDatabaseFile, vLevel["id"])["console"] == []
    assert get_level_view(vDatabaseFile, vLevel["id"])["passed"]
