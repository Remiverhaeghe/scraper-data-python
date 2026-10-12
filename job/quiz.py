"""Révision technique : questions à choix multiple, progression et thèmes conseillés"""

import json
import random
import re
import unicodedata
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from config import QUIZ_DIRECTORY
from job.quiz_domains import classify_theme
from storage.job_offers import (
    count_offers_by_skill,
    get_offer_texts,
    get_offers_signature,
)
from storage.quiz_answers import (
    count_answers_by_day,
    get_answer_history,
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
    "spaced": "Répétition espacée",
    "discover": "Nouvelles questions d'abord",
    "review": "Questions ratées à revoir",
}
DEFAULT_MODE = "spaced"

# État d'un thème, signalé par une icône sur sa carte : (icône, tonalité, texte)
THEME_STATUSES = {
    "done": ("circle-check", "success", "Toutes les questions sont acquises"),
    "due": ("circle-alert", "warning", "Des questions sont à revoir aujourd'hui"),
    "progress": ("history", "primary", "Révision commencée"),
}

# Répétition espacée (méthode Leitner) : délai avant de revoir une question, en
# jours, selon sa boîte. Une bonne réponse la fait monter d'une boîte, une
# erreur la renvoie dans la première.
LEITNER_INTERVALS = (1, 3, 7, 21, 60)

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
        vMeta = vImportedThemes.get(
            vKey, {"label": vLabel, "skills": [vLabel], "domain": None}
        )
        vTheme = rThemes.setdefault(
            vKey,
            {
                "key": vKey,
                "label": vMeta["label"],
                "skills": vMeta["skills"] or [vMeta["label"]],
                "domain": vMeta["domain"],
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


# Sigle court (« GC », « SSO ») : cherché tel quel en majuscules, sinon il
# reconnaîtrait des mots sans rapport.
MIN_INSENSITIVE_LENGTH = 4

# Une compétence générique (« HTTP », « maintenance ») apparaît partout : une
# offre ne compte pour un thème que si elle en cite au moins deux.
MIN_MATCHED_SKILLS = 2

# Comptes par texte, gardés tant que les offres en base ne changent pas
TEXT_COUNTS_CACHE = {}


def build_skills_pattern(pSkills):
    """Retourne le motif qui repère les compétences, en mots entiers, ou None."""

    vParts = [
        (
            re.escape(vSkill)
            if len(vSkill) < MIN_INSENSITIVE_LENGTH
            else f"(?i:{re.escape(vSkill)})"
        )
        for vSkill in sorted(pSkills, key=len, reverse=True)
        if vSkill.strip()
    ]

    rPattern = (
        re.compile(r"(?<![\w-])(?:" + "|".join(vParts) + r")(?![\w-])")
        if vParts
        else None
    )

    return rPattern


def count_offers_by_text(pDatabaseFile, pThemes):
    """Compte, par thème, les offres dont le texte cite assez de ses compétences.

    Sert aux thèmes importés dont les compétences (« Tomcat », « logs ») ne sont
    pas reconnues à l'enrichissement. Une seule recherche par offre, pour tous
    les thèmes à la fois.
    """

    vThemeSkills = {
        vTheme["key"]: {vSkill.lower() for vSkill in vTheme["skills"] if vSkill.strip()}
        for vTheme in pThemes
    }
    vKey = (
        str(pDatabaseFile),
        get_offers_signature(pDatabaseFile),
        tuple(
            sorted(
                (vTheme, tuple(sorted(vSkills)))
                for vTheme, vSkills in vThemeSkills.items()
            )
        ),
    )

    if vKey not in TEXT_COUNTS_CACHE:
        vPattern = build_skills_pattern(
            {vSkill for vTheme in pThemes for vSkill in vTheme["skills"]}
        )
        rCounts = dict.fromkeys(vThemeSkills, 0)

        for vText in get_offer_texts(pDatabaseFile) if vPattern else []:
            vFound = {vMatch.lower() for vMatch in vPattern.findall(vText)}

            for vTheme, vSkills in vThemeSkills.items():
                if len(vFound & vSkills) >= min(MIN_MATCHED_SKILLS, len(vSkills)):
                    rCounts[vTheme] += 1

        # Un seul état gardé : la base a changé, l'ancien compte ne sert plus.
        TEXT_COUNTS_CACHE.clear()
        TEXT_COUNTS_CACHE[vKey] = rCounts

    rCounts = TEXT_COUNTS_CACHE[vKey]

    return rCounts


def count_theme_offers(pDatabaseFile, pQuiz):
    """Compte, par thème, les offres qui demandent ses compétences.

    Les compétences reconnues à l'enrichissement sont comptées directement ;
    sinon, elles sont cherchées dans le titre et la description.
    """

    vSkillCounts = count_offers_by_skill(pDatabaseFile)

    rCounts = {
        vKey: max(
            (vSkillCounts.get(vSkill, 0) for vSkill in vTheme["skills"]), default=0
        )
        for vKey, vTheme in pQuiz.items()
    }

    vMissing = [vTheme for vKey, vTheme in pQuiz.items() if not rCounts[vKey]]

    if vMissing:
        rCounts.update(count_offers_by_text(pDatabaseFile, vMissing))

    return rCounts


def get_theme_status(pCorrect, pTotal, pAnswered, pDue):
    """Retourne l'état d'un thème : done, due, progress, ou None s'il est neuf."""

    if pTotal and pCorrect == pTotal:
        rStatus = "done"
    elif pDue:
        rStatus = "due"
    elif pAnswered:
        rStatus = "progress"
    else:
        rStatus = None

    return rStatus


def build_quiz_overview(pDatabaseFile, pQuiz, pToday=None):
    """Retourne les thèmes avec leur score, leurs questions à revoir et leur intérêt.

    Un thème est conseillé quand ses compétences sont citées dans les offres en
    base ; les thèmes conseillés viennent en premier.
    """

    vAnswers = get_last_answers(pDatabaseFile)
    vSchedule = get_review_schedule(pDatabaseFile)
    vToday = pToday or date.today()
    vOfferCounts = count_theme_offers(pDatabaseFile, pQuiz)
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
        vOfferCount = vOfferCounts[vTheme["key"]]
        vDue = count_due_questions(vTheme["questions"], vSchedule, vToday)
        vDomain, vSubdomain = vTheme.get("domain") or classify_theme(
            vTheme["label"], vTheme["skills"]
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
                "due": vDue,
                "status": get_theme_status(vCorrect, len(vIds), len(vAnswered), vDue),
                "domain": vDomain,
                "subdomain": vSubdomain,
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

    # Le graphique commence au premier jour de révision : sans jours vides
    # avant lui, la barre ne se retrouve pas isolée à droite.
    vFirstDay = min(
        (vDay for vDay in vChartDays if vDay.isoformat() in vDays), default=vToday
    )

    rStatistics = {
        "acquired": sum(vTheme["correct"] for vTheme in pThemes),
        "total": sum(vTheme["total"] for vTheme in pThemes),
        "to_review": sum(vTheme["to_review"] for vTheme in pThemes),
        "answers": vAnswers,
        "rate": round(100 * vCorrect / vAnswers) if vAnswers else None,
        "streak": count_streak(vDays, vToday),
        "days": [
            (vDay, *vDays.get(vDay.isoformat(), (0, 0)))
            for vDay in vChartDays
            if vDay >= vFirstDay
        ],
    }

    return rStatistics


def build_review_schedule(pHistory):
    """Calcule la boîte et la date de prochaine révision de chaque question.

    Retourne {question: {"box": 1 à 5, "due": date}} à partir de l'historique
    des réponses, sans rien enregistrer de plus.
    """

    rSchedule = {}

    for vQuestionId, vCorrect, vAnsweredAt in pHistory:
        vBox = rSchedule.get(vQuestionId, {"box": 0})["box"]
        vBox = min(vBox + 1, len(LEITNER_INTERVALS)) if vCorrect else 1

        rSchedule[vQuestionId] = {
            "box": vBox,
            "due": datetime.fromisoformat(vAnsweredAt).date()
            + timedelta(days=LEITNER_INTERVALS[vBox - 1]),
        }

    return rSchedule


def get_review_schedule(pDatabaseFile):
    """Retourne le calendrier de révision des questions déjà répondues."""

    rSchedule = build_review_schedule(get_answer_history(pDatabaseFile))

    return rSchedule


def count_due_questions(pQuestions, pSchedule, pToday):
    """Compte les questions déjà vues dont la révision est due."""

    rCount = sum(
        1
        for vQuestion in pQuestions
        if vQuestion["id"] in pSchedule and pSchedule[vQuestion["id"]]["due"] <= pToday
    )

    return rCount


def get_next_review(pQuiz, pThemeKey, pSchedule):
    """Retourne la prochaine date de révision d'un thème, ou None."""

    rDate = min(
        (
            pSchedule[vQuestion["id"]]["due"]
            for vQuestion in pQuiz[pThemeKey]["questions"]
            if vQuestion["id"] in pSchedule
        ),
        default=None,
    )

    return rDate


def describe_no_question(pMode, pNextReview):
    """Explique pourquoi aucune question n'est proposée dans ce mode."""

    if pMode == "review":
        rText = "Aucune question ratée à revoir dans ce thème."
    elif pNextReview:
        rText = (
            "Rien à revoir aujourd'hui dans ce thème : prochaine révision le "
            f"{pNextReview:%d/%m/%Y}."
        )
    else:
        rText = "Aucune question dans ce thème."

    return rText


def pick_question(
    pQuiz,
    pThemeKey,
    pMode,
    pLastAnswers,
    pRandom=random,
    pSchedule=None,
    pToday=None,
):
    """Choisit une question du thème, choix mélangés ; None s'il n'y en a plus.

    spaced propose les questions dont la révision est due, puis les nouvelles ;
    discover d'abord les questions jamais répondues, review seulement celles
    dont la dernière réponse était fausse.
    """

    vQuestions = pQuiz[pThemeKey]["questions"]

    if pMode == "spaced":
        vSchedule = pSchedule or {}
        vToday = pToday or date.today()
        vCandidates = [
            vQuestion
            for vQuestion in vQuestions
            if vQuestion["id"] in vSchedule
            and vSchedule[vQuestion["id"]]["due"] <= vToday
        ] or [vQuestion for vQuestion in vQuestions if vQuestion["id"] not in vSchedule]
    elif pMode == "review":
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
