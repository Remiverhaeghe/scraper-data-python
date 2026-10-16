"""Mode examen : une série de questions tirées au hasard, notée et chronométrée

L'examen en cours est enregistré dans les réglages : il se poursuit après un
changement de page, et indifféremment sur le bureau ou le web. Chaque réponse
compte aussi dans la progression et la répétition espacée.
"""

import json
import random
from datetime import datetime

from job.quiz import answer_question, build_quiz_overview, find_question
from job.quiz_types import prepare_question
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

EXAM_KEY = "quiz_exam"
EXAM_QUESTION_COUNT = 20

# Durée conseillée : une minute par question, comme dans beaucoup de tests
# techniques de recrutement.
SECONDS_PER_QUESTION = 60


def load_exam(pDatabaseFile):
    """Retourne l'examen en cours, ou None."""

    vValue = get_setting_values(pDatabaseFile).get(EXAM_KEY)

    try:
        rExam = json.loads(vValue) if vValue else None

    except ValueError:
        logger.warning("Examen en cours illisible : ignoré")

        rExam = None

    return rExam


def save_exam(pDatabaseFile, pExam):
    """Enregistre l'état de l'examen, ou l'efface avec None."""

    save_setting_values(
        pDatabaseFile,
        {EXAM_KEY: json.dumps(pExam, ensure_ascii=False) if pExam else ""},
    )


def start_exam(
    pDatabaseFile,
    pQuiz,
    pDomain,
    pNow,
    pRandom=random,
    pSubdomain=None,
    pThemeKeys=None,
    pTitle=None,
):
    """Tire les questions d'une catégorie, ou de toutes, et commence l'examen.

    pThemeKeys restreint le tirage à certains thèmes, ceux d'une offre par exemple.
    Lève ValueError si le domaine ne contient aucune question.
    """

    vThemes = {
        vTheme["key"]: vTheme
        for vTheme in build_quiz_overview(pDatabaseFile, pQuiz)
        if (not pDomain or vTheme["domain"] == pDomain)
        and (not pSubdomain or vTheme["subdomain"] == pSubdomain)
        and (pThemeKeys is None or vTheme["key"] in pThemeKeys)
    }
    vQuestions = [
        vQuestion["id"] for vKey in vThemes for vQuestion in pQuiz[vKey]["questions"]
    ]

    if not vQuestions:
        raise ValueError("Aucune question dans ce domaine.")

    # Tirage pour varier les examens, sans enjeu de sécurité.
    vIds = pRandom.sample(
        vQuestions, min(EXAM_QUESTION_COUNT, len(vQuestions))
    )  # nosec B311

    rExam = {
        "domain": pDomain,
        "subdomain": pSubdomain,
        "title": pTitle,
        "ids": vIds,
        "index": 0,
        "correct": 0,
        "wrong": [],
        "started_at": pNow.isoformat(timespec="seconds"),
        "finished_at": None,
    }

    save_exam(pDatabaseFile, rExam)

    logger.info(
        "Examen commencé : %s question(s), domaine %s", len(vIds), pDomain or "tous"
    )

    return rExam


def get_exam_question(pQuiz, pExam, pRandom=random):
    """Retourne la question en cours, éléments mélangés, ou None si l'examen est fini."""

    rQuestion = None

    if pExam and not pExam["finished_at"]:
        vId = pExam["ids"][pExam["index"]]
        vFound = next(
            (
                (vQuestion, vKey)
                for vKey, vTheme in pQuiz.items()
                for vQuestion in vTheme["questions"]
                if vQuestion["id"] == vId
            ),
            None,
        )

        if vFound:
            vQuestion, vKey = vFound
            rQuestion = {
                **prepare_question(vQuestion, pRandom),
                "theme_key": vKey,
                "theme_label": pQuiz[vKey]["label"],
                "position": pExam["index"] + 1,
                "count": len(pExam["ids"]),
            }

    return rQuestion


def answer_exam(pDatabaseFile, pQuiz, pResponse, pNow):
    """Corrige la réponse à la question en cours ; retourne (correction, examen).

    Une question supprimée depuis le début de l'examen est passée. Lève
    ValueError sans avancer si la réponse est illisible.
    """

    vExam = load_exam(pDatabaseFile)

    if not vExam or vExam["finished_at"]:
        raise ValueError("Aucun examen en cours.")

    vId = vExam["ids"][vExam["index"]]

    rResult = None

    if find_question(pQuiz, vId)[0] is not None:
        rResult = answer_question(pDatabaseFile, pQuiz, vId, pResponse, pNow)

    if rResult and rResult["correct"]:
        vExam["correct"] += 1
    elif rResult:
        vExam["wrong"].append(vId)

    vExam["index"] += 1

    if vExam["index"] >= len(vExam["ids"]):
        vExam["finished_at"] = pNow.isoformat(timespec="seconds")

        logger.info("Examen terminé : %s / %s", vExam["correct"], len(vExam["ids"]))

    save_exam(pDatabaseFile, vExam)

    return rResult, vExam


def summarize_exam(pQuiz, pExam):
    """Résume un examen terminé : note, durée et thèmes à revoir."""

    vCount = len(pExam["ids"])
    vSeconds = (
        datetime.fromisoformat(pExam["finished_at"])
        - datetime.fromisoformat(pExam["started_at"])
    ).total_seconds()

    vThemes = {}

    for vTheme in pQuiz.values():
        for vQuestion in vTheme["questions"]:
            if vQuestion["id"] in pExam["wrong"]:
                vThemes[vTheme["label"]] = vThemes.get(vTheme["label"], 0) + 1

    rSummary = {
        "correct": pExam["correct"],
        "count": vCount,
        "score": round(100 * pExam["correct"] / vCount) if vCount else 0,
        "minutes": int(vSeconds // 60),
        "seconds": int(vSeconds % 60),
        "overtime": vSeconds > vCount * SECONDS_PER_QUESTION,
        "advised_minutes": vCount * SECONDS_PER_QUESTION // 60,
        "to_review": sorted(vThemes.items(), key=lambda pItem: (-pItem[1], pItem[0])),
    }

    return rSummary


def describe_exam_summary(pSummary):
    """Décrit le résultat d'un examen en une phrase, puis les thèmes à revoir."""

    vDuration = f"{pSummary['minutes']} min {pSummary['seconds']:02d} s"
    vTime = (
        f"en {vDuration}, au-delà des {pSummary['advised_minutes']} min conseillées"
        if pSummary["overtime"]
        else f"en {vDuration}"
    )

    rText = (
        f"Note : {pSummary['correct']} / {pSummary['count']} "
        f"({pSummary['score']} %) {vTime}."
    )

    if pSummary["to_review"]:
        rText += (
            " À revoir : "
            + ", ".join(
                f"{vLabel} ({vCount} erreur(s))"
                for vLabel, vCount in pSummary["to_review"]
            )
            + "."
        )
    else:
        rText += " Aucune erreur."

    return rText


def stop_exam(pDatabaseFile):
    """Abandonne ou referme l'examen en cours."""

    save_exam(pDatabaseFile, None)

    logger.info("Examen refermé")
