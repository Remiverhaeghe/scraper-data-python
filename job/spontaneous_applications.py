"""Suivi des candidatures spontanées envoyées aux employeurs de la région

Une candidature spontanée n'a pas d'offre : elle est rattachée à l'employeur par
son numéro SIREN, avec sa date d'envoi, sa relance et la réponse reçue. Une
candidature restée sans réponse est à relancer au bout de FOLLOW_UP_DAYS jours.
L'envoi et la relance rapportent des points, comme pour une offre.
"""

from datetime import date, timedelta

from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

SPONTANEOUS_KEY = "spontaneous_applications"
FOLLOW_UP_DAYS = 15
MAX_NOTE_LENGTH = 500

STATUSES = {
    "sent": "Envoyée",
    "followed_up": "Relancée",
    "interview": "Entretien obtenu",
    "refused": "Refus",
    "no_answer": "Sans réponse",
}
# Une réponse reçue clôt le suivi : plus de relance à proposer
CLOSED_STATUSES = ("interview", "refused", "no_answer")


def load_spontaneous(pDatabaseFile):
    """Retourne les candidatures spontanées, par SIREN de l'employeur."""

    rApplications = load_json_setting(pDatabaseFile, SPONTANEOUS_KEY, {}, dict)

    return rApplications


def save_spontaneous(pDatabaseFile, pSiren, pName, pStatus, pToday, pNote=None):
    """Enregistre l'étape d'une candidature spontanée ; un statut vide la retire.

    Lève ValueError pour un statut inconnu. L'envoi garde sa première date ; une
    relance ou une réponse sans envoi noté compte l'envoi le jour même.
    """

    if pStatus and pStatus not in STATUSES:
        raise ValueError("Étape de candidature inconnue.")

    vApplications = load_spontaneous(pDatabaseFile)

    if not pStatus:
        vApplications.pop(pSiren, None)
        logger.info("Candidature spontanée retirée du suivi : %s", pName)
    else:
        vApplication = vApplications.setdefault(pSiren, {})
        vApplication["name"] = pName
        vApplication["status"] = pStatus
        vApplication.setdefault("sent_on", pToday.isoformat())

        if pStatus == "followed_up":
            vApplication["followed_up_on"] = pToday.isoformat()

        if pStatus in CLOSED_STATUSES:
            vApplication["answered_on"] = pToday.isoformat()

        if pNote is not None:
            vApplication["note"] = pNote.strip()[:MAX_NOTE_LENGTH]

        logger.info("Candidature spontanée chez %s : %s", pName, STATUSES[pStatus])

    save_json_setting(pDatabaseFile, SPONTANEOUS_KEY, vApplications)


def describe_spontaneous(pApplication, pToday):
    """Retourne le suivi lisible d'une candidature : étape, dates, relance due."""

    if not pApplication:
        return None

    vLast = date.fromisoformat(
        pApplication.get("followed_up_on") or pApplication["sent_on"]
    )

    rDescription = {
        **pApplication,
        "status_label": STATUSES.get(pApplication.get("status"), ""),
        "follow_up_on": (vLast + timedelta(days=FOLLOW_UP_DAYS)).isoformat(),
        "follow_up_due": pApplication.get("status") not in CLOSED_STATUSES
        and pToday >= vLast + timedelta(days=FOLLOW_UP_DAYS),
    }

    return rDescription


def list_due_follow_ups(pDatabaseFile, pToday):
    """Retourne les candidatures spontanées à relancer, les plus anciennes d'abord."""

    rDue = sorted(
        (
            {"siren": vSiren, **vDescription}
            for vSiren, vApplication in load_spontaneous(pDatabaseFile).items()
            if (vDescription := describe_spontaneous(vApplication, pToday))[
                "follow_up_due"
            ]
        ),
        key=lambda pItem: pItem["follow_up_on"],
    )

    return rDue


def get_contact_tone(pSpontaneous):
    """Retourne la teinte d'un employeur sur la carte selon sa candidature spontanée."""

    if pSpontaneous is None:
        return "primary"

    if pSpontaneous["follow_up_due"]:
        return "danger"

    rTone = {"interview": "success", "refused": "muted", "no_answer": "muted"}.get(
        pSpontaneous.get("status"), "warning"
    )

    return rTone
