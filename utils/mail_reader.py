"""Lecture des messages reçus sur Gmail, en IMAP et en lecture seule"""

import email
import imaplib
import os
import ssl
from datetime import timedelta
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from utils.helpers import html_to_text
from utils.logger import get_logger
from utils.mailer import get_missing_email_settings

logger = get_logger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_TIMEOUT = 30

# Début du texte gardé par message : assez pour reconnaître une réponse
MAX_TEXT_LENGTH = 4000

# Messages lus au plus : les plus récents
MAX_MESSAGES = 300


def decode_text(pValue):
    """Décode un en-tête encodé (=?utf-8?...?=) en texte lisible."""

    rText = str(make_header(decode_header(pValue or "")))

    return rText


def read_body(pMessage):
    """Retourne le début du texte d'un message, sa version HTML convertie à défaut."""

    vPlain = None
    vHtml = None

    for vPart in pMessage.walk():
        if vPart.get_content_maintype() == "multipart":
            continue

        vType = vPart.get_content_type()
        vPayload = vPart.get_payload(decode=True) or b""
        vText = vPayload.decode(vPart.get_content_charset() or "utf-8", "replace")

        if vType == "text/plain" and vPlain is None:
            vPlain = vText
        elif vType == "text/html" and vHtml is None:
            vHtml = vText

    rText = (vPlain or html_to_text(vHtml) or "")[:MAX_TEXT_LENGTH]

    return rText


def parse_message(pRaw):
    """Transforme un message brut en dictionnaire : identifiant, expéditeur, objet, date, texte."""

    vMessage = email.message_from_bytes(pRaw)

    try:
        vDate = parsedate_to_datetime(vMessage.get("Date"))

    except (TypeError, ValueError):
        vDate = None

    rMessage = {
        "message_id": (vMessage.get("Message-ID") or "").strip(),
        "sender": decode_text(vMessage.get("From")),
        "subject": decode_text(vMessage.get("Subject")),
        "date": vDate,
        "text": read_body(vMessage),
    }

    return rMessage


def read_recent_messages(pNow, pDays):
    """Retourne les messages reçus depuis pDays jours, les plus récents en tête.

    La boîte est ouverte en lecture seule : aucun message n'est marqué comme lu.
    Lève ValueError si l'adresse ou le mot de passe d'application manque.
    """

    vMissing = get_missing_email_settings()

    if vMissing:
        raise ValueError(f"À renseigner dans .env : {', '.join(vMissing)}")

    vSince = (pNow - timedelta(days=pDays)).strftime("%d-%b-%Y")
    rMessages = []

    with imaplib.IMAP4_SSL(
        IMAP_HOST,
        IMAP_PORT,
        ssl_context=ssl.create_default_context(),
        timeout=IMAP_TIMEOUT,
    ) as vServer:
        vServer.login(os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD"))
        vServer.select("INBOX", readonly=True)

        _, vData = vServer.search(None, "SINCE", vSince)
        vIds = vData[0].split()[-MAX_MESSAGES:]

        for vId in reversed(vIds):
            # BODY.PEEK laisse le message non lu.
            _, vParts = vServer.fetch(vId, "(BODY.PEEK[])")
            vRaw = next(
                (vPart[1] for vPart in vParts if isinstance(vPart, tuple)), None
            )

            if vRaw:
                rMessages.append(parse_message(vRaw))

    # Ni expéditeur ni objet au journal : seulement le nombre de messages.
    logger.info("Messages Gmail lus : %s sur %s jour(s)", len(rMessages), pDays)

    return rMessages
