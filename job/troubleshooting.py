"""Pannes à résoudre : choisir les mesures, trouver la cause, au moindre temps

Chaque scénario décrit une machine en panne, des mesures possibles qui
coûtent chacune du temps, et des réparations dont une seule est la bonne.
Le moteur est sans état : il rejoue la liste des actions du joueur, ce qui
permet au web de la transporter dans le formulaire.
"""

import json
from datetime import datetime
from functools import lru_cache

from config import TROUBLESHOOTING_FILE
from job.progress import (
    TROUBLESHOOTING_RESULTS_KEY,
    TROUBLESHOOTING_XP_PER_TEN,
    XP_RULES,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_RESULTS = 200

CHECK_PREFIX = "check:"
REPAIR_PREFIX = "repair:"

# Points retirés pour chaque pièce remplacée pour rien
WRONG_REPAIR_PENALTY = 15

# Plafond du score quand la panne est réparée sans aucune mesure qui la prouve
UNPROVEN_SCORE = 50

# Étoiles selon le score : trois au-dessus de 80, deux au-dessus de 50
STAR_THRESHOLDS = (80, 50, 0)


@lru_cache(maxsize=1)
def load_scenarios():
    """Retourne les scénarios livrés, par identifiant, dans l'ordre du fichier."""

    vScenarios = json.loads(TROUBLESHOOTING_FILE.read_text(encoding="utf-8"))

    rScenarios = {vScenario["id"]: vScenario for vScenario in vScenarios}

    return rScenarios


def get_scenario(pScenarioId):
    """Retourne un scénario ; lève ValueError s'il n'existe pas."""

    vScenario = load_scenarios().get(pScenarioId)

    if vScenario is None:
        raise ValueError(f"Scénario inconnu : {pScenarioId}")

    return vScenario


def parse_actions(pText):
    """Retourne la liste des actions d'un texte « check:a,repair:b »."""

    rActions = [vAction for vAction in (pText or "").split(",") if vAction]

    return rActions


def get_stars(pScore):
    """Retourne le nombre d'étoiles d'un score, de 1 à 3."""

    rStars = next(
        3 - vIndex
        for vIndex, vThreshold in enumerate(STAR_THRESHOLDS)
        if pScore >= vThreshold
    )

    return rStars


def play(pScenarioId, pActions):
    """Rejoue les actions sur un scénario livré et retourne l'état de la partie."""

    rState = play_scenario(get_scenario(pScenarioId), pActions)

    return rState


def play_scenario(pScenario, pActions):
    """Rejoue les actions et retourne l'état de la partie.

    Une mesure qui demande une consignation non faite est refusée, sans
    coûter de temps. La partie s'arrête à la bonne réparation ; les actions
    suivantes sont ignorées. L'application mobile rejoue la même logique, en
    Dart : tests/fixtures/shared_lab_cases.json garde les deux identiques.
    """

    vScenario = pScenario
    vChecks = {vCheck["id"]: vCheck for vCheck in vScenario["checks"]}
    vCauses = {vCause["id"]: vCause for vCause in vScenario["causes"]}
    vDone = []
    vLog = []
    vWrong = []
    vMinutes = 0
    vSolved = False

    for vAction in pActions:
        if vSolved:
            break

        if vAction.startswith(CHECK_PREFIX):
            vCheck = vChecks.get(vAction[len(CHECK_PREFIX) :])

            if vCheck is None or vCheck["id"] in vDone:
                continue

            if vCheck.get("requires") and vCheck["requires"] not in vDone:
                vLog.append(
                    {
                        "label": vCheck["label"],
                        "result": "Refusé : consignez d'abord, cette mesure se fait "
                        "hors tension.",
                        "minutes": 0,
                        "refused": True,
                    }
                )
                continue

            vDone.append(vCheck["id"])
            vMinutes += vCheck["minutes"]
            vLog.append(
                {
                    "label": vCheck["label"],
                    "result": vCheck["result"],
                    "minutes": vCheck["minutes"],
                }
            )

        elif vAction.startswith(REPAIR_PREFIX):
            vCause = vCauses.get(vAction[len(REPAIR_PREFIX) :])

            if vCause is None or vCause["id"] in vWrong:
                continue

            vMinutes += vCause["minutes"]
            vSolved = bool(vCause.get("right"))

            if not vSolved:
                vWrong.append(vCause["id"])

            vLog.append(
                {
                    "label": vCause["label"],
                    "result": (
                        "La machine repart : panne résolue."
                        if vSolved
                        else "Essai : la panne est toujours là."
                    )
                    + (f" {vCause['note']}" if vCause.get("note") else ""),
                    "minutes": vCause["minutes"],
                    "repair": True,
                    "solved": vSolved,
                }
            )

    vProven = any(vChecks[vId].get("evidence") for vId in vDone)

    rState = {
        "scenario": vScenario,
        "done": vDone,
        "wrong": vWrong,
        "log": vLog,
        "minutes": vMinutes,
        "solved": vSolved,
        "proven": vProven,
        "score": (
            compute_score(vScenario, vMinutes, len(vWrong), vProven)
            if vSolved
            else None
        ),
    }
    rState["stars"] = get_stars(rState["score"]) if vSolved else 0

    return rState


def compute_score(pScenario, pMinutes, pWrongCount, pProven):
    """Retourne le score sur 100 : temps comparé au meilleur, moins les erreurs."""

    vScore = min(100, round(100 * pScenario["best_minutes"] / max(pMinutes, 1)))
    vScore -= WRONG_REPAIR_PENALTY * pWrongCount

    if not pProven:
        vScore = min(vScore, UNPROVEN_SCORE)

    rScore = max(vScore, 0)

    return rScore


def load_results(pDatabaseFile):
    """Retourne les parties terminées, les plus récentes en tête."""

    rResults = load_json_setting(pDatabaseFile, TROUBLESHOOTING_RESULTS_KEY, [], list)

    return rResults


def save_result(pDatabaseFile, pState, pNow=None):
    """Enregistre une partie résolue ; retourne les points gagnés."""

    vResult = {
        "scenario": pState["scenario"]["id"],
        "score": pState["score"],
        "minutes": pState["minutes"],
        "wrong": len(pState["wrong"]),
        "finished_at": (pNow or datetime.now()).isoformat(timespec="seconds"),
    }
    vResults = [vResult, *load_results(pDatabaseFile)][:MAX_RESULTS]

    save_json_setting(pDatabaseFile, TROUBLESHOOTING_RESULTS_KEY, vResults)
    logger.info(
        "Panne résolue : %s, %s points en %s min, %s pièce(s) pour rien",
        vResult["scenario"],
        vResult["score"],
        vResult["minutes"],
        vResult["wrong"],
    )

    rXp = get_result_xp(pState["score"])

    return rXp


def get_result_xp(pScore):
    """Retourne les points d'une panne résolue : un forfait plus un bonus selon le score."""

    rXp = XP_RULES["troubleshooting"][1] + TROUBLESHOOTING_XP_PER_TEN * (pScore // 10)

    return rXp


def build_overview(pDatabaseFile):
    """Retourne les scénarios avec le meilleur score et le nombre de parties."""

    vResults = load_results(pDatabaseFile)
    vRows = []

    for vScenario in load_scenarios().values():
        vScores = [
            vResult["score"]
            for vResult in vResults
            if vResult.get("scenario") == vScenario["id"]
        ]
        vBest = max(vScores, default=None)

        vRows.append(
            {
                "id": vScenario["id"],
                "title": vScenario["title"],
                "domain": vScenario["domain"],
                "symptom": vScenario["symptom"],
                "attempts": len(vScores),
                "best": vBest,
                "stars": get_stars(vBest) if vBest is not None else 0,
            }
        )

    rOverview = {
        "rows": vRows,
        "solved": sum(vRow["attempts"] > 0 for vRow in vRows),
        "stars": sum(vRow["stars"] for vRow in vRows),
        "max_stars": 3 * len(vRows),
    }

    return rOverview
