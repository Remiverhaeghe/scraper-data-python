"""Niveaux de l'atelier Excel : énoncés, vérification d'une formule et progression

La formule écrite pour la première cellule est recopiée sur toute la plage du
niveau, comme une poignée de recopie, puis chaque cellule est comparée au
résultat de la solution de référence recopiée de la même façon.
"""

import json
import re
from datetime import datetime
from functools import lru_cache

from config import EXCEL_LEVELS_FILE
from job.excel_formula import (
    FormulaError,
    Sheet,
    cell_name,
    collect,
    column_letters,
    parse_cell,
    parse_formula,
    shift_formula,
)
from job.excel_values import format_value, is_error, is_number, same_value
from job.progress import EXCEL_PROGRESS_KEY
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

NO_REFERENCE_MESSAGE = (
    "La formule doit s'appuyer sur les cellules de la feuille, pas sur des "
    "valeurs recopiées à la main."
)
CIRCULAR_MESSAGE = (
    "Référence circulaire : la formule dépend de la cellule où elle est écrite."
)
TOO_COMPLEX_MESSAGE = "Formule trop complexe pour être calculée."


@lru_cache(maxsize=1)
def load_content():
    """Retourne le contenu livré : les niveaux."""

    rContent = json.loads(EXCEL_LEVELS_FILE.read_text(encoding="utf-8"))

    return rContent


def load_levels():
    """Retourne les niveaux, par identifiant, dans l'ordre du fichier."""

    rLevels = {vLevel["id"]: vLevel for vLevel in load_content()["levels"]}

    return rLevels


def get_level(pLevelId):
    """Retourne un niveau ; lève ValueError s'il n'existe pas."""

    vLevel = load_levels().get(pLevelId)

    if vLevel is None:
        raise ValueError(f"Niveau Excel inconnu : {pLevelId}")

    return vLevel


def get_targets(pLevel):
    """Retourne les cellules à remplir : la plage de recopie, ou la seule cellule."""

    vFirst, _, vLast = pLevel.get("fill", pLevel["cell"]).partition(":")
    vTop, vLeft = parse_cell(vFirst)
    vBottom, vRight = parse_cell(vLast or vFirst)

    rTargets = [
        (vRow, vColumn)
        for vRow in range(vTop, vBottom + 1)
        for vColumn in range(vLeft, vRight + 1)
    ]

    return rTargets


def fill_formulas(pLevel, pFormula):
    """Retourne la formule recopiée dans chaque cellule cible, par adresse."""

    vTop, vLeft = parse_cell(pLevel["cell"])

    rFormulas = {
        cell_name(vRow, vColumn): shift_formula(pFormula, vRow - vTop, vColumn - vLeft)
        for vRow, vColumn in get_targets(pLevel)
    }

    return rFormulas


def get_format(pLevel, pColumn):
    """Retourne le format d'affichage d'une colonne : date, euro, percent ou standard."""

    rFormat = pLevel.get("formats", {}).get(column_letters(pColumn), "")

    return rFormat


def check_formula(pLevel, pFormula):
    """Retourne le message qui refuse la formule, ou une chaîne vide."""

    try:
        vTree = parse_formula(pFormula)

    except FormulaError as vError:
        return str(vError)

    vFunctions = set()

    if not collect(vTree, vFunctions):
        return NO_REFERENCE_MESSAGE

    for vGroup in pLevel.get("requires", []):
        vNames = vGroup.split("|")

        if not vFunctions.intersection(vNames):
            return (
                f"Ce niveau attend la fonction {vNames[0]}."
                if len(vNames) == 1
                else f"Ce niveau attend l'une des fonctions {', '.join(vNames)}."
            )

    return ""


def build_sheet(pLevel, pFormula):
    """Retourne la feuille du niveau, avec la formule recopiée si elle est fournie."""

    rSheet = Sheet(
        pLevel["rows"], fill_formulas(pLevel, pFormula) if pFormula else None
    )

    return rSheet


def build_grid(pLevel, pSheet):
    """Retourne la feuille en texte, ligne par ligne, avec ses formats."""

    vTargets = get_targets(pLevel)
    vRows = max([len(pLevel["rows"])] + [vRow for vRow, _ in vTargets])
    vColumns = max(
        [len(vRow) for vRow in pLevel["rows"]] + [vColumn for _, vColumn in vTargets]
    )

    rGrid = {
        "columns": [column_letters(vColumn) for vColumn in range(1, vColumns + 1)],
        "rows": [
            [
                format_value(
                    pSheet.value(vRow, vColumn),
                    "" if vRow == 1 else get_format(pLevel, vColumn),
                )
                for vColumn in range(1, vColumns + 1)
            ]
            for vRow in range(1, vRows + 1)
        ],
        "targets": [cell_name(vRow, vColumn) for vRow, vColumn in vTargets],
    }

    return rGrid


def describe_type(pValue):
    """Retourne le genre d'une valeur, pour un écart invisible à l'affichage."""

    if is_error(pValue):
        return "une erreur"

    if isinstance(pValue, bool):
        return "une valeur logique"

    rType = "un nombre" if is_number(pValue) else "un texte"

    return rType


def find_pitfalls(pLevel, pFormula):
    """Retourne les conseils des erreurs classiques reconnues dans la formule."""

    rAdvice = [
        vMessage
        for vPattern, vMessage in pLevel.get("pitfalls", [])
        if re.search(vPattern, pFormula, re.I)
    ]

    return rAdvice


def compare_cells(pLevel, pSheet, pExpected):
    """Compare chaque cellule cible à l'attendu ; retourne (cellules, message)."""

    vCells = []
    vWrong = []

    for vRow, vColumn in get_targets(pLevel):
        vValue = pSheet.value(vRow, vColumn)
        vExpected = pExpected.value(vRow, vColumn)
        vFormat = get_format(pLevel, vColumn)
        vCell = {
            "cell": cell_name(vRow, vColumn),
            "value": format_value(vValue, vFormat),
            "expected": format_value(vExpected, vFormat),
            "ok": same_value(vValue, vExpected),
        }
        vCells.append(vCell)

        if not vCell["ok"]:
            vWrong.append((vCell, vValue, vExpected))

    if not vWrong:
        return vCells, ""

    vCell, vValue, vExpected = vWrong[0]
    vGap = (
        f"{vCell['cell']} : {vCell['value']} obtenu ({describe_type(vValue)}), "
        f"{describe_type(vExpected)} attendu."
        if vCell["value"] == vCell["expected"]
        else f"{vCell['cell']} : {vCell['value']} obtenu, {vCell['expected']} attendu."
    )

    rMessage = (
        f"{len(vWrong)} cellules sur {len(vCells)} diffèrent de l'attendu. {vGap}"
        if len(vWrong) > 1
        else vGap
    )

    return vCells, rMessage


def run_level(pLevel, pFormula):
    """Recopie la formule sur la plage du niveau et la compare à la solution."""

    vFormula = pFormula.strip()
    vMessage = check_formula(pLevel, vFormula)
    vCells = []
    vSheet = build_sheet(pLevel, "")

    if not vMessage:
        vSheet = build_sheet(pLevel, vFormula)
        vExpected = build_sheet(pLevel, pLevel["solution"])

        try:
            vCells, vMessage = compare_cells(pLevel, vSheet, vExpected)

        except RecursionError:
            vSheet = build_sheet(pLevel, "")
            vCells = []
            vMessage = TOO_COMPLEX_MESSAGE

        if vSheet.circular:
            vMessage = CIRCULAR_MESSAGE

    vPassed = not vMessage

    rRun = {
        "passed": vPassed,
        "message": vMessage,
        "advice": [] if vPassed else find_pitfalls(pLevel, vFormula),
        "cells": vCells,
        "grid": build_grid(pLevel, vSheet),
    }

    return rRun


def load_excel_progress(pDatabaseFile):
    """Retourne, par niveau, la dernière formule essayée et la date de réussite."""

    vProgress = load_json_setting(pDatabaseFile, EXCEL_PROGRESS_KEY, {}, dict)
    vLevels = vProgress.get("levels")

    rProgress = {"levels": vLevels if isinstance(vLevels, dict) else {}}

    return rProgress


def save_attempt(pDatabaseFile, pLevelId, pFormula, pPassed, pNow=None):
    """Garde la formule essayée ; la première réussite est datée."""

    vProgress = load_excel_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}
    vFirst = pPassed and not vEntry.get("passed_at")

    vEntry["formula"] = pFormula

    if vFirst:
        vEntry["passed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")

    vProgress["levels"][pLevelId] = vEntry
    save_json_setting(pDatabaseFile, EXCEL_PROGRESS_KEY, vProgress)

    if vFirst:
        logger.info("Niveau Excel réussi : %s", pLevelId)

    rFirst = vFirst

    return rFirst


def build_excel_overview(pDatabaseFile):
    """Retourne les niveaux par série, avec leur état et la dernière formule."""

    vProgress = load_excel_progress(pDatabaseFile)
    vGroups = {}

    for vLevel in load_levels().values():
        vEntry = vProgress["levels"].get(vLevel["id"]) or {}
        vGroups.setdefault(vLevel["series"], []).append(
            {
                "id": vLevel["id"],
                "title": vLevel["title"],
                "goal": vLevel["goal"],
                "passed": bool(vEntry.get("passed_at")),
                "formula": vEntry.get("formula") or "=",
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
        "series": vSeries,
        "passed": sum(vGroup["done"] for vGroup in vSeries),
        "total": len(load_levels()),
    }

    return rOverview
