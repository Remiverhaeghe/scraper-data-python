"""Réponses des recruteurs repérées dans Gmail et statut proposé pour la candidature

Les messages sont lus à la demande, en lecture seule. Seuls les identifiants des
messages déjà traités sont gardés en base : ni objet ni texte ne sont enregistrés.
"""

import hashlib
import imaplib
import re
from datetime import datetime, timedelta

from job.fingerprint import normalize, normalize_company
from storage.job_applications import (
    get_applications_with_offers,
    save_application,
    update_application_status,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger
from utils.mail_reader import read_recent_messages
from utils.mailer import get_missing_email_settings

logger = get_logger(__name__)

# Jours de messages relus à chaque lecture
REPLY_DAYS = 30

# Lecture automatique par le planificateur, pour le téléphone : au plus toutes
# les REPLY_CHECK_HOURS heures. Seuls l'offre et le statut annoncé sont gardés.
REPLY_CHECK_HOURS = 3
LAST_CHECK_KEY = "last_reply_check"
PENDING_KEY = "pending_replies"

# Messages déjà appliqués ou ignorés, à ne plus proposer
HANDLED_KEY = "handled_reply_ids"
MAX_HANDLED = 500

# Candidatures dont une réponse peut changer le statut, et statuts proposés
WATCHED_STATUSES = ("APPLIED", "INTERVIEW")
NEXT_STATUSES = {"APPLIED": ("INTERVIEW", "REJECTED"), "INTERVIEW": ("REJECTED",)}

# Repères, sur le texte normalisé (minuscules, sans accents). Le refus passe
# avant l'entretien : « suite à notre entretien, nous ne pouvons... » est un refus.
REJECTION_PATTERN = re.compile(
    r"malheureusement|pas (pu )?donner (une )?suite|ne pas donner suite"
    r"|(n a|n avons) pas ete retenu|pas ete retenue?|ne correspond pas"
    r"|regrettons|unfortunately|not (be )?moving forward|decided not to"
    r"|other candidates"
)
INTERVIEW_PATTERN = re.compile(
    r"entretien|rendez vous|vos disponibilites|echange telephonique"
    r"|vous rencontrer|interview|schedule a call|your availability"
)
# Simple accusé de réception : il annonce souvent un entretien éventuel.
ACKNOWLEDGEMENT_PATTERN = re.compile(
    r"bien recu votre candidature|candidature a bien ete|accuse de reception"
    r"|thank you for applying|received your application"
)

# Nom d'entreprise trop court pour être reconnu sans erreur
MIN_COMPANY_LENGTH = 3

HALF_YEAR_DAYS = 182

MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}

# Date d'entretien, sur le texte normalisé : « 5 novembre a 14h30 »,
# « 05 11 2026 a 14 h » (les « / » deviennent des espaces), « le 5 novembre 14h ».
WORD_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}) ("
    + "|".join(MONTHS)
    + r")(?: (\d{4}))?(?: a)? (\d{1,2}) ?h ?(\d{2})?\b"
)
NUMBER_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}) (\d{1,2}) (\d{4})(?: a)? (\d{1,2}) ?h ?(\d{2})?\b"
)


def classify_reply(pText):
    """Retourne le statut annoncé par un message (REJECTED, INTERVIEW), ou None."""

    vText = normalize(pText)

    if REJECTION_PATTERN.search(vText):
        rStatus = "REJECTED"
    elif ACKNOWLEDGEMENT_PATTERN.search(vText):
        rStatus = None
    elif INTERVIEW_PATTERN.search(vText):
        rStatus = "INTERVIEW"
    else:
        rStatus = None

    return rStatus


def find_interview_date(pText, pNow):
    """Retourne la date et l'heure d'entretien annoncées dans un message, ou None.

    Une date déjà passée n'est pas proposée.
    """

    vText = normalize(pText)
    vFound = None

    if vMatch := WORD_DATE_PATTERN.search(vText):
        vDay, vMonth, vYear, vHour, vMinute = vMatch.groups()
        vFound = (vYear, MONTHS[vMonth], vDay, vHour, vMinute)

    elif vMatch := NUMBER_DATE_PATTERN.search(vText):
        vDay, vMonth, vYear, vHour, vMinute = vMatch.groups()
        vFound = (vYear, vMonth, vDay, vHour, vMinute)

    if vFound is None:
        return None

    vYear, vMonth, vDay, vHour, vMinute = vFound

    try:
        rDate = datetime(
            int(vYear or pNow.year),
            int(vMonth),
            int(vDay),
            int(vHour),
            int(vMinute or 0),
        )

        # Sans année, « 3 janvier » lu en décembre est l'an prochain ; une date
        # passée depuis moins de six mois reste passée.
        if vYear is None and (pNow - rDate).days > HALF_YEAR_DAYS:
            rDate = rDate.replace(year=pNow.year + 1)

    except ValueError:
        return None

    if rDate < pNow:
        return None

    return rDate


def find_application(pMessage, pApplications):
    """Retourne la candidature dont l'entreprise est nommée par l'expéditeur ou l'objet."""

    # Le domaine compte : « recrutement@kiabi.com » nomme Kiabi.
    vText = f" {normalize(pMessage['sender'] + ' ' + pMessage['subject'])} "

    rApplication = next(
        (
            vApplication
            for vApplication in pApplications
            if len(vCompany := normalize_company(vApplication.get("company")))
            >= MIN_COMPANY_LENGTH
            and f" {vCompany} " in vText
        ),
        None,
    )

    return rApplication


def find_replies(pDatabaseFile, pMessages):
    """Retourne les statuts proposés : candidature, message et statut annoncé."""

    vApplications = get_applications_with_offers(pDatabaseFile, WATCHED_STATUSES)
    vHandled = set(load_json_setting(pDatabaseFile, HANDLED_KEY, [], list))
    rReplies = []

    for vMessage in pMessages:
        if vMessage["message_id"] in vHandled:
            continue

        vApplication = find_application(vMessage, vApplications)

        if vApplication is None:
            continue

        vStatus = classify_reply(f"{vMessage['subject']} {vMessage['text']}")

        if vStatus in NEXT_STATUSES.get(vApplication["status"], ()):
            rReplies.append(
                {
                    "message_id": vMessage["message_id"],
                    "subject": vMessage["subject"],
                    "date": vMessage["date"],
                    "source": vApplication["source"],
                    "source_id": vApplication["source_id"],
                    "title": vApplication["title"],
                    "company": vApplication["company"],
                    "current_status": vApplication["status"],
                    "status": vStatus,
                    "interview_at": (
                        find_interview_date(
                            f"{vMessage['subject']} {vMessage['text']}",
                            (
                                vMessage["date"].replace(tzinfo=None)
                                if vMessage["date"]
                                else datetime.now()
                            ),
                        )
                        if vStatus == "INTERVIEW"
                        else None
                    ),
                }
            )

    logger.info(
        "Réponses de recruteurs : %s statut(s) proposé(s) sur %s message(s)",
        len(rReplies),
        len(pMessages),
    )

    return rReplies


def check_replies(pDatabaseFile, pNow):
    """Lit les messages récents de Gmail et retourne les statuts proposés.

    Lève ValueError si Gmail n'est pas configuré ; OSError ou imaplib.IMAP4.error
    si la boîte est injoignable ou refuse la connexion.
    """

    rReplies = find_replies(pDatabaseFile, read_recent_messages(pNow, REPLY_DAYS))

    return rReplies


def build_reply_id(pMessageId):
    """Retourne un identifiant court du message, sans révéler son en-tête."""

    rId = hashlib.sha256(str(pMessageId).encode("utf-8")).hexdigest()[:16]

    return rId


def run_due_reply_check(pDatabaseFile, pNow):
    """Lit Gmail si la dernière lecture date de plus de REPLY_CHECK_HOURS heures.

    Les statuts proposés sont gardés pour le téléphone, sans objet ni texte du
    message. Sans Gmail configuré, rien n'est lu. Retourne le nombre gardé, ou
    None sans lecture.
    """

    if get_missing_email_settings():
        return None

    vLast = load_json_setting(pDatabaseFile, LAST_CHECK_KEY, None, str)

    if vLast and pNow - datetime.fromisoformat(vLast) < timedelta(
        hours=REPLY_CHECK_HOURS
    ):
        return None

    save_json_setting(pDatabaseFile, LAST_CHECK_KEY, pNow.isoformat(timespec="seconds"))

    try:
        vReplies = check_replies(pDatabaseFile, pNow)

    except (OSError, imaplib.IMAP4.error) as vException:
        logger.warning("Lecture automatique de Gmail impossible : %s", vException)
        return None

    save_json_setting(
        pDatabaseFile,
        PENDING_KEY,
        [
            {
                "id": build_reply_id(vReply["message_id"]),
                "title": vReply["title"],
                "company": vReply["company"],
                "status": vReply["status"],
                "interview_at": (
                    vReply["interview_at"].isoformat(timespec="minutes")
                    if vReply["interview_at"]
                    else None
                ),
            }
            for vReply in vReplies
        ],
    )

    rCount = len(vReplies)

    return rCount


def load_pending_replies(pDatabaseFile):
    """Retourne les statuts proposés lors de la dernière lecture automatique."""

    rReplies = load_json_setting(pDatabaseFile, PENDING_KEY, [], list)

    return rReplies


def mark_reply_handled(pDatabaseFile, pMessageId):
    """Note un message comme traité : il ne sera plus proposé."""

    vHandled = load_json_setting(pDatabaseFile, HANDLED_KEY, [], list)

    if pMessageId not in vHandled:
        vHandled.append(pMessageId)

    save_json_setting(pDatabaseFile, HANDLED_KEY, vHandled[-MAX_HANDLED:])


def apply_reply(pDatabaseFile, pReply, pNow):
    """Donne à la candidature le statut annoncé, puis note le message comme traité."""

    # Un entretien daté alimente le rappel de la veille et l'export agenda.
    if pReply.get("interview_at"):
        save_application(
            pDatabaseFile,
            pReply["source"],
            pReply["source_id"],
            pReply["status"],
            pNow=pNow,
            pInterviewAt=pReply["interview_at"],
        )
    else:
        update_application_status(
            pDatabaseFile, pReply["source"], pReply["source_id"], pReply["status"], pNow
        )
    mark_reply_handled(pDatabaseFile, pReply["message_id"])

    logger.info(
        "Statut appliqué depuis une réponse : %s/%s -> %s",
        pReply["source"],
        pReply["source_id"],
        pReply["status"],
    )
