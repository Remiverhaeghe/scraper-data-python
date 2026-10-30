"""Simulations de l'application mobile : contenu à emporter, parties à intégrer

Le téléphone joue hors ligne avec sa propre version de chaque simulateur, en
Dart. Le contenu (scénarios, niveaux) vient d'ici, seul endroit où il se
modifie. Au retour, le PC ne croit pas le score annoncé : il rejoue les actions
avec le simulateur de référence, puis enregistre la partie comme sur le bureau.
"""

from datetime import datetime

from job.progress import TROUBLESHOOTING_XP_PER_TEN, XP_RULES
from job.troubleshooting import (
    STAR_THRESHOLDS,
    UNPROVEN_SCORE,
    WRONG_REPAIR_PENALTY,
    load_scenarios,
    play,
    save_result,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Identifiants des parties déjà intégrées : un envoi répété n'est pas compté deux fois
RECEIVED_KEY = "mobile_lab_ids"
MAX_RECEIVED = 1000
MAX_RESULTS_PER_SYNC = 200
MAX_ACTIONS = 100


def build_labs_package():
    """Retourne le contenu des simulations jouables sur le téléphone."""

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
        },
    }

    return rPackage


def read_result(pItem):
    """Vérifie une partie envoyée ; retourne (id, laboratoire, contenu, date) ou lève ValueError."""

    if not isinstance(pItem, dict):
        raise ValueError("partie illisible")

    vId = pItem.get("id")
    vActions = pItem.get("actions")

    if not isinstance(vId, str) or not 1 <= len(vId) <= 64:
        raise ValueError("identifiant de partie manquant")

    if (
        not isinstance(vActions, list)
        or len(vActions) > MAX_ACTIONS
        or not all(isinstance(vAction, str) for vAction in vActions)
    ):
        raise ValueError("actions illisibles")

    try:
        vFinishedAt = datetime.fromisoformat(str(pItem.get("finished_at")))

    except ValueError as vError:
        raise ValueError("date de fin illisible") from vError

    rResult = (vId, pItem.get("lab"), pItem.get("scenario"), vActions, vFinishedAt)

    return rResult


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
            vId, vLab, vScenarioId, vActions, vFinishedAt = read_result(vItem)

            if vId in vReceived:
                continue

            if vLab != "troubleshooting" or vScenarioId not in load_scenarios():
                raise ValueError("simulation ou scénario inconnu")

            vState = play(vScenarioId, vActions)

            if not vState["solved"]:
                raise ValueError("panne non résolue")

        except ValueError as vError:
            vRejected.append(
                {
                    "id": vItem.get("id") if isinstance(vItem, dict) else None,
                    "reason": str(vError),
                }
            )
            continue

        vXp += save_result(pDatabaseFile, vState, vFinishedAt)
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
