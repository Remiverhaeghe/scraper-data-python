"""Synchronisation avec l'application mobile de révision

Le téléphone télécharge tout ce qu'il faut pour réviser hors ligne : questions
avec leur réponse et leur explication, schémas, guides et progression. Il
corrige lui-même, puis renvoie ses réponses au retour du réseau. Le serveur
recalcule alors chaque correction : il ne se fie pas au téléphone.
"""

import hashlib
import io
import json
import re
from datetime import datetime, timedelta

import segno

from job.access_tokens import check_access_token, get_access_token, renew_access_token
from job.quiz import (
    LEITNER_INTERVALS,
    QUIZ_LEVELS,
    build_quiz_overview,
    build_quiz_statistics,
    find_question,
    get_review_schedule,
    load_active_quiz,
)
from job.quiz_domains import DOMAIN_ICONS
from job.quiz_types import (
    DEFAULT_TYPE,
    MAX_TEXT_ANSWER_LENGTH,
    get_type,
    grade_answer,
)
from storage.quiz_answers import get_last_answers, save_synced_answers
from storage.quiz_questions import get_quiz_assets, get_quiz_guide, get_quiz_guides
from utils.logger import get_logger

logger = get_logger(__name__)

# Nom du réglage qui garde le jeton ; ce n'est pas le jeton lui-même.
MOBILE_TOKEN_KEY = "mobile_api_token"  # nosec B105

# Version du format échangé : le téléphone refuse un format qu'il ne connaît pas.
API_VERSION = 1

# Préfixe des adresses de l'API, à la suite de l'adresse du tableau de bord
API_PREFIX = f"/api/v{API_VERSION}"

# Un envoi plus gros est une erreur : le téléphone envoie par lots.
MAX_SYNC_ANSWERS = 500

# Identifiant de réponse choisi par le téléphone, par exemple un UUID
CLIENT_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,64}")

# Types interactifs envoyés au téléphone, à part des QCM : une application qui ne
# les connaît pas encore ignore simplement la liste qui les contient.
MOBILE_INTERACTIVE_TYPES = ("numerique", "ordre", "association")

# Une réponse datée de plus loin est refusée : horloge du téléphone déréglée.
MAX_CLOCK_DRIFT = timedelta(days=1)
MAX_ANSWER_AGE = timedelta(days=366)


def get_mobile_token(pDatabaseFile):
    """Retourne le jeton de l'application mobile, ou None s'il n'a pas été créé."""

    rToken = get_access_token(pDatabaseFile, MOBILE_TOKEN_KEY)

    return rToken


def renew_mobile_token(pDatabaseFile):
    """Crée un nouveau jeton ; le téléphone devra utiliser le nouveau."""

    rToken = renew_access_token(pDatabaseFile, MOBILE_TOKEN_KEY)

    # Le jeton lui-même n'est jamais journalisé : il donne accès aux révisions.
    logger.info("Nouveau jeton de l'application mobile créé")

    return rToken


def build_connection_qr(pAddress, pToken):
    """Retourne le QR code de connexion du téléphone : adresse de l'API et jeton.

    Le contenu est un petit JSON que l'application lit au scan ; le QR code ne
    s'affiche qu'à la demande, puisqu'il donne accès aux révisions.
    """

    vPayload = json.dumps({"address": pAddress, "token": pToken}, separators=(",", ":"))

    rQrCode = segno.make(vPayload, error="m")

    return rQrCode


def build_connection_svg(pAddress, pToken):
    """Retourne le QR code de connexion en SVG, pour la page web."""

    rSvg = build_connection_qr(pAddress, pToken).svg_inline(
        scale=5, dark="#0f172a", light="#ffffff"
    )

    return rSvg


def build_connection_png(pAddress, pToken):
    """Retourne le QR code de connexion en PNG, pour l'application de bureau."""

    vBuffer = io.BytesIO()
    build_connection_qr(pAddress, pToken).save(
        vBuffer, kind="png", scale=6, dark="#0f172a", light="#ffffff"
    )

    rPng = vBuffer.getvalue()

    return rPng


def check_mobile_token(pDatabaseFile, pToken):
    """Indique si le jeton reçu est celui de l'application mobile."""

    rValid = check_access_token(pDatabaseFile, MOBILE_TOKEN_KEY, pToken)

    return rValid


def build_quiz_package(pDatabaseFile, pNow):
    """Retourne tout le contenu de révision, pour un usage hors ligne.

    La version change dès que le contenu change : le téléphone ne télécharge
    à nouveau que si elle diffère de la sienne.
    """

    vQuiz = load_active_quiz(pDatabaseFile)
    vOverview = {
        vTheme["key"]: vTheme for vTheme in build_quiz_overview(pDatabaseFile, vQuiz)
    }

    vContent = {
        "themes": [
            {
                "key": vKey,
                "label": vTheme["label"],
                "domain": vOverview[vKey]["domain"],
                "subdomain": vOverview[vKey]["subdomain"],
                "skills": vTheme["skills"],
                "guide": vOverview[vKey]["guide"],
            }
            for vKey, vTheme in vQuiz.items()
        ],
        "questions": [
            {**vQuestion, "theme": vKey}
            for vKey, vTheme in vQuiz.items()
            for vQuestion in vTheme["questions"]
            if get_type(vQuestion) == DEFAULT_TYPE
        ],
        # Éléments dans l'ordre correct : le téléphone les mélange à l'affichage.
        "interactive_questions": [
            {**vQuestion, "theme": vKey, "type": get_type(vQuestion)}
            for vKey, vTheme in vQuiz.items()
            for vQuestion in vTheme["questions"]
            if get_type(vQuestion) in MOBILE_INTERACTIVE_TYPES
        ],
        "interactive_types": list(MOBILE_INTERACTIVE_TYPES),
        "assets": get_quiz_assets(pDatabaseFile),
        "guides": [
            get_quiz_guide(pDatabaseFile, vGuide["name"])
            for vGuide in get_quiz_guides(pDatabaseFile)
        ],
        "levels": list(QUIZ_LEVELS),
        "leitner_intervals": list(LEITNER_INTERVALS),
        "icons": DOMAIN_ICONS,
    }

    vVersion = hashlib.sha256(
        json.dumps(vContent, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    rPackage = {
        "api_version": API_VERSION,
        "version": vVersion,
        "generated_at": pNow.isoformat(timespec="seconds"),
        **vContent,
    }

    return rPackage


def build_progress(pDatabaseFile, pNow):
    """Retourne la progression : état de chaque question et chiffres d'ensemble.

    Le téléphone s'en sert pour la répétition espacée hors ligne.
    """

    vQuiz = load_active_quiz(pDatabaseFile)
    vLastAnswers = get_last_answers(pDatabaseFile)
    vSchedule = get_review_schedule(pDatabaseFile)
    vStatistics = build_quiz_statistics(
        pDatabaseFile, build_quiz_overview(pDatabaseFile, vQuiz), pNow
    )

    rProgress = {
        "api_version": API_VERSION,
        "generated_at": pNow.isoformat(timespec="seconds"),
        "questions": {
            vQuestionId: {
                "last_correct": vLastAnswers.get(vQuestionId),
                "box": vState["box"],
                "due": vState["due"].isoformat(),
            }
            for vQuestionId, vState in vSchedule.items()
        },
        "statistics": {
            "acquired": vStatistics["acquired"],
            "total": vStatistics["total"],
            "answers": vStatistics["answers"],
            "rate": vStatistics["rate"],
            "streak": vStatistics["streak"],
            # Activité des derniers jours, pour le graphique du téléphone ; un
            # ancien téléphone ignore ce champ.
            "days": [
                {"date": vDay.isoformat(), "answers": vCount, "correct": vCorrect}
                for vDay, vCount, vCorrect in vStatistics["days"]
            ],
        },
    }

    return rProgress


def grade_synced_response(pQuestion, pResponse, pClientId):
    """Corrige la réponse du téléphone à une question interactive ; retourne si elle est juste."""

    # Calcul : texte court ou nombre ; ordre et association : liste d'indices.
    vReadable = (
        isinstance(pResponse, (str, int, float))
        and not isinstance(pResponse, bool)
        and len(str(pResponse)) <= MAX_TEXT_ANSWER_LENGTH
        if get_type(pQuestion) == "numerique"
        else isinstance(pResponse, list)
    )

    if not vReadable:
        raise ValueError(f"{pClientId} : réponse illisible")

    try:
        rCorrect = grade_answer(pQuestion, pResponse)[0]

    except ValueError as vException:
        raise ValueError(f"{pClientId} : réponse illisible") from vException

    return rCorrect


def check_synced_answer(pQuiz, pAnswer, pNow):
    """Vérifie une réponse du téléphone ; retourne la ligne à enregistrer.

    Lève ValueError en nommant le défaut : identifiant, question, choix ou date.
    """

    if not isinstance(pAnswer, dict):
        raise ValueError("format inattendu")

    vClientId = pAnswer.get("id")

    if not isinstance(vClientId, str) or not CLIENT_ID_PATTERN.fullmatch(vClientId):
        raise ValueError("identifiant de réponse invalide")

    vQuestion, vThemeKey = find_question(pQuiz, pAnswer.get("question_id"))

    vType = None if vQuestion is None else get_type(vQuestion)

    if vType not in (DEFAULT_TYPE, *MOBILE_INTERACTIVE_TYPES):
        raise ValueError(f"{vClientId} : question inconnue")

    if vType == DEFAULT_TYPE:
        vChoice = pAnswer.get("choice")

        if (
            not isinstance(vChoice, int)
            or isinstance(vChoice, bool)
            or not 0 <= vChoice < len(vQuestion["choices"])
        ):
            raise ValueError(f"{vClientId} : choix hors des réponses proposées")

        vCorrect = vChoice == vQuestion["answer"]

    else:
        vCorrect = grade_synced_response(vQuestion, pAnswer.get("response"), vClientId)

    try:
        vAnsweredAt = datetime.fromisoformat(str(pAnswer.get("answered_at")))

    except ValueError as vException:
        raise ValueError(f"{vClientId} : date de réponse illisible") from vException

    # Les dates sont comparées sans fuseau, comme celles des réponses du PC.
    vAnsweredAt = vAnsweredAt.replace(tzinfo=None)

    if not pNow - MAX_ANSWER_AGE <= vAnsweredAt <= pNow + MAX_CLOCK_DRIFT:
        raise ValueError(f"{vClientId} : date de réponse hors limites")

    rRow = (
        vClientId,
        vQuestion["id"],
        vThemeKey,
        vCorrect,
        vAnsweredAt.isoformat(timespec="seconds"),
    )

    return rRow


def sync_answers(pDatabaseFile, pAnswers, pNow):
    """Enregistre les réponses faites hors ligne ; retourne le bilan de l'envoi.

    Une réponse déjà reçue (même identifiant) est comptée comme doublon ; une
    réponse invalide est refusée avec sa raison, les autres sont gardées.
    """

    if not isinstance(pAnswers, list):
        raise ValueError("Liste de réponses attendue.")

    if len(pAnswers) > MAX_SYNC_ANSWERS:
        raise ValueError(f"{MAX_SYNC_ANSWERS} réponses au plus par envoi.")

    vQuiz = load_active_quiz(pDatabaseFile)
    vRows = []
    vRejected = []

    for vAnswer in pAnswers:
        try:
            vRows.append(check_synced_answer(vQuiz, vAnswer, pNow))

        except ValueError as vException:
            vRejected.append(str(vException))

    vAdded = save_synced_answers(pDatabaseFile, vRows) if vRows else 0

    rReport = {
        "received": len(pAnswers),
        "added": vAdded,
        "duplicates": len(vRows) - vAdded,
        "rejected": vRejected,
    }

    logger.info(
        "Réponses du téléphone : %s reçue(s), %s ajoutée(s), %s doublon(s), "
        "%s refusée(s)",
        rReport["received"],
        rReport["added"],
        rReport["duplicates"],
        len(vRejected),
    )

    return rReport
