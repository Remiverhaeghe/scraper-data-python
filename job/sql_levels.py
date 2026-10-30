"""Niveaux du bac à sable SQL : énoncés, vérification d'une requête et progression

Le résultat attendu est celui de la solution de référence dans le dialecte
choisi : une autre requête qui renvoie les mêmes lignes est acceptée.
"""

import json
import re
from datetime import datetime
from functools import lru_cache

from config import SQL_LEVELS_FILE
from job.progress import SQL_PROGRESS_KEY
from job.sql_sandbox import (
    DEFAULT_DIALECT,
    DIALECTS,
    compare_results,
    describe_schema,
    execute,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def load_content():
    """Retourne le contenu livré : description des tables et niveaux."""

    rContent = json.loads(SQL_LEVELS_FILE.read_text(encoding="utf-8"))

    return rContent


def load_levels():
    """Retourne les niveaux, par identifiant, dans l'ordre du fichier."""

    rLevels = {vLevel["id"]: vLevel for vLevel in load_content()["levels"]}

    return rLevels


def get_level(pLevelId):
    """Retourne un niveau ; lève ValueError s'il n'existe pas."""

    vLevel = load_levels().get(pLevelId)

    if vLevel is None:
        raise ValueError(f"Niveau SQL inconnu : {pLevelId}")

    return vLevel


def pick(pLevel, pKey, pDialect):
    """Retourne un champ du niveau, propre au dialecte quand il en dépend."""

    vValue = pLevel[pKey]

    rValue = vValue[pDialect] if isinstance(vValue, dict) else vValue

    return rValue


def build_schema():
    """Retourne les tables de la base d'exemple : nom, rôle et colonnes."""

    vLabels = load_content()["tables"]

    rSchema = [
        {"name": vTable, "label": vLabels.get(vTable, ""), "columns": vColumns}
        for vTable, vColumns in describe_schema()
    ]

    return rSchema


@lru_cache(maxsize=64)
def get_expected(pLevelId, pDialect):
    """Retourne le résultat de la solution de référence dans un dialecte."""

    vLevel = get_level(pLevelId)

    rExpected = execute(
        pick(vLevel, "solution", pDialect), pDialect, vLevel.get("check", "")
    )

    if rExpected["error"]:
        logger.error(
            "Solution SQL en échec : %s (%s) : %s",
            pLevelId,
            pDialect,
            rExpected["error"],
        )

    return rExpected


def find_pitfalls(pLevel, pQuery):
    """Retourne les conseils des erreurs classiques reconnues dans la requête."""

    rAdvice = [
        vMessage
        for vPattern, vMessage in pLevel.get("pitfalls", [])
        if re.search(vPattern, pQuery, re.I)
    ]

    return rAdvice


def mask_columns(pColumns):
    """Masque les en-têtes calculés, qui donneraient la réponse : « colonne n »."""

    rColumns = [
        vName if re.fullmatch(r"\w+", vName) else f"colonne {vIndex}"
        for vIndex, vName in enumerate(pColumns, start=1)
    ]

    return rColumns


def run_level(pLevel, pQuery, pDialect):
    """Exécute la requête et la compare au résultat attendu du niveau."""

    vExpected = get_expected(pLevel["id"], pDialect)
    vResult = execute(pQuery, pDialect, pLevel.get("check", ""))
    vMessage = vResult["error"]

    if not vMessage and not pLevel.get("check") and vResult["changed"] is not None:
        vMessage = "Ce niveau attend une requête SELECT : la vôtre modifie la base."

    if not vMessage:
        vMessage = compare_results(vResult, vExpected, pLevel["ordered"])

    vPassed = not vMessage

    rRun = {
        "result": vResult,
        "expected": {**vExpected, "columns": mask_columns(vExpected["columns"])},
        "passed": vPassed,
        "message": vMessage,
        "advice": [] if vPassed else find_pitfalls(pLevel, pQuery),
    }

    return rRun


def load_sql_progress(pDatabaseFile):
    """Retourne le dialecte choisi et, par niveau, dernière requête et réussite."""

    vProgress = load_json_setting(pDatabaseFile, SQL_PROGRESS_KEY, {}, dict)
    vLevels = vProgress.get("levels")
    vDialect = vProgress.get("dialect")

    rProgress = {
        "dialect": vDialect if vDialect in DIALECTS else DEFAULT_DIALECT,
        "levels": vLevels if isinstance(vLevels, dict) else {},
    }

    return rProgress


def save_dialect(pDatabaseFile, pDialect):
    """Enregistre le dialecte choisi ; lève ValueError s'il est inconnu."""

    if pDialect not in DIALECTS:
        raise ValueError(f"Dialecte inconnu : {pDialect}")

    vProgress = load_sql_progress(pDatabaseFile)
    vProgress["dialect"] = pDialect
    save_json_setting(pDatabaseFile, SQL_PROGRESS_KEY, vProgress)


def save_attempt(pDatabaseFile, pLevelId, pQuery, pPassed, pNow=None):
    """Garde la requête essayée ; la première réussite est datée."""

    vProgress = load_sql_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}
    vFirst = pPassed and not vEntry.get("passed_at")

    vEntry["query"] = pQuery

    if vFirst:
        vEntry["passed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")

    vProgress["levels"][pLevelId] = vEntry
    save_json_setting(pDatabaseFile, SQL_PROGRESS_KEY, vProgress)

    if vFirst:
        logger.info("Niveau SQL réussi : %s (%s)", pLevelId, vProgress["dialect"])

    rFirst = vFirst

    return rFirst


def build_sql_overview(pDatabaseFile):
    """Retourne le dialecte et les niveaux par série, avec leur état."""

    vProgress = load_sql_progress(pDatabaseFile)
    vGroups = {}

    for vLevel in load_levels().values():
        vEntry = vProgress["levels"].get(vLevel["id"]) or {}
        vGroups.setdefault(vLevel["series"], []).append(
            {
                "id": vLevel["id"],
                "title": vLevel["title"],
                "goal": vLevel["goal"],
                "passed": bool(vEntry.get("passed_at")),
                "query": vEntry.get("query") or vLevel["starter"],
            }
        )

    vSeries = [
        {
            "label": vLabel,
            "rows": vRows,
            "done": sum(vRow["passed"] for vRow in vRows),
        }
        for vLabel, vRows in vGroups.items()
    ]

    rOverview = {
        "dialect": vProgress["dialect"],
        "series": vSeries,
        "passed": sum(vGroup["done"] for vGroup in vSeries),
        "total": len(load_levels()),
    }

    return rOverview
