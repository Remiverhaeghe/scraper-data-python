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

from config import WEB_SCHEME, WEB_TLS_CERTFILE
from job.access_tokens import check_access_token, get_access_token, renew_access_token
from job.interview_revision import find_offer_themes
from job.presentation import STATUS_LABELS
from job.quiz import (
    LEITNER_INTERVALS,
    QUIZ_LEVELS,
    build_quiz_overview,
    build_quiz_statistics,
    find_question,
    flag_question,
    get_review_schedule,
    load_active_quiz,
)
from job.quiz_domains import DOMAIN_ICONS
from job.quiz_exam import merge_exam_results
from job.quiz_types import (
    DEFAULT_TYPE,
    MAX_TEXT_ANSWER_LENGTH,
    get_type,
    grade_answer,
)
from job.weekly_digest import get_new_offers
from storage.job_applications import get_applications_with_offers, save_application
from storage.job_offers import get_offer
from storage.quiz_answers import get_last_answers, save_synced_answers
from storage.quiz_questions import get_quiz_assets, get_quiz_guide, get_quiz_guides
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger
from utils.tls import read_fingerprint

logger = get_logger(__name__)

# Nom du réglage qui garde le jeton ; ce n'est pas le jeton lui-même.
MOBILE_TOKEN_KEY = "mobile_api_token"  # nosec B105

# Heure de la dernière liste d'offres envoyée : la synchronisation est vivante.
LAST_SYNC_KEY = "mobile_last_sync"

# Version du format échangé : le téléphone refuse un format qu'il ne connaît pas.
API_VERSION = 1

# Préfixe des adresses de l'API, à la suite de l'adresse du tableau de bord
API_PREFIX = f"/api/v{API_VERSION}"

# Un envoi plus gros est une erreur : le téléphone envoie par lots.
MAX_SYNC_ANSWERS = 500

# Examens blancs et signalements reçus au plus par envoi
MAX_SYNC_EXAMS = 100
MAX_SYNC_FLAGS = 200

# Nouvelles offres envoyées au téléphone : les mieux notées de la semaine
MAX_PHONE_OFFERS = 30

# Statuts que le téléphone peut donner à une offre ; le reste du suivi (entretien,
# relances, notes) se fait sur le PC.
PHONE_STATUSES = ("INTERESTED", "APPLIED", "IGNORED")
MAX_SYNC_STATUSES = 200

# Candidatures envoyées au téléphone pour réviser leurs thèmes : les plus récentes
REVISION_STATUSES = ("INTERVIEW", "APPLIED")
MAX_REVISION_APPLICATIONS = 10

# Identifiant de réponse choisi par le téléphone, par exemple un UUID
CLIENT_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,64}")

# Types interactifs envoyés au téléphone, à part des QCM : une application qui ne
# les connaît pas encore ignore simplement la liste qui les contient.
MOBILE_INTERACTIVE_TYPES = ("numerique", "ordre", "association", "revue")

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


def build_connection_qr(pAddress, pToken, pFingerprint=None):
    """Retourne le QR code de connexion du téléphone : adresse de l'API et jeton.

    Le contenu est un petit JSON que l'application lit au scan ; le QR code ne
    s'affiche qu'à la demande, puisqu'il donne accès aux révisions.
    """

    vData = {"address": pAddress, "token": pToken}

    # En HTTPS, le téléphone n'accepte que le certificat de cette empreinte.
    if pFingerprint:
        vData["certificate_sha256"] = pFingerprint

    vPayload = json.dumps(vData, separators=(",", ":"))

    rQrCode = segno.make(vPayload, error="m")

    return rQrCode


def build_connection_svg(pAddress, pToken, pFingerprint=None):
    """Retourne le QR code de connexion en SVG, pour la page web."""

    rSvg = build_connection_qr(pAddress, pToken, pFingerprint).svg_inline(
        scale=5, dark="#0f172a", light="#ffffff"
    )

    return rSvg


def build_connection_png(pAddress, pToken, pFingerprint=None):
    """Retourne le QR code de connexion en PNG, pour l'application de bureau."""

    vBuffer = io.BytesIO()
    build_connection_qr(pAddress, pToken, pFingerprint).save(
        vBuffer, kind="png", scale=6, dark="#0f172a", light="#ffffff"
    )

    rPng = vBuffer.getvalue()

    return rPng


def get_certificate_fingerprint():
    """Retourne l'empreinte du certificat HTTPS du tableau de bord, ou None en HTTP."""

    rFingerprint = read_fingerprint(WEB_TLS_CERTFILE) if WEB_SCHEME == "https" else None

    return rFingerprint


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


def build_application_themes(pDatabaseFile, pQuiz):
    """Retourne les candidatures en cours et les thèmes à revoir pour chacune."""

    vApplications = get_applications_with_offers(pDatabaseFile, REVISION_STATUSES)

    rApplications = [
        {
            "title": vApplication.get("title"),
            "company": vApplication.get("company"),
            "status": STATUS_LABELS.get(vApplication.get("status")),
            "themes": list(find_offer_themes(pQuiz, vApplication)),
        }
        for vApplication in vApplications[:MAX_REVISION_APPLICATIONS]
    ]

    # Une candidature sans thème correspondant n'aide pas à réviser.
    rApplications = [vItem for vItem in rApplications if vItem["themes"]]

    return rApplications


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
        "applications": build_application_themes(pDatabaseFile, vQuiz),
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

    # Calcul : texte court ou nombre ; ordre, association, revue : liste d'indices.
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


def check_synced_exam(pExam):
    """Retourne la note d'examen reçue, au format de l'historique, ou lève ValueError."""

    try:
        vCorrect = int(pExam["correct"])
        vCount = int(pExam["count"])
        vSeconds = int(pExam.get("seconds") or 0)
        vFinishedAt = datetime.fromisoformat(str(pExam["finished_at"]))
    except (KeyError, TypeError, ValueError) as vException:
        raise ValueError("Examen blanc illisible.") from vException

    if not 0 <= vCorrect <= vCount or vCount == 0 or vSeconds < 0:
        raise ValueError("Examen blanc incohérent.")

    rResult = {
        "title": str(pExam.get("title") or "Examen blanc")[:120],
        "offer": None,
        "finished_at": vFinishedAt.isoformat(timespec="seconds"),
        "correct": vCorrect,
        "count": vCount,
        "score": round(100 * vCorrect / vCount),
        "seconds": vSeconds,
        "device": "téléphone",
    }

    return rResult


def sync_exam_results(pDatabaseFile, pExams):
    """Ajoute à l'historique du PC les examens blancs passés sur le téléphone."""

    if not isinstance(pExams, list):
        raise ValueError("Liste d'examens attendue.")

    if len(pExams) > MAX_SYNC_EXAMS:
        raise ValueError(f"{MAX_SYNC_EXAMS} examens au plus par envoi.")

    vResults = [check_synced_exam(vExam) for vExam in pExams]
    vAdded = merge_exam_results(pDatabaseFile, vResults)

    logger.info(
        "Examens blancs du téléphone : %s reçu(s), %s ajouté(s)", len(vResults), vAdded
    )

    rReport = {"received": len(vResults), "added": vAdded}

    return rReport


def sync_flags(pDatabaseFile, pQuestionIds):
    """Retire des tirages les questions signalées depuis le téléphone."""

    if not isinstance(pQuestionIds, list) or len(pQuestionIds) > MAX_SYNC_FLAGS:
        raise ValueError(f"Liste de {MAX_SYNC_FLAGS} questions au plus attendue.")

    vQuiz = load_active_quiz(pDatabaseFile)
    vFlagged = 0

    for vQuestionId in {str(vId) for vId in pQuestionIds}:
        # Une question déjà retirée, ou inconnue, est simplement ignorée.
        if find_question(vQuiz, vQuestionId)[0] is not None:
            flag_question(pDatabaseFile, vQuestionId)
            vFlagged += 1

    rReport = {"received": len(pQuestionIds), "flagged": vFlagged}

    return rReport


def get_last_phone_sync(pDatabaseFile):
    """Retourne l'heure de la dernière synchronisation du téléphone, ou None."""

    vValue = get_setting_values(pDatabaseFile).get(LAST_SYNC_KEY)

    rTime = datetime.fromisoformat(vValue) if vValue else None

    return rTime


def build_offer_list(pDatabaseFile, pNow):
    """Retourne les nouvelles offres de la semaine pour le téléphone, en lecture.

    Demandée à chaque synchronisation, tâche d'arrière-plan comprise : son heure
    est gardée pour la page Santé.
    """

    save_setting_values(
        pDatabaseFile, {LAST_SYNC_KEY: pNow.isoformat(timespec="seconds")}
    )

    rOffers = [
        {
            "source": vOffer["source"],
            "source_id": str(vOffer["source_id"]),
            "title": vOffer.get("title"),
            "company": vOffer.get("company"),
            "location": vOffer.get("location"),
            "contract": vOffer.get("contract"),
            "url": vOffer.get("url"),
            "match_score": vOffer.get("match_score"),
            "distance_km": vOffer.get("distance_km"),
            "first_seen_at": vOffer.get("first_seen_at"),
            "status": vOffer.get("application_status"),
        }
        for vOffer in get_new_offers(pDatabaseFile, pNow, MAX_PHONE_OFFERS)
    ]

    return rOffers


def sync_status_changes(pDatabaseFile, pChanges, pNow):
    """Applique les statuts donnés aux offres depuis le téléphone."""

    if not isinstance(pChanges, list) or len(pChanges) > MAX_SYNC_STATUSES:
        raise ValueError(f"Liste de {MAX_SYNC_STATUSES} changements au plus attendue.")

    vApplied = 0
    vRejected = []

    for vChange in pChanges:
        vSource = str((vChange or {}).get("source") or "")
        vSourceId = str((vChange or {}).get("source_id") or "")
        vStatus = (vChange or {}).get("status")

        # Une offre supprimée entre-temps, ou un statut réservé au PC, est refusé.
        if (
            vStatus not in PHONE_STATUSES
            or get_offer(pDatabaseFile, vSource, vSourceId) is None
        ):
            vRejected.append(f"{vSource}/{vSourceId}")
            continue

        save_application(pDatabaseFile, vSource, vSourceId, vStatus, pNow=pNow)
        vApplied += 1

    logger.info(
        "Statuts d'offres du téléphone : %s appliqué(s), %s refusé(s)",
        vApplied,
        len(vRejected),
    )

    rReport = {"applied": vApplied, "rejected": vRejected}

    return rReport
