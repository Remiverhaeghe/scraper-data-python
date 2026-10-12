"""Révision technique : questions à choix multiple, progression et thèmes conseillés"""

import json
import random
import re
import unicodedata
import zipfile
from datetime import timedelta
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from config import QUIZ_DIRECTORY
from storage.job_offers import count_offers_by_skill
from storage.quiz_answers import (
    count_answers_by_day,
    get_last_answers,
    save_quiz_answer,
)
from storage.quiz_questions import get_imported_questions, save_imported_questions
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

QUIZ_LEVELS = ("débutant", "confirmé")

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

# Import : au-delà, la saisie est une erreur de copier-coller.
MAX_IMPORT_LENGTH = 2_000_000
MAX_IMPORT_QUESTIONS = 200

# Nombre de questions demandées à ChatGPT en une fois : au-delà, la réponse est
# souvent coupée.
GENERATION_COUNTS = (10, 20, 30, 50)

# Archive .zip de fichiers JSON, par exemple produite par ChatGPT
IMPORT_EXTENSIONS = (".json", ".txt", ".zip")
MAX_ZIP_FILES = 100
MAX_ZIP_BYTES = 20 * 1024 * 1024

# Identifiants déjà pris envoyés à ChatGPT, pour éviter les doublons
MAX_PROMPT_IDS = 300


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

    for vKey, vLabel, vQuestion in get_imported_questions(pDatabaseFile):
        vTheme = rThemes.setdefault(
            vKey, {"key": vKey, "label": vLabel, "skills": [vLabel], "questions": []}
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


def parse_questions_text(pText):
    """Lit le thème éventuel et les questions d'une réponse ChatGPT ou d'un JSON.

    Le JSON peut être entouré de texte ou d'un bloc de code : seule la partie
    entre la première accolade ou le premier crochet et le dernier est lue.
    Retourne (thème indiqué dans le JSON ou None, questions).
    """

    vText = str(pText or "")

    if len(vText) > MAX_IMPORT_LENGTH:
        raise ValueError("Texte trop long pour un import.")

    vStarts = [vIndex for vIndex in (vText.find("{"), vText.find("[")) if vIndex >= 0]
    vEnd = max(vText.rfind("}"), vText.rfind("]"))

    if not vStarts or vEnd < min(vStarts):
        raise ValueError("Aucune question au format JSON n'a été trouvée.")

    try:
        vData = json.loads(vText[min(vStarts) : vEnd + 1])

    except ValueError as vException:
        raise ValueError(
            "JSON illisible : la réponse est peut-être coupée, demandez moins de "
            "questions à la fois."
        ) from vException

    vQuestions = vData.get("questions") if isinstance(vData, dict) else vData
    vTheme = vData.get("theme") if isinstance(vData, dict) else None

    if not isinstance(vQuestions, list) or not vQuestions:
        raise ValueError("Aucune question au format JSON n'a été trouvée.")

    if len(vQuestions) > MAX_IMPORT_QUESTIONS:
        raise ValueError(f"{MAX_IMPORT_QUESTIONS} questions au plus par import.")

    rParsed = (
        vTheme if isinstance(vTheme, str) and vTheme.strip() else None,
        vQuestions,
    )

    return rParsed


def import_questions(pDatabaseFile, pThemeLabel, pText, pNow):
    """Vérifie puis enregistre des questions ; retourne le bilan de l'import.

    Le thème indiqué dans le JSON l'emporte sur pThemeLabel. Une question
    incorrecte ou déjà présente est écartée avec la raison, les autres sont
    importées. Lève ValueError si rien n'est lisible.
    """

    vJsonTheme, vQuestions = parse_questions_text(pText)
    vRequestedTheme = vJsonTheme or str(pThemeLabel or "").strip()

    if not vRequestedTheme:
        raise ValueError("Indiquez le thème des questions.")

    vQuiz = load_active_quiz(pDatabaseFile)
    vThemeKey, vThemeLabel = find_theme(vQuiz, vRequestedTheme)

    # Les questions signalées gardent leur identifiant : il reste pris.
    vIds = {
        vQuestion["id"]
        for vTheme in load_quiz().values()
        for vQuestion in vTheme["questions"]
    }
    vIds |= {
        vQuestion["id"] for _, _, vQuestion in get_imported_questions(pDatabaseFile)
    }
    vTexts = {
        " ".join(vQuestion["question"].lower().split()) + vQuestion.get("code", "")
        for vQuestion in vQuiz.get(vThemeKey, {}).get("questions", [])
    }

    vAdded = []
    rRejected = []

    for vIndex, vQuestion in enumerate(vQuestions, start=1):
        try:
            if not isinstance(vQuestion, dict):
                raise ValueError(f"question {vIndex} : format inattendu")

            check_question(vQuestion, f"question {vIndex}")

            vText = " ".join(vQuestion["question"].lower().split()) + vQuestion.get(
                "code", ""
            )

            if vQuestion["id"] in vIds:
                raise ValueError(
                    f"question {vQuestion['id']} : identifiant déjà utilisé"
                )

            if vText in vTexts:
                raise ValueError(f"question {vQuestion['id']} : déjà présente")

        except ValueError as vException:
            rRejected.append(str(vException))

        else:
            # Seuls les champs connus sont gardés : rien d'autre n'est affiché.
            vAdded.append(
                {
                    vField: vQuestion[vField]
                    for vField in (*QUESTION_FIELDS, "code")
                    if vField in vQuestion
                }
            )
            vIds.add(vQuestion["id"])
            vTexts.add(vText)

    if vAdded:
        save_imported_questions(pDatabaseFile, vThemeKey, vThemeLabel, vAdded, pNow)

    if rRejected:
        logger.warning("Import de révision : %s question(s) écartée(s)", len(rRejected))

    rReport = {
        "themes": [vThemeLabel] if vAdded else [],
        "added": len(vAdded),
        "rejected": rRejected,
    }

    return rReport


def import_questions_file(pDatabaseFile, pThemeLabel, pFileName, pContent, pNow):
    """Importe un fichier .json ou .txt, ou chaque fichier JSON d'une archive .zip."""

    vExtension = Path(str(pFileName or "")).suffix.lower()

    if vExtension not in IMPORT_EXTENSIONS:
        raise ValueError(
            "Fichier refusé : formats acceptés " + ", ".join(IMPORT_EXTENSIONS)
        )

    if vExtension != ".zip":
        rReport = import_questions(
            pDatabaseFile, pThemeLabel, pContent.decode("utf-8", errors="replace"), pNow
        )

        return rReport

    try:
        vArchive = zipfile.ZipFile(BytesIO(pContent))

    except zipfile.BadZipFile as vException:
        raise ValueError("Archive .zip illisible.") from vException

    with vArchive:
        vEntries = [
            vEntry
            for vEntry in vArchive.infolist()
            if vEntry.filename.lower().endswith(".json") and not vEntry.is_dir()
        ]

        if not vEntries:
            raise ValueError("L'archive ne contient aucun fichier .json.")

        # Tailles annoncées vérifiées avant lecture : une archive piégée est refusée.
        if len(vEntries) > MAX_ZIP_FILES or (
            sum(vEntry.file_size for vEntry in vEntries) > MAX_ZIP_BYTES
        ):
            raise ValueError(
                f"Archive trop volumineuse : {MAX_ZIP_FILES} fichiers et "
                f"{MAX_ZIP_BYTES // (1024 * 1024)} Mo au plus."
            )

        rReport = {"themes": [], "added": 0, "rejected": []}

        for vEntry in vEntries:
            vName = Path(vEntry.filename).name

            try:
                vReport = import_questions(
                    pDatabaseFile,
                    pThemeLabel or Path(vName).stem,
                    vArchive.read(vEntry).decode("utf-8", errors="replace"),
                    pNow,
                )

            except (ValueError, zipfile.BadZipFile) as vException:
                rReport["rejected"].append(f"{vName} : {vException}")

            else:
                rReport["added"] += vReport["added"]
                rReport["themes"] += [
                    vTheme
                    for vTheme in vReport["themes"]
                    if vTheme not in rReport["themes"]
                ]
                rReport["rejected"] += [
                    f"{vName}, {vReason}" for vReason in vReport["rejected"]
                ]

    return rReport


def describe_quiz_import(pReport):
    """Résume un import en une phrase, avec les premières raisons de rejet."""

    rText = f"{pReport['added']} question(s) ajoutée(s)" + (
        f" : {', '.join(pReport['themes'])}." if pReport["themes"] else "."
    )

    if pReport["rejected"]:
        rText += (
            f" {len(pReport['rejected'])} écartée(s) : "
            + " ; ".join(pReport["rejected"][:5])
            + (" ; …" if len(pReport["rejected"]) > 5 else "")
        )

    return rText


def build_generation_prompt(pQuiz, pThemeLabel, pLevel, pCount):
    """Retourne la demande ChatGPT qui produit des questions au format attendu."""

    vThemeKey, vThemeLabel = find_theme(pQuiz, pThemeLabel)
    vIds = [
        vQuestion["id"] for vQuestion in pQuiz.get(vThemeKey, {}).get("questions", [])
    ]
    vLevel = pLevel if pLevel in QUIZ_LEVELS else QUIZ_LEVELS[0]

    rPrompt = (
        f"Écris {pCount} questions à choix multiple sur « {vThemeLabel} », niveau "
        f"{vLevel}, pour préparer un entretien technique de développeur.\n"
        "Règles :\n"
        "1. Une seule bonne réponse par question, vérifiée ; 4 choix plausibles.\n"
        "2. Place la bonne réponse à des positions variées.\n"
        "3. Mélange « que fait ce code ? », notions, nouveautés de version et "
        "bonnes pratiques.\n"
        "4. Une explication de 1 à 3 phrases qui justifie la réponse.\n"
        f"5. Identifiants en minuscules et tirets, commençant par « {vThemeKey}- », "
        "jamais parmi ceux déjà pris ci-dessous.\n"
        "6. Tout en français, sauf le code.\n"
        "Réponds uniquement par ce JSON, sans texte autour :\n"
        '{"questions": [{"id": "' + vThemeKey + '-exemple", "level": "' + vLevel + '", '
        '"question": "Que fait ce code ?", "code": "facultatif", '
        '"choices": ["…", "…", "…", "…"], "answer": 0, "explanation": "…"}]}\n\n'
        "Identifiants déjà pris : " + (", ".join(vIds[-MAX_PROMPT_IDS:]) or "aucun")
    )

    return rPrompt


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
