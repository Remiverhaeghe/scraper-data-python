"""Montages électriques : niveaux guidés, vérification par étapes, schémas libres

Un niveau donne une palette de composants et une suite d'étapes : on manœuvre
les commandes (interrupteurs, boutons) et on vérifie l'état des récepteurs ou
une mesure. Le mode libre réutilise le même éditeur et le même simulateur ; ses
schémas sont enregistrés avec la progression.
"""

import json
from datetime import datetime
from functools import lru_cache

from config import CIRCUIT_LEVELS_FILE
from job.circuit import (
    OPERABLE_DEFAULTS,
    SIMULATED_TYPES,
    VALUE_RANGES,
    Circuit,
    format_measure,
    get_value,
)
from job.circuit_drawing import get_instance_label
from job.progress import CIRCUIT_PROGRESS_KEY
from job.schema_building import read_answer
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Palette du mode libre : nombre d'exemplaires permis par type
FREE_LIMITS = {
    vType: (
        1
        if vType in ("alimentation", "bobine_relais", "telerupteur")
        else 2 if vType in ("pile", "masse", "voltmetre", "amperemetre") else 4
    )
    for vType in SIMULATED_TYPES
}
MAX_SCHEMAS = 30
MAX_NAME_LENGTH = 60
MEASURE_UNITS = {"voltage": "V", "current": "A", "potential": "V"}


@lru_cache(maxsize=1)
def load_levels():
    """Retourne les niveaux livrés, par identifiant, dans l'ordre du fichier."""

    vLevels = json.loads(CIRCUIT_LEVELS_FILE.read_text(encoding="utf-8"))

    rLevels = {vLevel["id"]: vLevel for vLevel in vLevels}

    return rLevels


def get_level(pLevelId):
    """Retourne un niveau ; lève ValueError s'il n'existe pas."""

    vLevel = load_levels().get(pLevelId)

    if vLevel is None:
        raise ValueError(f"Montage inconnu : {pLevelId}")

    return vLevel


def read_schema(pSchema, pLimits):
    """Vérifie un schéma envoyé ; retourne (composants, fils).

    Lève ValueError si le schéma est vide, illisible ou hors de la palette.
    """

    vSchema = json.loads(pSchema) if isinstance(pSchema, str) else pSchema
    vInstances, vPositions, vWires = read_answer(vSchema, pLimits)

    rSchema = (
        [
            {"id": vId, "type": vType, "x": vPositions[vId][0], "y": vPositions[vId][1]}
            for vId, vType in vInstances.items()
        ],
        [list(vWire) for vWire in vWires],
    )

    return rSchema


def build_values(pComponents, pRaw, pFixed=None, pEditable=None):
    """Retourne la valeur de chaque composant réglable : fixée, saisie ou par défaut.

    pEditable vaut None en mode libre : toutes les valeurs sont alors réglables.
    """

    rValues = {}

    for vItem in pComponents:
        vId = vItem["id"]

        if vItem["type"] not in VALUE_RANGES:
            continue

        vSource = (pFixed or {}).get(vId)

        if (pEditable is None or vId in pEditable) and vId in (pRaw or {}):
            vSource = pRaw[vId]

        rValues[vId] = get_value(
            vItem["type"], vId, {} if vSource is None else {vId: vSource}
        )

    return rValues


def get_controls(pComponents):
    """Retourne les commandes manœuvrables d'un schéma : (id, type, nom)."""

    rControls = [
        (vItem["id"], vItem["type"], get_instance_label(vItem["id"], vItem["type"]))
        for vItem in sorted(pComponents, key=lambda pItem: pItem["id"])
        if vItem["type"] in OPERABLE_DEFAULTS
    ]

    return rControls


def read_state(pInputs, pMemory, pComponents):
    """Retourne commandes et mémoire envoyées par le navigateur, réduites au schéma.

    Seules des valeurs booléennes, sur des composants du bon type, sont gardées :
    un envoi forgé ne peut rien injecter d'autre dans la simulation.
    """

    vTypes = {vItem["id"]: vItem["type"] for vItem in pComponents}
    vInputs = pInputs if isinstance(pInputs, dict) else {}
    vMemory = pMemory if isinstance(pMemory, dict) else {}

    def keep(pValue, pAllowed):
        return {
            vId: vValue
            for vId, vValue in (pValue if isinstance(pValue, dict) else {}).items()
            if vTypes.get(vId) in pAllowed and isinstance(vValue, bool)
        }

    rState = (
        keep(vInputs, OPERABLE_DEFAULTS),
        {
            "coils": keep(vMemory.get("coils"), ("bobine_relais",)),
            "latches": keep(vMemory.get("latches"), ("telerupteur",)),
            "remote": keep(vMemory.get("remote"), ("telerupteur",)),
            "tripped": [
                vId
                for vId in (
                    vMemory.get("tripped")
                    if isinstance(vMemory.get("tripped"), list)
                    else []
                )
                if vTypes.get(vId) in ("disjoncteur", "fusible")
            ],
        },
    )

    return rState


def get_editable(pComponents, pLevel=None):
    """Retourne les composants dont l'utilisateur règle la valeur : (id, nom, unité)."""

    rEditable = [
        (
            vItem["id"],
            get_instance_label(vItem["id"], vItem["type"]),
            VALUE_RANGES[vItem["type"]],
        )
        for vItem in pComponents
        if vItem["type"] in VALUE_RANGES
        and (pLevel is None or vItem["id"] in pLevel.get("editable", []))
    ]

    return rEditable


def evaluate(pKey, pExpected, pResult, pPrevious):
    """Retourne (réussi, détail) d'une attente d'étape sur un composant."""

    vId, _, vMeasure = pKey.partition(".")
    vPart = pResult["parts"].get(vId)

    if vPart is None:
        return (False, f"composant absent : {vId}")

    vLabel = get_instance_label(vId, vPart["type"])

    if not vMeasure:
        vPassed = (
            vPart["on"] != pPrevious.get(vId, False)
            if pExpected == "toggle"
            else vPart["on"] == (pExpected == "on")
        )

        return (vPassed, f"{vLabel} : {vPart['status'] or 'sans courant'}")

    vValue = abs(vPart[vMeasure])

    vText = format_measure(vValue, MEASURE_UNITS[vMeasure])

    rEvaluation = (
        pExpected[0] <= vValue <= pExpected[1],
        (
            f"{vLabel} : reste sous {vText}"
            if vMeasure == "potential"
            else f"{vLabel} : {vText}"
        ),
    )

    return rEvaluation


def run_level(pLevel, pComponents, pWires, pValues):
    """Joue les étapes du niveau sur le schéma ; retourne vérifications et état final."""

    vCircuit = Circuit(pComponents, pWires, pValues)
    vInputs = {}
    vMemory = None
    vPrevious = {}
    vChecks = []
    vResult = None

    for vStep in pLevel["steps"]:
        vInputs.update(vStep["set"])
        vResult = vCircuit.simulate(vInputs, vMemory)
        vMemory = vResult["memory"]
        vDetails = []
        vPassed = not vResult["faults"]

        for vKey, vExpected in vStep["expect"].items():
            vOk, vDetail = evaluate(vKey, vExpected, vResult, vPrevious)
            vPassed &= vOk

            if not vOk:
                vDetails.append(vDetail)

        if vStep["expect"] or vResult["faults"]:
            vChecks.append(
                {
                    "message": vStep.get("message", "Mise en position de départ."),
                    "passed": vPassed,
                    "details": vDetails + vResult["faults"],
                }
            )

        vPrevious = {vId: vPart["on"] for vId, vPart in vResult["parts"].items()}

    rRun = {
        "passed": all(vCheck["passed"] for vCheck in vChecks),
        "checks": vChecks,
        "result": vResult,
        "inputs": vInputs,
    }

    return rRun


def get_solution(pLevel):
    """Retourne la solution d'un niveau : composants, fils et valeurs."""

    vComponents = pLevel["solution_components"]

    rSolution = (
        vComponents,
        pLevel["solution_wires"],
        build_values(
            vComponents,
            pLevel.get("solution_values", {}),
            pLevel.get("values"),
            pLevel.get("editable", []),
        ),
    )

    return rSolution


def load_circuit_progress(pDatabaseFile):
    """Retourne les niveaux (dernier schéma, réussite) et les schémas libres."""

    vProgress = load_json_setting(pDatabaseFile, CIRCUIT_PROGRESS_KEY, {}, dict)
    vLevels = vProgress.get("levels")
    vSchemas = vProgress.get("schemas")

    rProgress = {
        "levels": vLevels if isinstance(vLevels, dict) else {},
        "schemas": vSchemas if isinstance(vSchemas, list) else [],
    }

    return rProgress


def save_attempt(pDatabaseFile, pLevelId, pSchema, pValues, pPassed, pNow=None):
    """Garde le dernier schéma essayé ; la première réussite est datée."""

    vProgress = load_circuit_progress(pDatabaseFile)
    vEntry = vProgress["levels"].get(pLevelId) or {}
    vFirst = pPassed and not vEntry.get("passed_at")

    vEntry["schema"] = pSchema
    vEntry["values"] = pValues

    if vFirst:
        vEntry["passed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")

    vProgress["levels"][pLevelId] = vEntry
    save_json_setting(pDatabaseFile, CIRCUIT_PROGRESS_KEY, vProgress)

    if vFirst:
        logger.info("Montage électrique réussi : %s", pLevelId)

    rFirst = vFirst

    return rFirst


def save_schema(pDatabaseFile, pName, pSchema, pValues, pNow=None):
    """Enregistre un schéma libre sous un nom ; le même nom remplace l'ancien.

    Lève ValueError si le nom est vide ou si la liste est pleine.
    """

    vName = " ".join(str(pName).split())[:MAX_NAME_LENGTH]

    if not vName:
        raise ValueError("Donnez un nom au schéma.")

    vProgress = load_circuit_progress(pDatabaseFile)
    vSchemas = [
        vItem
        for vItem in vProgress["schemas"]
        if isinstance(vItem, dict) and vItem.get("name") != vName
    ]

    if len(vSchemas) >= MAX_SCHEMAS:
        raise ValueError(f"{MAX_SCHEMAS} schémas au plus : supprimez-en un.")

    vSchemas.insert(
        0,
        {
            "name": vName,
            "schema": pSchema,
            "values": pValues,
            "saved_at": (pNow or datetime.now()).isoformat(timespec="seconds"),
        },
    )
    vProgress["schemas"] = vSchemas
    save_json_setting(pDatabaseFile, CIRCUIT_PROGRESS_KEY, vProgress)
    logger.info("Schéma électrique enregistré (%d au total)", len(vSchemas))


def delete_schema(pDatabaseFile, pName):
    """Supprime un schéma libre par son nom."""

    vProgress = load_circuit_progress(pDatabaseFile)
    vProgress["schemas"] = [
        vItem
        for vItem in vProgress["schemas"]
        if isinstance(vItem, dict) and vItem.get("name") != pName
    ]
    save_json_setting(pDatabaseFile, CIRCUIT_PROGRESS_KEY, vProgress)


def find_schema(pDatabaseFile, pName):
    """Retourne un schéma libre enregistré, ou None."""

    rSchema = next(
        (
            vItem
            for vItem in load_circuit_progress(pDatabaseFile)["schemas"]
            if isinstance(vItem, dict) and vItem.get("name") == pName
        ),
        None,
    )

    return rSchema


def build_circuit_overview(pDatabaseFile):
    """Retourne les niveaux avec leur état et les noms des schémas libres."""

    vProgress = load_circuit_progress(pDatabaseFile)
    vRows = []

    for vLevel in load_levels().values():
        vEntry = vProgress["levels"].get(vLevel["id"]) or {}
        vRows.append(
            {
                "id": vLevel["id"],
                "title": vLevel["title"],
                "goal": vLevel["goal"],
                "passed": bool(vEntry.get("passed_at")),
                "schema": vEntry.get("schema"),
                "values": vEntry.get("values") or {},
            }
        )

    rOverview = {
        "rows": vRows,
        "passed": sum(vRow["passed"] for vRow in vRows),
        "schemas": [
            vItem["name"]
            for vItem in vProgress["schemas"]
            if isinstance(vItem, dict) and vItem.get("name")
        ],
    }

    return rOverview
