"""Niveaux Maven et Docker : fichier à corriger, commandes simulées, objectif

Chaque niveau donne un fichier de départ (pom.xml ou Dockerfile) et un
objectif. L'état d'un niveau (fichier modifié, hôte Docker, console) est gardé
dans un réglage : le bureau et le web reprennent là où l'on s'était arrêté.
"""

import json
from datetime import datetime
from functools import lru_cache

from config import DEVOPS_LEVELS_FILE
from job.docker_sim import DockerError, is_goal_reached, new_host, run_docker
from job.maven_sim import PHASES, run_maven
from job.progress import DEVOPS_PROGRESS_KEY
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_COMMAND_LENGTH = 300
MAX_FILE_LENGTH = 8000
MAX_CONSOLE_LINES = 300
FILE_NAMES = {"maven": "pom.xml", "docker": "Dockerfile"}
SERIES_ICONS = {"Maven": "code", "Docker": "server"}


@lru_cache(maxsize=1)
def load_levels():
    """Retourne les niveaux livrés, par identifiant, dans l'ordre du fichier."""

    vLevels = json.loads(DEVOPS_LEVELS_FILE.read_text(encoding="utf-8"))

    rLevels = {vLevel["id"]: vLevel for vLevel in vLevels}

    return rLevels


def get_level(pLevelId):
    """Retourne un niveau ; lève ValueError s'il n'existe pas."""

    vLevel = load_levels().get(pLevelId)

    if vLevel is None:
        raise ValueError(f"Niveau inconnu : {pLevelId}")

    return vLevel


def check_maven_goal(pTarget, pReport):
    """Retourne (atteint, explication) de l'objectif d'un niveau Maven."""

    if not pReport["success"] or pReport["phase"] is None:
        return (False, "")

    if PHASES.index(pReport["phase"]) < PHASES.index(pTarget["phase"]):
        return (
            False,
            f"Construction réussie, mais l'objectif demande mvn {pTarget['phase']}.",
        )

    if pReport["skipped_tests"]:
        return (False, "Les tests ont été sautés : l'objectif demande qu'ils passent.")

    if pReport["tests_run"] < pTarget.get("tests_min", 0):
        return (
            False,
            f"{pReport['tests_run']} test exécuté sur {pTarget['tests_min']} : "
            "des tests existent mais ne sont pas lancés.",
        )

    if pTarget.get("jar") and pReport["jar"] != pTarget["jar"]:
        return (
            False,
            f"Le jar produit est {pReport['jar']}, il faut {pTarget['jar']}.",
        )

    for vKey, vScope in pTarget.get("scopes", {}).items():
        if pReport["scopes"].get(vKey) != vScope:
            return (
                False,
                f"Construction réussie, mais {vKey.split(':')[1]} est en scope "
                f"{pReport['scopes'].get(vKey, 'absent')} : il faut {vScope}.",
            )

    rCheck = (True, "")

    return rCheck


def load_devops_progress(pDatabaseFile):
    """Retourne l'état de chaque niveau commencé : fichier, hôte, console, réussite."""

    vLevels = load_json_setting(pDatabaseFile, DEVOPS_PROGRESS_KEY, {}, dict).get(
        "levels"
    )

    rProgress = {"levels": vLevels if isinstance(vLevels, dict) else {}}

    return rProgress


def get_level_view(pDatabaseFile, pLevelId):
    """Retourne le niveau avec son fichier actuel, sa console et sa réussite."""

    vLevel = get_level(pLevelId)
    vEntry = load_devops_progress(pDatabaseFile)["levels"].get(pLevelId) or {}

    rView = {
        "level": vLevel,
        "file_name": FILE_NAMES[vLevel["tool"]],
        "file": vEntry.get("file") or vLevel["file"],
        "console": vEntry.get("console") or [],
        "passed": bool(vEntry.get("passed_at")),
    }

    return rView


def play_step(pLevel, pFile, pCommand, pHost):
    """Joue une commande sur un fichier ; retourne (lignes, objectif atteint, message).

    Pour Docker, l'hôte pHost est modifié sur place. Le téléphone joue la même
    étape en Dart, et le PC rejoue ainsi les parties qu'il reçoit.
    """

    vMessage = ""

    if pLevel["tool"] == "maven":
        vLines, vReport = run_maven(pLevel["project"], pFile, pCommand)
        vReached, vMessage = check_maven_goal(pLevel["target"], vReport)
    else:
        try:
            vLines = run_docker(pHost, pLevel, pFile, pCommand)

        except DockerError as vError:
            vLines = [f"Error: {vError}"]

        vReached = is_goal_reached(pHost, pLevel["target"])

    rStep = (vLines, vReached, vMessage)

    return rStep


def replay_steps(pLevel, pSteps):
    """Rejoue des étapes (fichier, commande) depuis le départ ; indique si l'objectif est atteint."""

    vHost = new_host(pLevel.get("setup", []))
    rReached = False

    for vFile, vCommand in pSteps:
        vCommand = " ".join(vCommand.split())[:MAX_COMMAND_LENGTH]

        if vCommand:
            rReached |= play_step(pLevel, vFile[:MAX_FILE_LENGTH], vCommand, vHost)[1]

    return rReached


def mark_passed(pDatabaseFile, pLevelId, pFile, pNow):
    """Marque un niveau réussi sur un autre appareil ; indique si c'est la première fois."""

    vProgress = load_devops_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}
    rFirst = not vEntry.get("passed_at")

    if rFirst:
        vEntry["passed_at"] = pNow.isoformat(timespec="seconds")
        vEntry.setdefault("file", pFile)
        vProgress["levels"][pLevelId] = vEntry
        save_json_setting(pDatabaseFile, DEVOPS_PROGRESS_KEY, vProgress)
        logger.info("Niveau Maven ou Docker réussi sur le téléphone : %s", pLevelId)

    return rFirst


def run_level_command(pDatabaseFile, pLevelId, pFile, pCommand, pNow=None):
    """Exécute une commande sur le niveau ; retourne lignes, objectif et première réussite."""

    vLevel = get_level(pLevelId)
    vCommand = " ".join(pCommand.split())[:MAX_COMMAND_LENGTH]
    vFile = pFile[:MAX_FILE_LENGTH]
    vProgress = load_devops_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}
    vMessage = ""

    if not vCommand:
        return {
            "lines": [],
            "reached": False,
            "first": False,
            "message": "Saisissez une commande.",
        }

    vHost = vEntry.get("host") or new_host(vLevel.get("setup", []))
    vLines, vReached, vMessage = play_step(vLevel, vFile, vCommand, vHost)

    if vLevel["tool"] == "docker":
        vEntry["host"] = vHost

    vFirst = vReached and not vEntry.get("passed_at")
    vEntry["file"] = vFile
    vEntry["console"] = ((vEntry.get("console") or []) + [f"$ {vCommand}"] + vLines)[
        -MAX_CONSOLE_LINES:
    ]

    if vFirst:
        vEntry["passed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")
        logger.info("Niveau Maven ou Docker réussi : %s", pLevelId)

    vProgress["levels"][pLevelId] = vEntry
    save_json_setting(pDatabaseFile, DEVOPS_PROGRESS_KEY, vProgress)

    rRun = {"lines": vLines, "reached": vReached, "first": vFirst, "message": vMessage}

    return rRun


def reset_level(pDatabaseFile, pLevelId):
    """Remet un niveau à son départ : fichier d'origine, hôte vide, console effacée."""

    get_level(pLevelId)
    vProgress = load_devops_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}

    for vKey in ("file", "host", "console"):
        vEntry.pop(vKey, None)

    vProgress["levels"][pLevelId] = vEntry
    save_json_setting(pDatabaseFile, DEVOPS_PROGRESS_KEY, vProgress)


def build_devops_overview(pDatabaseFile):
    """Retourne les niveaux par série, avec leur état."""

    vProgress = load_devops_progress(pDatabaseFile)
    vSeries = {}

    for vLevel in load_levels().values():
        vEntry = vProgress["levels"].get(vLevel["id"]) or {}
        vSeries.setdefault(vLevel["series"], []).append(
            {
                "id": vLevel["id"],
                "title": vLevel["title"],
                "goal": vLevel["goal"],
                "passed": bool(vEntry.get("passed_at")),
                "started": bool(vEntry.get("console")),
            }
        )

    vGroups = [
        {
            "label": vLabel,
            "icon": SERIES_ICONS.get(vLabel, "terminal"),
            "rows": vRows,
            "done": sum(vRow["passed"] for vRow in vRows),
        }
        for vLabel, vRows in vSeries.items()
    ]

    rOverview = {
        "series": vGroups,
        "passed": sum(vGroup["done"] for vGroup in vGroups),
        "total": len(load_levels()),
    }

    return rOverview
