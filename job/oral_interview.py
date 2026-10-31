"""Entretien oral simulé : questions lues à voix haute, réponse chronométrée, grille

Chaque question est lue par la synthèse vocale de l'appareil, puis le candidat
répond à voix haute dans le temps choisi. Il note ensuite sa réponse : structure
et exemple concret selon lui, durée d'après le temps mesuré. Rien n'est
enregistré du son : seules les notes sont gardées, pour suivre la progression
d'une séance à l'autre.
"""

import random
from datetime import datetime

from job.agencies import load_interim_agencies
from job.interview_simulation import load_interview_questions
from job.star_answers import BEHAVIORAL_QUESTIONS
from job.tricky_questions import (
    EMPLOYER_LABELS,
    TRICKY_QUESTIONS,
    build_tricky_questions,
)
from job.weekly_digest import get_coming_interviews
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Séance en cours et séances terminées ; lues aussi par job/progress.py pour l'XP
ORAL_KEY = "oral_interviews"
MODES = {
    "general": "Questions classiques",
    "tricky": "Questions pièges",
    "technical": "Questions techniques",
}
DURATIONS = (60, 90, 120)
SESSION_LENGTH = 5
# En deçà, la réponse est trop courte pour convaincre
MIN_SECONDS = 20
MAX_SECONDS = 3600
MAX_HISTORY = 100
CRITERIA = (
    ("structure", "Structure", "Idée annoncée, développée, puis conclue"),
    ("example", "Exemple concret", "Une situation vécue, avec son résultat"),
    ("duration", "Durée", "Ni trop courte, ni au-delà du temps"),
)
RATINGS = {0: "Non", 1: "En partie", 2: "Oui"}
DURATION_RATINGS = {0: "trop courte", 1: "au-delà du temps", 2: "dans le temps"}
GENERAL_QUESTIONS = (
    (
        "Présentez-vous en deux minutes.",
        "Parcours, compétence phare, réussite récente, puis ce que vous cherchez.",
    ),
    (
        "Pourquoi avez-vous postulé chez nous ?",
        "Citez un fait précis sur l'entreprise, puis ce que vous lui apportez.",
    ),
    (
        "Quelles sont vos principales qualités ?",
        "Deux qualités, chacune illustrée par un fait vérifiable.",
    ),
    (
        "Quel est votre principal défaut ?",
        "Un vrai défaut, sans rapport direct avec le cœur du poste, et ce que "
        "vous faites pour le corriger.",
    ),
    (
        "Où vous voyez-vous dans cinq ans ?",
        "Une évolution crédible dans le métier, compatible avec le poste.",
    ),
    *(
        (vQuestion, "Méthode STAR : situation, tâche, action, résultat.")
        for vQuestion in BEHAVIORAL_QUESTIONS.values()
    ),
)


def build_questions(pDatabaseFile, pMode, pNow):
    """Retourne les questions d'un mode : (question, conseil) et la cible éventuelle.

    Les questions pièges sont celles du prochain entretien prévu, selon le type
    d'employeur ; sans entretien, celles de tous les employeurs.
    """

    if pMode == "general":
        return (list(GENERAL_QUESTIONS), "")

    if pMode == "technical":
        return (
            [
                (vQuestion["question"], " ; ".join(vQuestion["points"]))
                for vQuestion in load_interview_questions().values()
            ],
            "",
        )

    vInterviews = get_coming_interviews(pDatabaseFile, pNow)

    if vInterviews:
        vTricky = build_tricky_questions(
            vInterviews[0], load_interim_agencies(pDatabaseFile)
        )

        return (
            [(vItem["question"], vItem["hint"]) for vItem in vTricky["questions"]],
            f"{vInterviews[0].get('company') or 'prochain entretien'} · "
            f"{vTricky['employer']}",
        )

    rQuestions = (
        [vItem for vKind in EMPLOYER_LABELS for vItem in TRICKY_QUESTIONS[vKind]],
        "",
    )

    return rQuestions


def load_oral(pDatabaseFile):
    """Retourne la séance en cours et l'historique."""

    vData = load_json_setting(pDatabaseFile, ORAL_KEY, {}, dict)

    rData = {
        "current": (
            vData.get("current") if isinstance(vData.get("current"), dict) else None
        ),
        "history": (
            vData.get("history") if isinstance(vData.get("history"), list) else []
        ),
    }

    return rData


def save_oral(pDatabaseFile, pData):
    """Enregistre la séance en cours et les dernières séances terminées."""

    pData["history"] = pData["history"][-MAX_HISTORY:]
    save_json_setting(pDatabaseFile, ORAL_KEY, pData)


def start_oral(pDatabaseFile, pMode, pDuration, pNow, pRandom=random):
    """Tire les questions d'une séance et l'enregistre ; lève ValueError si un choix est inconnu."""

    if pMode not in MODES or pDuration not in DURATIONS:
        raise ValueError("Choisissez un type de questions et un temps de réponse.")

    vQuestions, vTarget = build_questions(pDatabaseFile, pMode, pNow)
    vData = load_oral(pDatabaseFile)
    vData["current"] = {
        "mode": pMode,
        "duration": pDuration,
        "target": vTarget,
        "questions": [
            {"question": vQuestion, "hint": vHint}
            for vQuestion, vHint in pRandom.sample(
                vQuestions, min(SESSION_LENGTH, len(vQuestions))
            )
        ],
        "answers": [],
    }
    save_oral(pDatabaseFile, vData)
    logger.info("Entretien oral commencé : %s, %d s par réponse", pMode, pDuration)


def rate_duration(pSeconds, pDuration):
    """Retourne la note de durée : 0 trop courte, 1 au-delà du temps, 2 dans le temps."""

    if pSeconds < MIN_SECONDS:
        return 0

    rRating = 2 if pSeconds <= pDuration else 1

    return rRating


def grade_answer(pSeconds, pDuration, pStructure, pExample):
    """Retourne la réponse notée ; lève ValueError si une note ou le temps est illisible."""

    if (
        not all(
            isinstance(vRating, int)
            and not isinstance(vRating, bool)
            and vRating in RATINGS
            for vRating in (pStructure, pExample)
        )
        or not isinstance(pSeconds, (int, float))
        or isinstance(pSeconds, bool)
        or not 0 <= pSeconds <= MAX_SECONDS
    ):
        raise ValueError("Notez la structure et l'exemple de votre réponse.")

    # Arrondie d'abord : la durée notée est celle affichée
    vSeconds = round(pSeconds)
    vDuration = rate_duration(vSeconds, pDuration)

    rAnswer = {
        "seconds": vSeconds,
        "structure": pStructure,
        "example": pExample,
        "duration": vDuration,
        "score": round(100 * (pStructure + pExample + vDuration) / (2 * len(CRITERIA))),
    }

    return rAnswer


def summarize_session(pSession, pFinishedAt):
    """Retourne la séance terminée : note moyenne et moyenne de chaque critère sur 2."""

    vAnswers = pSession["answers"]

    rSummary = {
        "finished_at": pFinishedAt.isoformat(timespec="seconds"),
        "mode": pSession["mode"],
        "duration": pSession["duration"],
        "count": len(vAnswers),
        "score": round(sum(vAnswer["score"] for vAnswer in vAnswers) / len(vAnswers)),
        "criteria": {
            vId: round(sum(vAnswer[vId] for vAnswer in vAnswers) / len(vAnswers), 1)
            for vId, _, _ in CRITERIA
        },
    }

    return rSummary


def answer_oral(pDatabaseFile, pPosition, pSeconds, pStructure, pExample, pNow):
    """Note la réponse à la question en cours ; retourne la note et le conseil.

    Lève ValueError sans séance, pour une question déjà notée ou une note illisible.
    """

    vData = load_oral(pDatabaseFile)
    vSession = vData["current"]

    if vSession is None:
        raise ValueError("Aucune séance en cours : commencez-en une.")

    if pPosition != len(vSession["answers"]):
        raise ValueError("Cette question a déjà été notée.")

    vAnswer = grade_answer(pSeconds, vSession["duration"], pStructure, pExample)
    vSession["answers"].append(vAnswer)
    vFinished = len(vSession["answers"]) == len(vSession["questions"])

    if vFinished:
        vData["history"].append(summarize_session(vSession, pNow))
        vData["current"] = None
        logger.info("Entretien oral terminé : %d %%", vData["history"][-1]["score"])

    save_oral(pDatabaseFile, vData)

    rFeedback = {
        **vAnswer,
        "duration_label": DURATION_RATINGS[vAnswer["duration"]],
        "hint": vSession["questions"][pPosition]["hint"],
        "finished": vFinished,
    }

    return rFeedback


def stop_oral(pDatabaseFile):
    """Abandonne la séance en cours, sans la compter."""

    vData = load_oral(pDatabaseFile)
    vData["current"] = None
    save_oral(pDatabaseFile, vData)


def find_weakest(pHistory):
    """Retourne le critère le moins bien noté sur les cinq dernières séances, ou None."""

    vRecent = pHistory[-5:]

    if not vRecent:
        return None

    vAverages = {
        vId: sum(vSession["criteria"].get(vId, 0) for vSession in vRecent)
        / len(vRecent)
        for vId, _, _ in CRITERIA
    }
    vWeakest = min(vAverages, key=vAverages.get)

    rWeakest = (
        None
        if vAverages[vWeakest] >= 1.5
        else next((vLabel, vTip) for vId, vLabel, vTip in CRITERIA if vId == vWeakest)
    )

    return rWeakest


def build_oral_view(pDatabaseFile):
    """Retourne ce qu'affichent les pages : question en cours, dernière séance, progression."""

    vData = load_oral(pDatabaseFile)
    vSession = vData["current"]
    vHistory = vData["history"]

    rView = {
        "modes": MODES,
        "durations": DURATIONS,
        "criteria": CRITERIA,
        "ratings": RATINGS,
        "session": vSession,
        "position": len(vSession["answers"]) if vSession else None,
        "question": (
            vSession["questions"][len(vSession["answers"])] if vSession else None
        ),
        "previous": (
            {
                **vSession["answers"][-1],
                "duration_label": DURATION_RATINGS[vSession["answers"][-1]["duration"]],
                "hint": vSession["questions"][len(vSession["answers"]) - 1]["hint"],
            }
            if vSession and vSession["answers"]
            else None
        ),
        "last": vHistory[-1] if vHistory else None,
        "recent": [vSession["score"] for vSession in vHistory[-10:]],
        "count": len(vHistory),
        "weakest": find_weakest(vHistory),
    }

    return rView


def record_phone_session(pDatabaseFile, pSession, pFinishedAt):
    """Ajoute une séance jouée sur le téléphone ; retourne sa note.

    Les réponses sont renotées ici : seules les notes de l'utilisateur et le
    temps mesuré sont repris. Lève ValueError si la séance est illisible.
    """

    if (
        not isinstance(pSession, dict)
        or pSession.get("mode") not in MODES
        or pSession.get("duration") not in DURATIONS
        or not isinstance(pSession.get("answers"), list)
        or not 1 <= len(pSession["answers"]) <= SESSION_LENGTH
        or not all(isinstance(vAnswer, dict) for vAnswer in pSession["answers"])
    ):
        raise ValueError("séance illisible")

    vSession = {
        "mode": pSession["mode"],
        "duration": pSession["duration"],
        "answers": [
            grade_answer(
                vAnswer.get("seconds"),
                pSession["duration"],
                vAnswer.get("structure"),
                vAnswer.get("example"),
            )
            for vAnswer in pSession["answers"]
        ],
    }
    vData = load_oral(pDatabaseFile)
    vData["history"].append(summarize_session(vSession, pFinishedAt or datetime.now()))
    save_oral(pDatabaseFile, vData)

    rScore = vData["history"][-1]["score"]

    return rScore
