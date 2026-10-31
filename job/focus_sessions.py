"""Sessions de concentration : 25 minutes sur un objectif, points doublés

Une session suit la méthode Pomodoro : un objectif choisi, 25 minutes, puis un
bilan. Les points des actions faites pendant la session, comptées d'après leurs
horodatages, sont ajoutés une seconde fois en bonus si la session va à son
terme ; une session arrêtée avant reste au bilan, sans bonus.
"""

from datetime import datetime, timedelta

from job.progress import FOCUS_SESSIONS_KEY, XP_RULES, count_window_actions
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

GOALS = {
    "apply": "Postuler",
    "revise": "Réviser",
    "interview": "Préparer un entretien",
}
DURATION_MINUTES = 25
MAX_HISTORY = 200


def load_focus(pDatabaseFile):
    """Retourne la session en cours et les sessions passées."""

    vData = load_json_setting(pDatabaseFile, FOCUS_SESSIONS_KEY, {}, dict)

    rData = {
        "current": (
            vData.get("current") if isinstance(vData.get("current"), dict) else None
        ),
        "history": (
            vData.get("history") if isinstance(vData.get("history"), list) else []
        ),
    }

    return rData


def save_focus(pDatabaseFile, pData):
    """Enregistre la session en cours et les dernières sessions."""

    pData["history"] = pData["history"][-MAX_HISTORY:]
    save_json_setting(pDatabaseFile, FOCUS_SESSIONS_KEY, pData)


def start_focus(pDatabaseFile, pGoal, pNow):
    """Commence une session ; lève ValueError pour un objectif inconnu ou une session en cours."""

    if pGoal not in GOALS:
        raise ValueError("Choisissez un objectif pour la session.")

    vData = load_focus(pDatabaseFile)

    if vData["current"] is not None:
        raise ValueError("Une session est déjà en cours.")

    vData["current"] = {
        "goal": pGoal,
        "started_at": pNow.isoformat(timespec="seconds"),
        "ends_at": (pNow + timedelta(minutes=DURATION_MINUTES)).isoformat(
            timespec="seconds"
        ),
    }
    save_focus(pDatabaseFile, vData)
    logger.info("Session de concentration commencée : %s", GOALS[pGoal])


def describe_actions(pCounts):
    """Retourne le bilan lisible des actions : « 12 × Réponse juste en révision »."""

    rLines = [
        f"{vCount} × {XP_RULES[vAction][0]}"
        for vAction, vCount in sorted(pCounts.items(), key=lambda pItem: -pItem[1])
    ]

    return rLines


def finish_focus(pDatabaseFile, pNow):
    """Clôt la session en cours ; retourne son bilan, ou None sans session.

    La fenêtre comptée s'arrête à la fin prévue : une session oubliée ouverte ne
    compte pas les actions faites après. Le bonus n'est acquis qu'au terme.
    """

    vData = load_focus(pDatabaseFile)
    vSession = vData["current"]

    if vSession is None:
        return None

    vStart = datetime.fromisoformat(vSession["started_at"])
    vPlannedEnd = datetime.fromisoformat(vSession["ends_at"])
    vEnd = min(pNow, vPlannedEnd)
    vCompleted = pNow >= vPlannedEnd
    vCounts, vXp = count_window_actions(pDatabaseFile, vStart, vEnd)

    rSummary = {
        "goal": vSession["goal"],
        "started_at": vSession["started_at"],
        "ended_at": vEnd.isoformat(timespec="seconds"),
        "minutes": round((vEnd - vStart).total_seconds() / 60),
        "completed": vCompleted,
        "actions": vCounts,
        "xp": vXp,
        "bonus": vXp if vCompleted else 0,
    }
    vData["history"].append(rSummary)
    vData["current"] = None
    save_focus(pDatabaseFile, vData)
    logger.info(
        "Session de concentration %s : %d point(s), bonus %d",
        "terminée" if vCompleted else "arrêtée",
        vXp,
        rSummary["bonus"],
    )

    return rSummary


def build_focus_view(pDatabaseFile, pNow):
    """Retourne la session en cours, ou le bilan de la dernière ; clôt une session échue."""

    vData = load_focus(pDatabaseFile)
    vSession = vData["current"]

    if vSession is not None and pNow >= datetime.fromisoformat(vSession["ends_at"]):
        finish_focus(pDatabaseFile, pNow)
        vData = load_focus(pDatabaseFile)
        vSession = None

    vLast = vData["history"][-1] if vData["history"] else None
    vToday = pNow.date().isoformat()

    rView = {
        "goals": GOALS,
        "duration": DURATION_MINUTES,
        "current": (
            {
                **vSession,
                "goal_label": GOALS[vSession["goal"]],
                "remaining": max(
                    0,
                    round(
                        (
                            datetime.fromisoformat(vSession["ends_at"]) - pNow
                        ).total_seconds()
                    ),
                ),
            }
            if vSession
            else None
        ),
        "last": (
            {
                **vLast,
                "goal_label": GOALS.get(vLast["goal"], vLast["goal"]),
                "lines": describe_actions(vLast["actions"]),
            }
            if vLast
            else None
        ),
        "today": sum(
            1
            for vEntry in vData["history"]
            if vEntry.get("completed")
            and str(vEntry.get("ended_at", "")).startswith(vToday)
        ),
    }

    return rView
