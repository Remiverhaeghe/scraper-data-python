"""Simulations de l'application mobile : contenu à emporter, parties à intégrer

Le téléphone joue hors ligne avec sa propre version de chaque simulateur, en
Dart. Le contenu (scénarios, niveaux) vient d'ici, seul endroit où il se
modifie. Au retour, le PC ne croit pas le résultat annoncé : il rejoue la
partie avec le simulateur de référence, puis l'enregistre comme sur le bureau.
"""

from dataclasses import asdict
from datetime import datetime

from job.devops_levels import build_devops_overview
from job.devops_levels import load_levels as load_devops_levels
from job.devops_levels import mark_passed, replay_steps
from job.docker_sim import REGISTRY
from job.git_levels import LEVELS as GIT_LEVELS
from job.git_levels import get_level as get_git_level
from job.git_levels import is_goal_reached, replay_level
from job.ladder_game import build_ladder_overview, load_levels, run_level
from job.ladder_game import save_attempt as save_ladder_attempt
from job.maven_sim import CENTRAL
from job.progress import TROUBLESHOOTING_XP_PER_TEN, XP_RULES
from job.sql_levels import build_schema, build_sql_overview
from job.sql_levels import load_levels as load_sql_levels
from job.sql_levels import run_level as run_sql_level
from job.sql_levels import save_attempt as save_sql_attempt
from job.sql_sandbox import (
    ALLOWED_STATEMENTS,
    DIALECTS,
    ERROR_MESSAGES,
    INTERNAL_WRITE_PATTERN,
    MAX_CELL_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_ROWS,
    MAX_VALUE_LENGTH,
    NOT_ALLOWED_MESSAGE,
    RECURSIVE_MESSAGE,
    REFUSED,
    REFUSED_FUNCTIONS,
    REWRITES,
    TODAY,
    UNIT_FUNCTIONS,
    UNITS,
    load_script,
)
from job.troubleshooting import (
    STAR_THRESHOLDS,
    UNPROVEN_SCORE,
    WRONG_REPAIR_PENALTY,
    build_overview,
    load_scenarios,
    play,
    save_result,
)
from storage.git_levels import get_git_level_results, save_git_level_result
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Identifiants des parties déjà intégrées : un envoi répété n'est pas compté deux fois
RECEIVED_KEY = "mobile_lab_ids"
MAX_RECEIVED = 1000
MAX_RESULTS_PER_SYNC = 200
MAX_ACTIONS = 100
MAX_PROGRAM_LENGTH = 4000


def build_labs_package(pDatabaseFile):
    """Retourne le contenu des simulations et ce qui est déjà réussi sur le PC."""

    rPackage = {
        "troubleshooting": {
            "scenarios": list(load_scenarios().values()),
            "rules": {
                "wrong_penalty": WRONG_REPAIR_PENALTY,
                "unproven_score": UNPROVEN_SCORE,
                "star_thresholds": list(STAR_THRESHOLDS),
                "xp_base": XP_RULES["troubleshooting"][1],
                "xp_per_ten": TROUBLESHOOTING_XP_PER_TEN,
            },
            "best": {
                vRow["id"]: vRow["best"]
                for vRow in build_overview(pDatabaseFile)["rows"]
                if vRow["best"] is not None
            },
        },
        "ladder": {
            "levels": list(load_levels().values()),
            "xp": XP_RULES["ladder_level"][1],
            "passed": [
                vRow["id"]
                for vRow in build_ladder_overview(pDatabaseFile)["rows"]
                if vRow["passed"]
            ],
        },
        "git": {
            "levels": [asdict(vLevel) for vLevel in GIT_LEVELS],
            "xp": XP_RULES["git_level"][1],
            "best": get_git_level_results(pDatabaseFile),
        },
        "devops": {
            "levels": list(load_devops_levels().values()),
            "central": CENTRAL,
            "registry": REGISTRY,
            "xp": XP_RULES["devops_level"][1],
            "passed": [
                vRow["id"]
                for vSeries in build_devops_overview(pDatabaseFile)["series"]
                for vRow in vSeries["rows"]
                if vRow["passed"]
            ],
        },
        "sql": build_sql_package(pDatabaseFile),
    }

    return rPackage


def build_sql_rules():
    """Retourne les règles du bac à sable SQL que le téléphone applique à l'identique."""

    rRules = {
        "today": TODAY,
        "dialects": DIALECTS,
        "max_query_length": MAX_QUERY_LENGTH,
        "max_rows": MAX_ROWS,
        "max_cell_length": MAX_CELL_LENGTH,
        "max_value_length": MAX_VALUE_LENGTH,
        "allowed_statements": list(ALLOWED_STATEMENTS),
        "refused_functions": sorted(REFUSED_FUNCTIONS),
        "not_allowed": NOT_ALLOWED_MESSAGE,
        "recursive": RECURSIVE_MESSAGE,
        "internal_write": INTERNAL_WRITE_PATTERN,
        "refused": REFUSED,
        "rewrites": REWRITES,
        "unit_functions": UNIT_FUNCTIONS,
        "units": UNITS,
        "errors": ERROR_MESSAGES,
    }

    return rRules


def build_sql_package(pDatabaseFile):
    """Retourne le bac à sable SQL à emporter : niveaux, base, règles, réussites."""

    vOverview = build_sql_overview(pDatabaseFile)

    rPackage = {
        "levels": list(load_sql_levels().values()),
        "schema": build_schema(),
        "script": load_script(),
        "rules": build_sql_rules(),
        "xp": XP_RULES["sql_level"][1],
        "dialect": vOverview["dialect"],
        "passed": [
            vRow["id"]
            for vSeries in vOverview["series"]
            for vRow in vSeries["rows"]
            if vRow["passed"]
        ],
    }

    return rPackage


def read_result(pItem):
    """Vérifie l'enveloppe d'une partie ; retourne (id, simulation, date) ou lève ValueError."""

    if not isinstance(pItem, dict):
        raise ValueError("partie illisible")

    vId = pItem.get("id")

    if not isinstance(vId, str) or not 1 <= len(vId) <= 64:
        raise ValueError("identifiant de partie manquant")

    try:
        vFinishedAt = datetime.fromisoformat(str(pItem.get("finished_at")))

    except ValueError as vError:
        raise ValueError("date de fin illisible") from vError

    rResult = (vId, pItem.get("lab"), vFinishedAt)

    return rResult


def integrate_troubleshooting(pDatabaseFile, pItem, pFinishedAt):
    """Rejoue une panne du téléphone ; retourne les points gagnés ou lève ValueError."""

    vActions = pItem.get("actions")

    if (
        not isinstance(vActions, list)
        or len(vActions) > MAX_ACTIONS
        or not all(isinstance(vAction, str) for vAction in vActions)
    ):
        raise ValueError("actions illisibles")

    if pItem.get("scenario") not in load_scenarios():
        raise ValueError("simulation ou scénario inconnu")

    vState = play(pItem["scenario"], vActions)

    if not vState["solved"]:
        raise ValueError("panne non résolue")

    rXp = save_result(pDatabaseFile, vState, pFinishedAt)

    return rXp


def integrate_ladder(pDatabaseFile, pItem, pFinishedAt):
    """Revérifie un programme d'automate du téléphone ; retourne les points gagnés."""

    vProgram = pItem.get("program")
    vLevel = load_levels().get(pItem.get("level"))

    if vLevel is None:
        raise ValueError("simulation ou niveau inconnu")

    if not isinstance(vProgram, str) or len(vProgram) > MAX_PROGRAM_LENGTH:
        raise ValueError("programme illisible")

    if not run_level(vLevel, vProgram)["passed"]:
        raise ValueError("niveau non réussi")

    vFirst = save_ladder_attempt(
        pDatabaseFile, vLevel["id"], vProgram, True, pFinishedAt
    )

    rXp = XP_RULES["ladder_level"][1] if vFirst else 0

    return rXp


def integrate_git(pDatabaseFile, pItem, pFinishedAt):
    """Rejoue les commandes Git du téléphone ; retourne les points gagnés."""

    vLevel = get_git_level(pItem.get("level"))
    vHistory = pItem.get("history")

    if vLevel is None:
        raise ValueError("simulation ou niveau inconnu")

    if not isinstance(vHistory, list) or not all(
        isinstance(vCommand, str) for vCommand in vHistory
    ):
        raise ValueError("commandes illisibles")

    if not is_goal_reached(vLevel, replay_level(vLevel, vHistory)):
        raise ValueError("niveau non réussi")

    vFirst = vLevel.id not in get_git_level_results(pDatabaseFile)
    save_git_level_result(pDatabaseFile, vLevel.id, len(vHistory), pFinishedAt)

    rXp = XP_RULES["git_level"][1] if vFirst else 0

    return rXp


def integrate_devops(pDatabaseFile, pItem, pFinishedAt):
    """Rejoue les étapes Maven ou Docker du téléphone ; retourne les points gagnés."""

    vLevel = load_devops_levels().get(pItem.get("level"))
    vSteps = pItem.get("steps")

    if vLevel is None:
        raise ValueError("simulation ou niveau inconnu")

    if (
        not isinstance(vSteps, list)
        or len(vSteps) > MAX_ACTIONS
        or not all(
            isinstance(vStep, dict)
            and isinstance(vStep.get("file"), str)
            and isinstance(vStep.get("command"), str)
            for vStep in vSteps
        )
    ):
        raise ValueError("étapes illisibles")

    if not replay_steps(
        vLevel, [(vStep["file"], vStep["command"]) for vStep in vSteps]
    ):
        raise ValueError("niveau non réussi")

    vFirst = mark_passed(pDatabaseFile, vLevel["id"], vSteps[-1]["file"], pFinishedAt)

    rXp = XP_RULES["devops_level"][1] if vFirst else 0

    return rXp


def integrate_sql(pDatabaseFile, pItem, pFinishedAt):
    """Réexécute une requête SQL du téléphone ; retourne les points gagnés."""

    vLevel = load_sql_levels().get(pItem.get("level"))
    vQuery = pItem.get("query")
    vDialect = pItem.get("dialect")

    if vLevel is None or vDialect not in DIALECTS:
        raise ValueError("simulation ou niveau inconnu")

    if not isinstance(vQuery, str) or len(vQuery) > MAX_QUERY_LENGTH:
        raise ValueError("requête illisible")

    if not run_sql_level(vLevel, vQuery, vDialect)["passed"]:
        raise ValueError("niveau non réussi")

    vFirst = save_sql_attempt(pDatabaseFile, vLevel["id"], vQuery, True, pFinishedAt)

    rXp = XP_RULES["sql_level"][1] if vFirst else 0

    return rXp


INTEGRATIONS = {
    "troubleshooting": integrate_troubleshooting,
    "ladder": integrate_ladder,
    "git": integrate_git,
    "devops": integrate_devops,
    "sql": integrate_sql,
}


def sync_lab_results(pDatabaseFile, pResults):
    """Intègre les parties jouées sur le téléphone ; retourne le bilan de l'envoi.

    Une partie refusée l'est pour de bon : le téléphone ne la renverra pas.
    """

    if not isinstance(pResults, list) or len(pResults) > MAX_RESULTS_PER_SYNC:
        raise ValueError(f"{MAX_RESULTS_PER_SYNC} parties au plus par envoi")

    vReceived = load_json_setting(pDatabaseFile, RECEIVED_KEY, [], list)
    vSaved = 0
    vXp = 0
    vRejected = []

    for vItem in pResults:
        try:
            vId, vLab, vFinishedAt = read_result(vItem)

            if vId in vReceived:
                continue

            if vLab not in INTEGRATIONS:
                raise ValueError("simulation ou scénario inconnu")

            vXp += INTEGRATIONS[vLab](pDatabaseFile, vItem, vFinishedAt)

        except ValueError as vError:
            vRejected.append(
                {
                    "id": vItem.get("id") if isinstance(vItem, dict) else None,
                    "reason": str(vError),
                }
            )
            continue

        vReceived.append(vId)
        vSaved += 1

    save_json_setting(pDatabaseFile, RECEIVED_KEY, vReceived[-MAX_RECEIVED:])

    if vSaved or vRejected:
        logger.info(
            "Simulations du téléphone : %d partie(s) intégrée(s), %d refusée(s)",
            vSaved,
            len(vRejected),
        )

    rReport = {"saved": vSaved, "xp": vXp, "rejected": vRejected}

    return rReport
