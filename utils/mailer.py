"""Envoi d'e-mails par le serveur SMTP de Gmail"""

import os
import smtplib
import ssl
from email.message import EmailMessage

from utils.logger import get_logger

logger = get_logger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT = 20

# Variables du fichier .env : l'adresse d'envoi et son mot de passe d'application
EMAIL_SETTINGS = ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD")


def get_missing_email_settings():
    """Retourne les variables d'environnement d'envoi non renseignées."""

    rMissing = [vName for vName in EMAIL_SETTINGS if not os.getenv(vName)]

    return rMissing


def send_email(pRecipient, pSubject, pText, pHtml=None):
    """Envoie un e-mail depuis le compte Gmail configuré dans le fichier .env."""

    vMissing = get_missing_email_settings()

    if vMissing:
        raise ValueError(f"À renseigner dans .env : {', '.join(vMissing)}")

    vSender = os.getenv("GMAIL_ADDRESS")

    vMessage = EmailMessage()
    vMessage["Subject"] = pSubject
    vMessage["From"] = vSender
    vMessage["To"] = pRecipient
    vMessage.set_content(pText)

    if pHtml is not None:
        vMessage.add_alternative(pHtml, subtype="html")

    with smtplib.SMTP_SSL(
        SMTP_HOST,
        SMTP_PORT,
        context=ssl.create_default_context(),
        timeout=SMTP_TIMEOUT,
    ) as vServer:
        vServer.login(vSender, os.getenv("GMAIL_APP_PASSWORD"))
        vServer.send_message(vMessage)

    logger.info("E-mail envoyé : %s", pSubject)
