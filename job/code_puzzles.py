"""Puzzles de code : lignes à remettre dans l'ordre, ligne fautive, code à trou

Les puzzles se jouent par séries de dix, de la plus facile à la plus dure. Le
niveau du joueur monte après une bonne série et descend après une mauvaise ; la
série de bonnes réponses d'affilée et le récapitulatif des erreurs sont gardés
avec la progression. Les types « ordre » et « saisie » sont ceux de la révision
(job/quiz_types.py), corrigés de la même façon.
"""

import json
import random
import secrets
from functools import lru_cache

from config import PUZZLES_FILE
from job.quiz_types import (
    check_completion,
    check_order,
    grade_completion,
    grade_order,
    is_text_list,
    prepare_question,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Niveau, séries et récapitulatifs, lus aussi par job/progress.py pour l'XP
PUZZLE_PROGRESS_KEY = "code_puzzles"
TYPE_LABELS = {
    "ordre": "Lignes à remettre dans l'ordre",
    "ligne": "Ligne fautive",
    "saisie": "Code à compléter",
}
LEVEL_LABELS = {1: "débutant", 2: "intermédiaire", 3: "confirmé"}
LEVELS = tuple(LEVEL_LABELS)
SERIES_LENGTH = 10
# Composition d'une série : écart au niveau du joueur, nombre de puzzles
SERIES_PLAN = ((-1, 3), (0, 5), (1, 2))
LEVEL_UP_SCORE = 8
LEVEL_DOWN_SCORE = 4
MAX_HISTORY = 200
MAX_SEED = 2**31
UNREADABLE_ANSWER = "réponse illisible"
REQUIRED_FIELDS = ("id", "type", "language", "level", "title", "prompt", "explanation")


def check_puzzle(pPuzzle):
    """Retourne le défaut d'un puzzle livré, ou ""."""

    if not isinstance(pPuzzle, dict) or any(
        vField not in pPuzzle for vField in REQUIRED_FIELDS
    ):
        return "champ manquant"

    if pPuzzle["type"] not in TYPE_LABELS or pPuzzle["level"] not in LEVELS:
        return "type ou niveau inconnu"

    if pPuzzle["type"] == "ordre":
        return check_order(pPuzzle)

    if pPuzzle["type"] == "saisie":
        return check_completion(pPuzzle)

    if not is_text_list(pPuzzle.get("lines"), 3, 12) or not (
        isinstance(pPuzzle.get("line"), int)
        and 1 <= pPuzzle["line"] <= len(pPuzzle["lines"])
    ):
        return "3 à 12 lignes et le numéro de la ligne fautive attendus"

    return ""


@lru_cache(maxsize=1)
def load_puzzles():
    """Retourne les puzzles livrés, par identifiant ; lève ValueError si l'un est invalide."""

    rPuzzles = {}

    for vPuzzle in json.loads(PUZZLES_FILE.read_text(encoding="utf-8")):
        vDefect = check_puzzle(vPuzzle)

        if vDefect or vPuzzle["id"] in rPuzzles:
            raise ValueError(
                f"Puzzle invalide {vPuzzle.get('id')} : {vDefect or 'doublon'}"
            )

        rPuzzles[vPuzzle["id"]] = vPuzzle

    return rPuzzles


def prepare_puzzle(pPuzzle, pSeed):
    """Retourne le puzzle prêt à afficher ; l'ordre mélangé dépend de la série."""

    if pPuzzle["type"] == "ligne":
        vQuestion = {**pPuzzle, "shuffled": list(enumerate(pPuzzle["lines"]))}
    else:
        # Mélange reproductible d'un exercice, sans usage cryptographique.
        vRandom = random.Random(f"{pSeed}-{pPuzzle['id']}")  # nosec B311
        vQuestion = prepare_question(pPuzzle, vRandom)

    rQuestion = {
        **vQuestion,
        "type_label": TYPE_LABELS[pPuzzle["type"]],
        "level_label": LEVEL_LABELS[pPuzzle["level"]],
    }

    return rQuestion


def grade_puzzle(pPuzzle, pResponse):
    """Corrige une réponse ; retourne (juste, réponse donnée, réponse attendue).

    Lève ValueError si la réponse est incomplète ou illisible.
    """

    if pPuzzle["type"] == "ordre":
        return grade_order(pPuzzle, pResponse)

    if pPuzzle["type"] == "saisie":
        return grade_completion(pPuzzle, pResponse)

    vLines = pPuzzle["lines"]

    if (
        not isinstance(pResponse, int)
        or isinstance(pResponse, bool)
        or not 0 <= pResponse < len(vLines)
    ):
        raise ValueError("Touchez la ligne fautive.")

    rGrade = (
        pResponse == pPuzzle["line"] - 1,
        f"ligne {pResponse + 1} : {vLines[pResponse].strip()}",
        f"ligne {pPuzzle['line']} : {vLines[pPuzzle['line'] - 1].strip()}",
    )

    return rGrade


def get_next_level(pLevel, pScore):
    """Retourne le niveau après une série : plus haut si elle est bonne, plus bas sinon."""

    rLevel = pLevel

    if pScore >= LEVEL_UP_SCORE:
        rLevel = min(pLevel + 1, LEVELS[-1])
    elif pScore <= LEVEL_DOWN_SCORE:
        rLevel = max(pLevel - 1, LEVELS[0])

    return rLevel


def draw_series(pPuzzles, pLevel, pStats, pRandom):
    """Retourne les puzzles d'une série, du plus facile au plus dur.

    Autour du niveau du joueur, les puzzles jamais vus passent d'abord, puis
    ceux manqués la dernière fois, puis ceux déjà réussis.
    """

    def rank(pPuzzle):
        vStat = pStats.get(pPuzzle["id"])

        return 0 if vStat is None else 1 if not vStat.get("last") else 2

    vChosen = []

    for vOffset, vCount in SERIES_PLAN:
        vLevel = min(max(pLevel + vOffset, LEVELS[0]), LEVELS[-1])
        vPool = [
            vPuzzle
            for vPuzzle in pPuzzles.values()
            if vPuzzle["level"] == vLevel and vPuzzle["id"] not in vChosen
        ]
        pRandom.shuffle(vPool)
        vPool.sort(key=rank)
        vChosen += [vPuzzle["id"] for vPuzzle in vPool[:vCount]]

    vRest = [vId for vId in pPuzzles if vId not in vChosen]
    pRandom.shuffle(vRest)
    vRest.sort(key=lambda pId: abs(pPuzzles[pId]["level"] - pLevel))
    vChosen += vRest[: SERIES_LENGTH - len(vChosen)]

    rSeries = sorted(vChosen, key=lambda pId: pPuzzles[pId]["level"])

    return rSeries


def load_puzzle_progress(pDatabaseFile):
    """Retourne la progression : niveau, séries de réussites, statistiques, série en cours."""

    vProgress = load_json_setting(pDatabaseFile, PUZZLE_PROGRESS_KEY, {}, dict)

    rProgress = {
        "level": vProgress.get("level") if vProgress.get("level") in LEVELS else 1,
        "streak": int(vProgress.get("streak") or 0),
        "best_streak": int(vProgress.get("best_streak") or 0),
        "stats": (
            vProgress.get("stats") if isinstance(vProgress.get("stats"), dict) else {}
        ),
        "current": (
            vProgress.get("current")
            if isinstance(vProgress.get("current"), dict)
            else None
        ),
        "history": (
            vProgress.get("history")
            if isinstance(vProgress.get("history"), list)
            else []
        ),
    }

    return rProgress


def save_puzzle_progress(pDatabaseFile, pProgress):
    """Enregistre la progression, en gardant les dernières séries seulement."""

    pProgress["history"] = pProgress["history"][-MAX_HISTORY:]
    save_json_setting(pDatabaseFile, PUZZLE_PROGRESS_KEY, pProgress)


def new_series(pProgress, pIds, pSeed):
    """Retourne une série vide, jouée au niveau actuel du joueur."""

    rSeries = {"ids": pIds, "seed": pSeed, "level": pProgress["level"], "answers": []}

    return rSeries


def start_series(pDatabaseFile, pRandom=None):
    """Tire une nouvelle série et l'enregistre comme série en cours."""

    vProgress = load_puzzle_progress(pDatabaseFile)
    # Tirage d'exercices, sans usage cryptographique.
    vRandom = pRandom or random.Random(secrets.randbelow(MAX_SEED))  # nosec B311
    vIds = draw_series(load_puzzles(), vProgress["level"], vProgress["stats"], vRandom)
    vProgress["current"] = new_series(vProgress, vIds, vRandom.randrange(MAX_SEED))
    save_puzzle_progress(pDatabaseFile, vProgress)
    logger.info("Série de puzzles commencée au niveau %d", vProgress["level"])


def get_answer(pPuzzle):
    """Retourne la bonne réponse d'un puzzle, au format des réponses saisies."""

    if pPuzzle["type"] == "ordre":
        return list(range(len(pPuzzle["items"])))

    if pPuzzle["type"] == "saisie":
        return pPuzzle["accepted"][0]

    rAnswer = pPuzzle["line"] - 1

    return rAnswer


def record_answer(pProgress, pPuzzleId, pGrade):
    """Ajoute une réponse corrigée à la série en cours et met à jour la progression."""

    vCorrect, vGiven, vExpected = pGrade
    vStat = pProgress["stats"].setdefault(pPuzzleId, {"right": 0, "wrong": 0})

    vStat["right" if vCorrect else "wrong"] += 1
    vStat["last"] = vCorrect
    pProgress["streak"] = pProgress["streak"] + 1 if vCorrect else 0
    pProgress["best_streak"] = max(pProgress["best_streak"], pProgress["streak"])
    pProgress["current"]["answers"].append(
        {"id": pPuzzleId, "correct": vCorrect, "given": vGiven, "expected": vExpected}
    )


def finish_series(pProgress, pFinishedAt):
    """Clôt la série en cours : score, nouveau niveau, erreurs gardées pour le récapitulatif."""

    vSeries = pProgress["current"]
    vScore = sum(vAnswer["correct"] for vAnswer in vSeries["answers"])

    pProgress["level"] = get_next_level(pProgress["level"], vScore)
    pProgress["history"].append(
        {
            "finished_at": pFinishedAt.isoformat(timespec="seconds"),
            "level": vSeries["level"],
            "score": vScore,
            "mistakes": [
                vAnswer for vAnswer in vSeries["answers"] if not vAnswer["correct"]
            ],
        }
    )
    pProgress["current"] = None
    logger.info(
        "Série de puzzles terminée : %d/%d, niveau %d",
        vScore,
        SERIES_LENGTH,
        pProgress["level"],
    )


def answer_puzzle(pDatabaseFile, pPosition, pResponse, pNow):
    """Corrige la réponse au puzzle en cours ; retourne le retour à afficher.

    pPosition est la place du puzzle dans la série : un formulaire renvoyé deux
    fois ne répond pas au puzzle suivant. Lève ValueError sinon.
    """

    vProgress = load_puzzle_progress(pDatabaseFile)
    vSeries = vProgress["current"]

    if vSeries is None:
        raise ValueError("Aucune série en cours : commencez-en une.")

    if pPosition != len(vSeries["answers"]):
        raise ValueError("Ce puzzle a déjà reçu sa réponse.")

    vPuzzle = load_puzzles()[vSeries["ids"][pPosition]]
    vCorrect, vGiven, vExpected = grade_puzzle(vPuzzle, pResponse)
    record_answer(vProgress, vPuzzle["id"], (vCorrect, vGiven, vExpected))
    vFinished = len(vSeries["answers"]) == len(vSeries["ids"])

    if vFinished:
        finish_series(vProgress, pNow)

    save_puzzle_progress(pDatabaseFile, vProgress)

    rFeedback = {
        "correct": vCorrect,
        "given": vGiven,
        "expected": vExpected,
        "explanation": vPuzzle["explanation"],
        "streak": vProgress["streak"],
        "finished": vFinished,
    }

    return rFeedback


def build_recap(pEntry):
    """Retourne le récapitulatif d'une série terminée : score et erreurs commentées."""

    vPuzzles = load_puzzles()

    rRecap = {
        "score": pEntry["score"],
        "total": SERIES_LENGTH,
        "mistakes": [
            {
                **vMistake,
                "title": vPuzzles[vMistake["id"]]["title"],
                "language": vPuzzles[vMistake["id"]]["language"],
                "explanation": vPuzzles[vMistake["id"]]["explanation"],
            }
            for vMistake in pEntry["mistakes"]
            if vMistake["id"] in vPuzzles
        ],
    }

    return rRecap


def build_puzzle_view(pDatabaseFile):
    """Retourne ce qu'affichent les pages : progression, puzzle en cours, dernier bilan."""

    vProgress = load_puzzle_progress(pDatabaseFile)
    vSeries = vProgress["current"]
    vPuzzle = None

    if vSeries is not None:
        vPosition = len(vSeries["answers"])
        vPuzzle = {
            **prepare_puzzle(
                load_puzzles()[vSeries["ids"][vPosition]], vSeries["seed"]
            ),
            "position": vPosition,
        }

    rView = {
        "level": vProgress["level"],
        "level_label": LEVEL_LABELS[vProgress["level"]],
        "streak": vProgress["streak"],
        "best_streak": vProgress["best_streak"],
        "series_count": len(vProgress["history"]),
        "total": SERIES_LENGTH,
        "puzzle": vPuzzle,
        "recap": (
            build_recap(vProgress["history"][-1])
            if vSeries is None and vProgress["history"]
            else None
        ),
    }

    return rView


def replay_series(pDatabaseFile, pAnswers, pFinishedAt):
    """Recorrige une série jouée sur le téléphone et l'ajoute à la progression du PC.

    pAnswers liste les réponses {id, response} de la série, dans l'ordre joué.
    Lève ValueError si la série est incomplète, en double ou illisible ; la
    série en cours sur le PC n'est pas touchée.
    """

    vPuzzles = load_puzzles()

    if (
        not isinstance(pAnswers, list)
        or len(pAnswers) != SERIES_LENGTH
        or not all(isinstance(vAnswer, dict) for vAnswer in pAnswers)
    ):
        raise ValueError("série incomplète")

    vIds = [vAnswer.get("id") for vAnswer in pAnswers]

    if len(set(vIds)) != len(vIds) or not all(vId in vPuzzles for vId in vIds):
        raise ValueError("puzzle inconnu ou en double")

    vProgress = load_puzzle_progress(pDatabaseFile)
    vCurrent = vProgress["current"]
    vProgress["current"] = new_series(vProgress, vIds, 0)

    for vAnswer in pAnswers:
        vPuzzle = vPuzzles[vAnswer["id"]]

        # Une réponse illisible compte comme fausse, sans écarter toute la série
        try:
            vGrade = grade_puzzle(vPuzzle, vAnswer.get("response"))

        except ValueError:
            vGrade = (
                False,
                UNREADABLE_ANSWER,
                grade_puzzle(vPuzzle, get_answer(vPuzzle))[2],
            )

        record_answer(vProgress, vPuzzle["id"], vGrade)

    finish_series(vProgress, pFinishedAt)
    vProgress["current"] = vCurrent
    save_puzzle_progress(pDatabaseFile, vProgress)

    rScore = vProgress["history"][-1]["score"]

    return rScore
