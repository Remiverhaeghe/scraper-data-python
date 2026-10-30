"""Simulateur d'automate : niveaux, machines simulées, tests et progression

L'automate scrute son programme toutes les 100 ms, comme un vrai : lecture des
entrées, barreaux exécutés de haut en bas, puis la machine réagit aux sorties
(le vérin avance, le tapis fait passer des pièces). Le temps se compte en
cycles entiers pour que les tests soient exacts.
"""

import json
from datetime import datetime
from functools import lru_cache
from html import escape

from config import LADDER_LEVELS_FILE
from job.ladder import LadderError, collect_names, evaluate, parse_program
from job.progress import LADDER_PROGRESS_KEY
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

CYCLE_SECONDS = 0.1
CYCLES_PER_SECOND = 10

# Vérin : une seconde de course ; tapis : une pièce par seconde, vue 0,3 s ;
# broche : deux secondes de course
VERIN_STROKE = 10
PIECE_PERIOD = 10
PIECE_VISIBLE = 3
SPINDLE_STROKE = 20


def to_cycles(pSeconds):
    """Retourne le nombre de cycles d'une durée en secondes."""

    rCycles = round(pSeconds * CYCLES_PER_SECOND)

    return rCycles


@lru_cache(maxsize=1)
def load_levels():
    """Retourne les niveaux livrés, par identifiant, dans l'ordre du fichier."""

    vLevels = json.loads(LADDER_LEVELS_FILE.read_text(encoding="utf-8"))

    rLevels = {vLevel["id"]: vLevel for vLevel in vLevels}

    return rLevels


def get_level(pLevelId):
    """Retourne un niveau ; lève ValueError s'il n'existe pas."""

    vLevel = load_levels().get(pLevelId)

    if vLevel is None:
        raise ValueError(f"Niveau inconnu : {pLevelId}")

    return vLevel


def get_names(pLevel, pKind):
    """Retourne les noms des variables d'un genre : input ou output."""

    rNames = [
        vVariable["name"]
        for vVariable in pLevel["variables"]
        if vVariable["kind"] == pKind
    ]

    return rNames


def get_sensor_names(pLevel):
    """Retourne les entrées pilotées par la machine, pas par l'opérateur."""

    rNames = {
        vVariable["name"]
        for vVariable in pLevel["variables"]
        if vVariable.get("control") == "sensor"
    }

    return rNames


class Simulator:
    """Automate et machine simulés, avancés cycle par cycle."""

    def __init__(self, pLevel, pRungs):
        """Démarre à l'arrêt : sorties et mémoires à 0, entrées à leur valeur de repos."""
        self.level = pLevel
        self.rungs = pRungs
        self.cycle = 0
        self.values = {vName: False for vName in collect_names(pRungs)}
        self.values.update(
            {
                vVariable["name"]: bool(vVariable.get("default", 0))
                for vVariable in pLevel["variables"]
            }
        )
        self.timers = {}
        self.counters = {}
        self.machine = {"position": 0, "run": 0}
        self.read_sensors()

    def set_input(self, pName, pValue):
        """Change une entrée commandée par l'opérateur."""
        self.values[pName] = bool(pValue)

    def read_sensors(self):
        """Met à jour les capteurs d'après l'état de la machine."""
        vKind = self.level["machine"]
        vPosition = self.machine["position"]

        if vKind == "verin":
            self.values["fin_sortie"] = vPosition >= VERIN_STROKE
        elif vKind == "tapis":
            self.values["piece"] = self.machine["run"] % PIECE_PERIOD < PIECE_VISIBLE
        elif vKind == "percage":
            self.values["haut"] = vPosition <= 0
            self.values["bas"] = vPosition >= SPINDLE_STROKE

    def scan(self):
        """Exécute les barreaux dans l'ordre, chacun voyant les résultats des précédents."""
        for vRung in self.rungs:
            vInput = evaluate(vRung["expr"], self.values)
            vTarget = vRung["target"]
            vKind = vRung["kind"]

            if vKind == "coil":
                self.values[vTarget] = vInput
            elif vKind == "set":
                if vInput:
                    self.values[vTarget] = True
            elif vKind == "reset":
                if vInput:
                    self.values[vTarget] = False
            elif vKind == "ton":
                vElapsed = self.timers.get(vTarget, 0) + 1 if vInput else 0
                self.timers[vTarget] = vElapsed
                self.values[vTarget] = vElapsed >= to_cycles(vRung["preset"])
            else:
                vCount, vPrevious = self.counters.get(vTarget, (0, False))

                if vInput and not vPrevious:
                    vCount += 1

                if vRung["reset"] is not None and evaluate(vRung["reset"], self.values):
                    vCount = 0

                self.counters[vTarget] = (vCount, vInput)
                self.values[vTarget] = vCount >= vRung["preset"]

    def move_machine(self):
        """Fait réagir la machine aux sorties pendant un cycle."""
        vKind = self.level["machine"]
        vValues = self.values

        if vKind == "verin":
            vStep = 1 if vValues.get("sortir") else -1
            self.machine["position"] = min(
                VERIN_STROKE, max(0, self.machine["position"] + vStep)
            )
        elif vKind == "tapis" and vValues.get("tapis"):
            self.machine["run"] += 1
        elif vKind == "percage":
            vStep = int(bool(vValues.get("descendre"))) - int(
                bool(vValues.get("monter"))
            )
            self.machine["position"] = min(
                SPINDLE_STROKE, max(0, self.machine["position"] + vStep)
            )

    def step(self):
        """Un cycle d'automate : capteurs, programme, machine."""
        self.read_sensors()
        self.scan()
        self.move_machine()
        self.cycle += 1

    def get_time(self):
        """Retourne le temps écoulé en secondes."""
        return self.cycle * CYCLE_SECONDS


def run_level(pLevel, pProgram):
    """Exécute le scénario de test d'un niveau sur un programme.

    Retourne l'erreur d'écriture éventuelle, le résultat de chaque vérification,
    les interdits violés et les valeurs de chaque cycle pour le chronogramme.
    """

    vInputs = set(get_names(pLevel, "input"))

    try:
        vRungs = parse_program(pProgram, vInputs)

    except LadderError as vException:
        return {"passed": False, "error": str(vException), "line": vException.line}

    if not vRungs:
        return {"passed": False, "error": "Le programme est vide.", "line": None}

    vSimulator = Simulator(pLevel, vRungs)
    vEvents = {}
    vChecks = {}

    for vEvent in pLevel["events"]:
        vEvents.setdefault(to_cycles(vEvent["at"]), {}).update(vEvent["set"])

    for vCheck in pLevel["checks"]:
        vChecks.setdefault(to_cycles(vCheck["at"]), []).append(vCheck)

    vSignals = get_names(pLevel, "input") + get_names(pLevel, "output")
    vSamples = []
    vResults = []
    vViolations = []

    for vCycle in range(to_cycles(pLevel["duration"]) + 1):
        for vName, vValue in vEvents.get(vCycle, {}).items():
            vSimulator.set_input(vName, vValue)

        for vCheck in vChecks.get(vCycle, []):
            vGot = {
                vName: int(bool(vSimulator.values.get(vName)))
                for vName in vCheck["expect"]
            }
            vResults.append(
                {
                    "at": vCheck["at"],
                    "message": vCheck["message"],
                    "expected": vCheck["expect"],
                    "got": vGot,
                    "passed": vGot == vCheck["expect"],
                }
            )

        vSimulator.step()
        vSamples.append(
            {vName: int(bool(vSimulator.values.get(vName))) for vName in vSignals}
        )

        for vForbidden in pLevel.get("forbidden", []):
            if (
                all(vSimulator.values.get(vName) for vName in vForbidden["all"])
                and vForbidden["message"] not in vViolations
            ):
                vViolations.append(vForbidden["message"])

    rRun = {
        "passed": all(vResult["passed"] for vResult in vResults) and not vViolations,
        "error": None,
        "line": None,
        "rungs": vRungs,
        "checks": vResults,
        "violations": vViolations,
        "signals": vSignals,
        "samples": vSamples,
    }

    return rRun


CHART_ROW = 30
CHART_LABEL = 120
CHART_STEP = 6


def render_chronogram(pSignals, pSamples, pInputs=()):
    """Retourne le chronogramme des signaux en SVG : une ligne par signal."""

    vWidth = CHART_LABEL + len(pSamples) * CHART_STEP + 10
    vHeight = len(pSignals) * CHART_ROW + 24
    vParts = []

    for vIndex, vName in enumerate(pSignals):
        vTop = vIndex * CHART_ROW + 8
        vHigh = vTop + 4
        vLow = vTop + CHART_ROW - 10
        vColor = "#2563eb" if vName in pInputs else "#16a34a"
        vPoints = []

        for vCycle, vSample in enumerate(pSamples):
            vY = vHigh if vSample[vName] else vLow
            vX = CHART_LABEL + vCycle * CHART_STEP
            vPoints.append(f"{vX},{vY} {vX + CHART_STEP},{vY}")

        vParts.append(
            f'<text x="4" y="{vLow}" font-size="12" fill="#0f172a">{escape(vName)}</text>'
            f'<polyline points="{" ".join(vPoints)}" fill="none" stroke="{vColor}" stroke-width="2"/>'
        )

    for vSecond in range(0, len(pSamples) // CYCLES_PER_SECOND + 1):
        vX = CHART_LABEL + vSecond * CYCLES_PER_SECOND * CHART_STEP
        vParts.append(
            f'<line x1="{vX}" y1="4" x2="{vX}" y2="{vHeight - 16}" stroke="#e2e8f0"/>'
            f'<text x="{vX}" y="{vHeight - 4}" text-anchor="middle" font-size="10" fill="#64748b">{vSecond} s</text>'
        )

    rSvg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vWidth}" height="{vHeight}" '
        f'viewBox="0 0 {vWidth} {vHeight}" font-family="Arial, sans-serif" role="img" '
        f'aria-label="Chronogramme des entrées et sorties">'
        f'<rect width="{vWidth}" height="{vHeight}" fill="#ffffff"/>'
        + "".join(vParts)
        + "</svg>"
    )

    return rSvg


def load_ladder_progress(pDatabaseFile):
    """Retourne, par niveau, le dernier programme et la date de réussite."""

    rProgress = load_json_setting(pDatabaseFile, LADDER_PROGRESS_KEY, {}, dict)

    return rProgress


def save_attempt(pDatabaseFile, pLevelId, pProgram, pPassed, pNow=None):
    """Garde le programme essayé ; la première réussite est datée et rapporte des points."""

    vProgress = load_ladder_progress(pDatabaseFile)
    vEntry = vProgress.get(pLevelId) or {}
    vFirst = pPassed and not vEntry.get("passed_at")

    vEntry["program"] = pProgram

    if vFirst:
        vEntry["passed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")

    vProgress[pLevelId] = vEntry
    save_json_setting(pDatabaseFile, LADDER_PROGRESS_KEY, vProgress)

    if vFirst:
        logger.info("Niveau d'automate réussi : %s", pLevelId)

    rFirst = vFirst

    return rFirst


def build_ladder_overview(pDatabaseFile):
    """Retourne les niveaux avec leur état : réussi, commencé ou nouveau."""

    vProgress = load_ladder_progress(pDatabaseFile)
    vRows = []

    for vLevel in load_levels().values():
        vEntry = vProgress.get(vLevel["id"]) or {}
        vRows.append(
            {
                "id": vLevel["id"],
                "title": vLevel["title"],
                "goal": vLevel["goal"],
                "passed": bool(vEntry.get("passed_at")),
                "program": vEntry.get("program") or vLevel["starter"],
            }
        )

    rOverview = {
        "rows": vRows,
        "passed": sum(vRow["passed"] for vRow in vRows),
    }

    return rOverview
