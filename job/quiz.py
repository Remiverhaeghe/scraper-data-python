"""Révision technique : questions à choix multiple, progression et thèmes conseillés"""

import json
import random
import re
import unicodedata
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from config import QUIZ_DIRECTORY
from storage.job_offers import count_offers_by_skill
from storage.quiz_answers import (
    count_answers_by_day,
    get_last_answers,
    save_quiz_answer,
)
from storage.quiz_questions import (
    get_imported_questions,
    get_quiz_guides,
    get_quiz_themes,
)
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

QUIZ_LEVELS = ("débutant", "intermédiaire", "confirmé", "expert")

QUIZ_MODES = {
    "discover": "Nouvelles questions d'abord",
    "review": "Questions ratées à revoir",
}
DEFAULT_MODE = "discover"

QUESTION_FIELDS = ("id", "level", "question", "choices", "answer", "explanation")
TEXT_FIELDS = ("question", "explanation")

# Identifiant court et lisible : « java-records », « sql-left-join »
QUESTION_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{2,79}")

# Questions signalées comme douteuses, retirées des tirages
FLAGGED_KEY = "quiz_flagged"


def check_question(pQuestion, pFileName):
    """Vérifie qu'une question est complète ; lève ValueError en nommant le défaut."""

    vId = pQuestion.get("id", "sans identifiant")
    vMissing = [vField for vField in QUESTION_FIELDS if vField not in pQuestion]

    if vMissing:
        raise ValueError(
            f"{pFileName}, question {vId} : {', '.join(vMissing)} manquant"
        )

    if not isinstance(pQuestion.get("code", ""), str):
        raise ValueError(f"{pFileName}, question {vId} : code attendu en texte")

    if pQuestion["level"] not in QUIZ_LEVELS:
        raise ValueError(f"{pFileName}, question {vId} : niveau inconnu")

    if not isinstance(pQuestion["id"], str) or not QUESTION_ID_PATTERN.fullmatch(
        pQuestion["id"]
    ):
        raise ValueError(
            f"{pFileName}, question {vId} : identifiant en minuscules, chiffres et "
            "tirets attendu"
        )

    if any(
        not isinstance(pQuestion[vField], str) or not pQuestion[vField].strip()
        for vField in TEXT_FIELDS
    ):
        raise ValueError(f"{pFileName}, question {vId} : texte vide")

    vChoices = pQuestion["choices"]

    if (
        not isinstance(vChoices, list)
        or not 2 <= len(vChoices) <= 5
        or any(
            not isinstance(vChoice, str) or not vChoice.strip() for vChoice in vChoices
        )
    ):
        raise ValueError(f"{pFileName}, question {vId} : 2 à 5 choix attendus")

    # bool est un int en Python : True ne doit pas passer pour la réponse 1.
    if (
        not isinstance(pQuestion["answer"], int)
        or isinstance(pQuestion["answer"], bool)
        or not 0 <= pQuestion["answer"] < len(vChoices)
    ):
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


def slugify(pText):
    """Transforme un libellé en clé : « Spring Boot » devient « spring-boot »."""

    vText = unicodedata.normalize("NFKD", str(pText)).encode("ascii", "ignore")

    rSlug = re.sub(r"[^a-z0-9]+", "-", vText.decode().lower()).strip("-")

    return rSlug


def get_flagged_questions(pDatabaseFile):
    """Retourne les identifiants des questions signalées comme douteuses."""

    vValue = get_setting_values(pDatabaseFile).get(FLAGGED_KEY)

    try:
        rFlagged = set(json.loads(vValue)) if vValue else set()

    except ValueError:
        logger.warning("Liste des questions signalées illisible : ignorée")

        rFlagged = set()

    return rFlagged


def flag_question(pDatabaseFile, pQuestionId):
    """Retire une question douteuse des tirages."""

    vFlagged = get_flagged_questions(pDatabaseFile) | {pQuestionId}

    save_setting_values(pDatabaseFile, {FLAGGED_KEY: json.dumps(sorted(vFlagged))})

    logger.info("Question de révision signalée comme douteuse : %s", pQuestionId)


def load_active_quiz(pDatabaseFile):
    """Retourne les thèmes livrés et importés, sans les questions signalées."""

    rThemes = {
        vKey: {**vTheme, "questions": list(vTheme["questions"])}
        for vKey, vTheme in load_quiz().items()
    }

    vImportedThemes = get_quiz_themes(pDatabaseFile)

    for vKey, vLabel, vQuestion in get_imported_questions(pDatabaseFile):
        # Un thème importé garde les compétences données par son fichier.
        vMeta = vImportedThemes.get(vKey, {"label": vLabel, "skills": [vLabel]})
        vTheme = rThemes.setdefault(
            vKey,
            {
                "key": vKey,
                "label": vMeta["label"],
                "skills": vMeta["skills"] or [vMeta["label"]],
                "questions": [],
            },
        )
        vTheme["questions"].append(vQuestion)

    vFlagged = get_flagged_questions(pDatabaseFile)

    for vTheme in rThemes.values():
        vTheme["questions"] = [
            vQuestion
            for vQuestion in vTheme["questions"]
            if vQuestion["id"] not in vFlagged
        ]

    return rThemes


def find_theme(pQuiz, pThemeLabel):
    """Retourne la clé et le libellé du thème nommé, existant ou nouveau."""

    vKey = slugify(pThemeLabel)

    rTheme = next(
        (
            (vThemeKey, vTheme["label"])
            for vThemeKey, vTheme in pQuiz.items()
            if vThemeKey == vKey or slugify(vTheme["label"]) == vKey
        ),
        (vKey, " ".join(str(pThemeLabel).split())),
    )

    return rTheme


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
    vGuides = {
        vGuide["theme"]: vGuide["name"]
        for vGuide in get_quiz_guides(pDatabaseFile)
        if vGuide["theme"]
    }

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
                "guide": vGuides.get(vTheme["key"]),
            }
        )

    rThemes = sorted(
        vThemes, key=lambda pTheme: (-pTheme["offer_count"], pTheme["label"])
    )

    return rThemes


# Jours affichés dans le graphique de révision
STATISTICS_DAYS = 14


def count_streak(pDays, pToday):
    """Compte les jours de révision consécutifs jusqu'à aujourd'hui.

    Une série en cours n'est pas perdue tant que la journée n'est pas finie :
    sans réponse aujourd'hui, le compte part d'hier.
    """

    vDay = pToday if pToday.isoformat() in pDays else pToday - timedelta(days=1)

    rStreak = 0

    while vDay.isoformat() in pDays:
        rStreak += 1
        vDay -= timedelta(days=1)

    return rStreak


def build_quiz_statistics(pDatabaseFile, pThemes, pNow, pDays=STATISTICS_DAYS):
    """Retourne les chiffres de la révision et l'activité des derniers jours.

    pThemes est la vue d'ensemble de build_quiz_overview.
    """

    vDays = count_answers_by_day(pDatabaseFile)
    vAnswers = sum(vCount for vCount, _ in vDays.values())
    vCorrect = sum(vCorrectCount for _, vCorrectCount in vDays.values())
    vToday = pNow.date()
    vChartDays = [vToday - timedelta(days=vOffset) for vOffset in range(pDays)][::-1]

    rStatistics = {
        "acquired": sum(vTheme["correct"] for vTheme in pThemes),
        "total": sum(vTheme["total"] for vTheme in pThemes),
        "to_review": sum(vTheme["to_review"] for vTheme in pThemes),
        "answers": vAnswers,
        "rate": round(100 * vCorrect / vAnswers) if vAnswers else None,
        "streak": count_streak(vDays, vToday),
        "days": [(vDay, *vDays.get(vDay.isoformat(), (0, 0))) for vDay in vChartDays],
    }

    return rStatistics


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
