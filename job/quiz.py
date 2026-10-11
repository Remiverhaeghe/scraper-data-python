"""Révision technique : questions à choix multiple, progression et thèmes conseillés"""

import json
import random
from functools import lru_cache
from pathlib import Path

from config import QUIZ_DIRECTORY
from storage.job_offers import count_offers_by_skill
from storage.quiz_answers import get_last_answers, save_quiz_answer
from utils.logger import get_logger

logger = get_logger(__name__)

QUIZ_LEVELS = ("débutant", "confirmé")

QUIZ_MODES = {
    "discover": "Nouvelles questions d'abord",
    "review": "Questions ratées à revoir",
}
DEFAULT_MODE = "discover"

QUESTION_FIELDS = ("id", "level", "question", "choices", "answer", "explanation")


def check_question(pQuestion, pFileName):
    """Vérifie qu'une question est complète ; lève ValueError en nommant le défaut."""

    vId = pQuestion.get("id", "sans identifiant")
    vMissing = [vField for vField in QUESTION_FIELDS if vField not in pQuestion]

    if vMissing:
        raise ValueError(
            f"{pFileName}, question {vId} : {', '.join(vMissing)} manquant"
        )

    if pQuestion["level"] not in QUIZ_LEVELS:
        raise ValueError(f"{pFileName}, question {vId} : niveau inconnu")

    if not 2 <= len(pQuestion["choices"]) <= 5:
        raise ValueError(f"{pFileName}, question {vId} : 2 à 5 choix attendus")

    if not 0 <= pQuestion["answer"] < len(pQuestion["choices"]):
        raise ValueError(f"{pFileName}, question {vId} : réponse hors des choix")


@lru_cache
def load_quiz(pDirectory=QUIZ_DIRECTORY):
    """Charge les thèmes de révision, un fichier JSON par thème, triés par nom.

    Le contenu est versionné avec le code : une question mal formée lève
    ValueError dès le chargement, et les tests le vérifient.
    """

    rThemes = {}
    vIds = set()

    for vFile in sorted(Path(pDirectory).glob("*.json")):
        vData = json.loads(vFile.read_text(encoding="utf-8"))

        for vQuestion in vData["questions"]:
            check_question(vQuestion, vFile.name)

            if vQuestion["id"] in vIds:
                raise ValueError(
                    f"{vFile.name} : identifiant {vQuestion['id']} en double"
                )

            vIds.add(vQuestion["id"])

        rThemes[vFile.stem] = {
            "key": vFile.stem,
            "label": vData["theme"],
            "skills": vData.get("skills", []),
            "questions": vData["questions"],
        }

    logger.info("Révision : %s thème(s), %s question(s)", len(rThemes), len(vIds))

    return rThemes


def find_question(pQuiz, pQuestionId):
    """Retourne une question et la clé de son thème, ou (None, None)."""

    rFound = next(
        (
            (vQuestion, vKey)
            for vKey, vTheme in pQuiz.items()
            for vQuestion in vTheme["questions"]
            if vQuestion["id"] == pQuestionId
        ),
        (None, None),
    )

    return rFound


def build_quiz_overview(pDatabaseFile, pQuiz):
    """Retourne les thèmes avec leur score, leurs questions à revoir et leur intérêt.

    Un thème est conseillé quand ses compétences sont citées dans les offres en
    base ; les thèmes conseillés viennent en premier.
    """

    vAnswers = get_last_answers(pDatabaseFile)
    vSkillCounts = count_offers_by_skill(pDatabaseFile)

    vThemes = []

    for vTheme in pQuiz.values():
        vIds = [vQuestion["id"] for vQuestion in vTheme["questions"]]
        vAnswered = [vId for vId in vIds if vId in vAnswers]
        vCorrect = sum(vAnswers[vId] for vId in vAnswered)
        vOfferCount = max(
            (vSkillCounts.get(vSkill, 0) for vSkill in vTheme["skills"]), default=0
        )

        vThemes.append(
            {
                "key": vTheme["key"],
                "label": vTheme["label"],
                "total": len(vIds),
                "answered": len(vAnswered),
                "correct": vCorrect,
                "to_review": len(vAnswered) - vCorrect,
                "score": round(100 * vCorrect / len(vIds)) if vIds else 0,
                "offer_count": vOfferCount,
            }
        )

    rThemes = sorted(
        vThemes, key=lambda pTheme: (-pTheme["offer_count"], pTheme["label"])
    )

    return rThemes


def pick_question(pQuiz, pThemeKey, pMode, pLastAnswers, pRandom=random):
    """Choisit une question du thème, choix mélangés ; None s'il n'y en a plus.

    discover propose d'abord les questions jamais répondues, review seulement
    celles dont la dernière réponse était fausse.
    """

    vQuestions = pQuiz[pThemeKey]["questions"]

    if pMode == "review":
        vCandidates = [
            vQuestion
            for vQuestion in vQuestions
            if pLastAnswers.get(vQuestion["id"]) is False
        ]
    else:
        vCandidates = [
            vQuestion for vQuestion in vQuestions if vQuestion["id"] not in pLastAnswers
        ] or vQuestions

    rQuestion = None

    if vCandidates:
        # Tirage pour varier l'ordre des questions, sans enjeu de sécurité.
        vQuestion = pRandom.choice(vCandidates)  # nosec B311

        # La bonne réponse ne doit pas se deviner à sa place dans la liste : les
        # choix sont mélangés, chacun gardant son indice d'origine.
        vChoices = list(enumerate(vQuestion["choices"]))
        pRandom.shuffle(vChoices)

        rQuestion = {**vQuestion, "theme_key": pThemeKey, "shuffled": vChoices}

    return rQuestion


def answer_question(pDatabaseFile, pQuiz, pQuestionId, pChoice, pNow):
    """Corrige et enregistre une réponse ; retourne la correction à afficher.

    Lève ValueError pour une question inconnue ou un choix hors liste.
    """

    vQuestion, vThemeKey = find_question(pQuiz, pQuestionId)

    if vQuestion is None or not 0 <= pChoice < len(vQuestion["choices"]):
        raise ValueError("Question ou réponse inconnue.")

    vCorrect = pChoice == vQuestion["answer"]

    save_quiz_answer(pDatabaseFile, pQuestionId, vThemeKey, vCorrect, pNow)

    rResult = {
        "question": vQuestion,
        "theme_key": vThemeKey,
        "correct": vCorrect,
        "chosen": vQuestion["choices"][pChoice],
        "answer": vQuestion["choices"][vQuestion["answer"]],
        "explanation": vQuestion["explanation"],
    }

    return rResult
