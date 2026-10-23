"""Réponses des recruteurs repérées dans Gmail et statut proposé pour la candidature

Les messages sont lus à la demande, en lecture seule. Seuls les identifiants des
messages déjà traités sont gardés en base : ni objet ni texte ne sont enregistrés.
"""

import re

from job.fingerprint import normalize, normalize_company
from storage.job_applications import (
    get_applications_with_offers,
    update_application_status,
)
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger
from utils.mail_reader import read_recent_messages

logger = get_logger(__name__)

# Jours de messages relus à chaque lecture
REPLY_DAYS = 30

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


def mark_reply_handled(pDatabaseFile, pMessageId):
    """Note un message comme traité : il ne sera plus proposé."""

    vHandled = load_json_setting(pDatabaseFile, HANDLED_KEY, [], list)

    if pMessageId not in vHandled:
        vHandled.append(pMessageId)

    save_json_setting(pDatabaseFile, HANDLED_KEY, vHandled[-MAX_HANDLED:])


def apply_reply(pDatabaseFile, pReply, pNow):
    """Donne à la candidature le statut annoncé, puis note le message comme traité."""

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
