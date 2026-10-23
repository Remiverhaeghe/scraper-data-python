"""Simulation d'entretien technique : questions ouvertes, auto-évaluées par points clés

Le candidat répond comme face à un recruteur, puis coche les points clés de la
réponse modèle qu'il a bien cités. Une question à moins de la moitié des points
rejoint l'entraînement à l'oral, en répétition espacée.
"""

import json
import random
from functools import lru_cache

from config import INTERVIEW_QUESTIONS_FILE
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Série en cours : thème, questions tirées, position et points cochés
CURRENT_KEY = "interview_simulation"

# Séries terminées, et dernier score de chaque question
HISTORY_KEY = "interview_simulation_history"
LAST_SCORES_KEY = "interview_simulation_scores"

SIMULATION_SIZE = 5
MAX_HISTORY = 30

# En dessous, la question est à retravailler dans l'entraînement à l'oral.
WEAK_SCORE = 50

# Toutes les questions, quel que soit leur thème
ALL_THEMES = "Tous les thèmes"

QUESTION_FIELDS = ("id", "theme", "question", "answer", "points")


@lru_cache
def load_interview_questions(pFile=INTERVIEW_QUESTIONS_FILE):
    """Charge les questions ouvertes ; lève ValueError si l'une est mal formée."""

    vQuestions = json.loads(pFile.read_text(encoding="utf-8"))["questions"]
    vIds = set()

    for vQuestion in vQuestions:
        vMissing = [vField for vField in QUESTION_FIELDS if not vQuestion.get(vField)]

        if vMissing or not 3 <= len(vQuestion["points"]) <= 6:
            raise ValueError(
                f"Question d'entretien {vQuestion.get('id')} : champs manquants "
                f"({', '.join(vMissing)}) ou 3 à 6 points clés attendus"
            )

        if vQuestion["id"] in vIds:
            raise ValueError(f"Question d'entretien {vQuestion['id']} en double")

        vIds.add(vQuestion["id"])

    rQuestions = {vQuestion["id"]: vQuestion for vQuestion in vQuestions}

    return rQuestions


def list_themes():
    """Retourne les thèmes proposés, dans l'ordre du fichier, précédés de « tous »."""

    rThemes = [ALL_THEMES]

    for vQuestion in load_interview_questions().values():
        if vQuestion["theme"] not in rThemes:
            rThemes.append(vQuestion["theme"])

    return rThemes


def start_simulation(pDatabaseFile, pTheme, pNow, pRandom=random):
    """Tire une série de questions du thème et la commence ; retourne son état."""

    vIds = [
        vId
        for vId, vQuestion in load_interview_questions().items()
        if pTheme == ALL_THEMES or vQuestion["theme"] == pTheme
    ]

    if not vIds:
        raise ValueError("Aucune question pour ce thème.")

    rSimulation = {
        "theme": pTheme,
        "ids": pRandom.sample(vIds, min(SIMULATION_SIZE, len(vIds))),
        "scores": [],
        "started_at": pNow.isoformat(timespec="seconds"),
    }

    save_json_setting(pDatabaseFile, CURRENT_KEY, rSimulation)

    logger.info("Simulation d'entretien commencée : %s", pTheme)

    return rSimulation


def load_simulation(pDatabaseFile):
    """Retourne la série en cours, ou None."""

    rSimulation = load_json_setting(pDatabaseFile, CURRENT_KEY, None, dict)

    return rSimulation


def get_current_question(pSimulation):
    """Retourne la question à poser avec sa position, ou None une fois la série finie."""

    if pSimulation is None or len(pSimulation["scores"]) >= len(pSimulation["ids"]):
        return None

    vQuestion = load_interview_questions().get(
        pSimulation["ids"][len(pSimulation["scores"])]
    )

    rQuestion = vQuestion and {
        **vQuestion,
        "position": len(pSimulation["scores"]) + 1,
        "count": len(pSimulation["ids"]),
    }

    return rQuestion


def compute_score(pChecked, pPointCount):
    """Retourne la part des points clés cités, sur 100."""

    rScore = round(100 * len(set(pChecked)) / pPointCount)

    return rScore


def record_answer(pDatabaseFile, pChecked, pNow):
    """Note la question en cours d'après les points cochés ; retourne la série.

    pChecked liste les indices des points clés cités. La série terminée rejoint
    l'historique.
    """

    vSimulation = load_simulation(pDatabaseFile)
    vQuestion = get_current_question(vSimulation)

    if vQuestion is None:
        raise ValueError("Aucune simulation en cours.")

    vChecked = [vIndex for vIndex in pChecked if 0 <= vIndex < len(vQuestion["points"])]
    vScore = compute_score(vChecked, len(vQuestion["points"]))
    vSimulation["scores"].append(vScore)

    vLastScores = load_json_setting(pDatabaseFile, LAST_SCORES_KEY, {}, dict)
    vLastScores[vQuestion["id"]] = vScore
    save_json_setting(pDatabaseFile, LAST_SCORES_KEY, vLastScores)

    if len(vSimulation["scores"]) == len(vSimulation["ids"]):
        vHistory = load_json_setting(pDatabaseFile, HISTORY_KEY, [], list)
        vHistory.insert(
            0,
            {
                "theme": vSimulation["theme"],
                "finished_at": pNow.isoformat(timespec="seconds"),
                "score": round(sum(vSimulation["scores"]) / len(vSimulation["scores"])),
            },
        )
        save_json_setting(pDatabaseFile, HISTORY_KEY, vHistory[:MAX_HISTORY])

        logger.info(
            "Simulation d'entretien terminée : %s, %s %%",
            vSimulation["theme"],
            vHistory[0]["score"],
        )

    save_json_setting(pDatabaseFile, CURRENT_KEY, vSimulation)

    rSimulation = vSimulation

    return rSimulation


def summarize_simulation(pSimulation):
    """Retourne le score moyen et les questions à retravailler d'une série finie."""

    vQuestions = load_interview_questions()

    rSummary = {
        "score": round(sum(pSimulation["scores"]) / len(pSimulation["scores"])),
        "weak": [
            vQuestions[vId]["question"]
            for vId, vScore in zip(pSimulation["ids"], pSimulation["scores"])
            if vId in vQuestions and vScore < WEAK_SCORE
        ],
    }

    return rSummary


def stop_simulation(pDatabaseFile):
    """Abandonne ou ferme la série en cours."""

    save_json_setting(pDatabaseFile, CURRENT_KEY, None)


def get_history(pDatabaseFile):
    """Retourne les séries terminées, la plus récente en tête."""

    rHistory = load_json_setting(pDatabaseFile, HISTORY_KEY, [], list)

    return rHistory


def get_weak_questions(pDatabaseFile):
    """Retourne les questions dont le dernier score est sous WEAK_SCORE."""

    vQuestions = load_interview_questions()

    rWeak = [
        vQuestions[vId]
        for vId, vScore in load_json_setting(
            pDatabaseFile, LAST_SCORES_KEY, {}, dict
        ).items()
        if vId in vQuestions and vScore < WEAK_SCORE
    ]

    return rWeak


def format_model_answer(pQuestion):
    """Retourne la réponse modèle suivie de ses points clés, pour une carte d'oral."""

    rText = (
        pQuestion["answer"]
        + "\n\nPoints clés :\n"
        + "\n".join(f"• {vPoint}" for vPoint in pQuestion["points"])
    )

    return rText


# Séries envoyées par le téléphone en une synchronisation, au plus
MAX_PHONE_SERIES = 20


def read_phone_series(pSeries, pQuestions):
    """Retourne le thème et les scores d'une série du téléphone ; ignore l'illisible."""

    vScores = []

    for vResult in pSeries.get("results") or []:
        vQuestion = pQuestions.get(vResult.get("question_id"))
        vChecked = vResult.get("checked")

        if vQuestion is None or not isinstance(vChecked, list):
            continue

        vChecked = [
            vIndex
            for vIndex in vChecked
            if isinstance(vIndex, int)
            and not isinstance(vIndex, bool)
            and 0 <= vIndex < len(vQuestion["points"])
        ]
        vScores.append(
            (vQuestion["id"], compute_score(vChecked, len(vQuestion["points"])))
        )

    rSeries = (str(pSeries.get("theme") or ALL_THEMES), vScores)

    return rSeries


def record_phone_series(pDatabaseFile, pSeries, pNow):
    """Ajoute à l'historique les séries faites sur le téléphone ; retourne leur nombre.

    Les derniers scores alimentent l'entraînement à l'oral, comme sur le PC.
    """

    if not isinstance(pSeries, list) or len(pSeries) > MAX_PHONE_SERIES:
        raise ValueError(f"Liste de {MAX_PHONE_SERIES} séries au plus attendue.")

    vQuestions = load_interview_questions()
    vLastScores = load_json_setting(pDatabaseFile, LAST_SCORES_KEY, {}, dict)
    vHistory = load_json_setting(pDatabaseFile, HISTORY_KEY, [], list)
    rCount = 0

    for vSeries in pSeries:
        if not isinstance(vSeries, dict):
            continue

        vTheme, vScores = read_phone_series(vSeries, vQuestions)

        if not vScores:
            continue

        vLastScores.update(vScores)
        vHistory.insert(
            0,
            {
                "theme": vTheme,
                "finished_at": str(
                    vSeries.get("finished_at") or pNow.isoformat(timespec="seconds")
                )[:19],
                "score": round(sum(vScore for _, vScore in vScores) / len(vScores)),
            },
        )
        rCount += 1

    save_json_setting(pDatabaseFile, LAST_SCORES_KEY, vLastScores)
    save_json_setting(pDatabaseFile, HISTORY_KEY, vHistory[:MAX_HISTORY])

    logger.info("Simulation d'entretien : %s série(s) reçue(s) du téléphone", rCount)

    return rCount
