"""Export des relances et des entretiens vers un agenda (format iCalendar, .ics)"""

import secrets
from datetime import datetime, timedelta, timezone

from config import APPLICATION_NAME
from job.presentation import safe_url
from storage.job_applications import get_applications_with_offers
from storage.job_offers import FOLLOW_UP_STATUSES
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Candidatures dont un entretien peut encore avoir lieu
INTERVIEW_STATUSES = ("INTERESTED", "APPLIED", "INTERVIEW", "ACCEPTED")

INTERVIEW_DURATION = timedelta(hours=1)

# Longueur maximale d'une ligne iCalendar, en octets, avant repli
MAX_LINE_BYTES = 75

# Jeton secret de l'adresse d'abonnement, relue par l'agenda sans session. La
# constante est le nom du réglage, pas le jeton : fausse alerte de bandit.
CALENDAR_TOKEN_KEY = "calendar_token"  # nosec B105

# 32 octets aléatoires : impossible à deviner, même en essayant en boucle
CALENDAR_TOKEN_BYTES = 32

# Chemin de l'abonnement sur le tableau de bord web, jeton compris
CALENDAR_SUBSCRIPTION_PATH = "/calendar/{token}.ics"


def get_calendar_token(pDatabaseFile):
    """Retourne le jeton de l'abonnement, ou None s'il n'a pas été créé."""

    rToken = get_setting_values(pDatabaseFile).get(CALENDAR_TOKEN_KEY) or None

    return rToken


def renew_calendar_token(pDatabaseFile):
    """Crée un nouveau jeton ; l'ancienne adresse cesse de fonctionner."""

    rToken = secrets.token_urlsafe(CALENDAR_TOKEN_BYTES)

    save_setting_values(pDatabaseFile, {CALENDAR_TOKEN_KEY: rToken})

    # Le jeton lui-même n'est jamais journalisé : il donne accès à l'agenda.
    logger.info("Nouvelle adresse d'abonnement à l'agenda créée")

    return rToken


def check_calendar_token(pDatabaseFile, pToken):
    """Indique si le jeton reçu correspond à celui de l'abonnement."""

    vExpected = get_calendar_token(pDatabaseFile)

    # Comparaison en temps constant : la durée ne révèle rien du jeton attendu.
    rValid = bool(vExpected and pToken) and secrets.compare_digest(
        vExpected.encode(), str(pToken).encode()
    )

    return rValid


def build_subscription_url(pBaseUrl, pToken):
    """Retourne l'adresse complète de l'abonnement, ou None sans jeton."""

    rUrl = (
        pBaseUrl.rstrip("/") + CALENDAR_SUBSCRIPTION_PATH.format(token=pToken)
        if pToken
        else None
    )

    return rUrl


def escape_text(pText):
    """Échappe un texte pour une propriété iCalendar (virgules, points-virgules…)."""

    rText = (
        str(pText or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )

    return rText


def fold_line(pLine):
    """Replie une ligne trop longue : la suite commence par une espace."""

    vParts = []
    vCurrent = ""

    for vChar in pLine:
        # Un caractère accentué occupe plusieurs octets : la limite porte sur les octets.
        if len((vCurrent + vChar).encode("utf-8")) > MAX_LINE_BYTES:
            vParts.append(vCurrent)
            vCurrent = " "

        vCurrent += vChar

    vParts.append(vCurrent)

    rLines = vParts

    return rLines


def build_event(pUid, pStart, pEnd, pSummary, pDescription, pStamp, pAllDay):
    """Construit les lignes d'un événement."""

    vFormat = "%Y%m%d" if pAllDay else "%Y%m%dT%H%M%S"
    vValue = ";VALUE=DATE" if pAllDay else ""

    rLines = [
        "BEGIN:VEVENT",
        f"UID:{pUid}",
        f"DTSTAMP:{pStamp}",
        f"DTSTART{vValue}:{pStart.strftime(vFormat)}",
        f"DTEND{vValue}:{pEnd.strftime(vFormat)}",
        f"SUMMARY:{escape_text(pSummary)}",
        f"DESCRIPTION:{escape_text(pDescription)}",
        "END:VEVENT",
    ]

    return rLines


def describe_offer(pApplication):
    """Résume l'offre : titre et entreprise."""

    rText = " – ".join(
        vPart
        for vPart in (
            pApplication["title"] or "Offre sans titre",
            pApplication["company"],
        )
        if vPart
    )

    return rText


def build_calendar(pDatabaseFile, pNow):
    """Retourne le contenu .ics des relances prévues et des entretiens."""

    vStamp = pNow.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    vLines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{APPLICATION_NAME}//Candidatures//FR",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape_text(APPLICATION_NAME)}",
    ]

    for vApplication in get_applications_with_offers(pDatabaseFile, INTERVIEW_STATUSES):
        vOffer = describe_offer(vApplication)
        vUrl = safe_url(vApplication["url"])
        vDescription = vUrl if vUrl != "#" else ""
        vKey = f"{vApplication['source']}-{vApplication['source_id']}"

        if (
            vApplication["status"] in FOLLOW_UP_STATUSES
            and vApplication["follow_up_date"]
        ):
            vDay = datetime.fromisoformat(vApplication["follow_up_date"]).date()

            vLines += build_event(
                f"relance-{vKey}@jobboard-perso",
                vDay,
                vDay + timedelta(days=1),
                f"Relancer : {vOffer}",
                vDescription,
                vStamp,
                True,
            )

        if vApplication["interview_at"]:
            # Heure locale « flottante » : l'agenda l'affiche telle quelle.
            vStart = datetime.fromisoformat(vApplication["interview_at"])

            vLines += build_event(
                f"entretien-{vKey}@jobboard-perso",
                vStart,
                vStart + INTERVIEW_DURATION,
                f"Entretien : {vOffer}",
                vDescription,
                vStamp,
                False,
            )

    vLines.append("END:VCALENDAR")

    # Le format impose des fins de ligne CRLF.
    rText = (
        "\r\n".join(vFolded for vLine in vLines for vFolded in fold_line(vLine))
        + "\r\n"
    )

    return rText
