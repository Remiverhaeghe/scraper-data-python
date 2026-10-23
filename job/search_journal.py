"""Journal de recherche d'emploi : démarches datées, exportées pour les justifier

Chaque candidature donne ses étapes connues : envoi, dernière relance, réponse
et entretien. Le fichier se lit dans un tableur, par exemple pour présenter ses
démarches à France Travail.
"""

import csv
import io
from datetime import datetime, timedelta

from job.export import protect_formula
from job.presentation import STATUS_LABELS, get_source_label
from storage.job_applications import get_applications_with_offers
from utils.logger import get_logger

logger = get_logger(__name__)

# Période proposée par défaut : les trois derniers mois
DEFAULT_JOURNAL_DAYS = 92

# Candidatures envoyées, quelle que soit la suite
JOURNAL_STATUSES = ("APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED", "CLOSED")

# Étape : (champ daté de la candidature, libellé de la démarche)
JOURNAL_STEPS = (
    ("applied_at", "Candidature envoyée"),
    ("last_follow_up_at", "Relance"),
    ("responded_at", "Réponse reçue"),
    ("interview_at", "Entretien"),
)

JOURNAL_COLUMNS = [
    "Date",
    "Démarche",
    "Entreprise",
    "Poste",
    "Lieu",
    "Source",
    "Statut actuel",
    "Lien",
]


def build_search_journal(pDatabaseFile, pStart, pEnd):
    """Retourne les démarches datées de pStart à pEnd inclus, les plus anciennes en tête."""

    rRows = []

    for vApplication in get_applications_with_offers(pDatabaseFile, JOURNAL_STATUSES):
        for vField, vLabel in JOURNAL_STEPS:
            vValue = vApplication.get(vField)

            if not vValue:
                continue

            vDate = datetime.fromisoformat(str(vValue)[:19])

            if pStart <= vDate < pEnd + timedelta(days=1):
                rRows.append(
                    {
                        "date": vDate,
                        "step": vLabel,
                        "company": vApplication.get("company") or "",
                        "title": vApplication.get("title") or "",
                        "location": vApplication.get("location") or "",
                        "source": get_source_label(vApplication["source"]),
                        "status": STATUS_LABELS.get(vApplication["status"], ""),
                        "url": vApplication.get("url") or "",
                    }
                )

    rRows.sort(key=lambda pRow: pRow["date"])

    return rRows


def write_journal_csv(pRows):
    """Retourne le journal en CSV pour un tableur français (point-virgule, BOM)."""

    vBuffer = io.StringIO()
    vWriter = csv.writer(vBuffer, delimiter=";")
    vWriter.writerow(JOURNAL_COLUMNS)

    for vRow in pRows:
        vWriter.writerow(
            protect_formula(vValue)
            for vValue in (
                vRow["date"].strftime("%d/%m/%Y %H:%M"),
                vRow["step"],
                vRow["company"],
                vRow["title"],
                vRow["location"],
                vRow["source"],
                vRow["status"],
                vRow["url"],
            )
        )

    logger.info("Journal de recherche exporté : %s démarche(s)", len(pRows))

    rContent = vBuffer.getvalue().encode("utf-8-sig")

    return rContent


def build_journal_file_name(pStart, pEnd):
    """Retourne le nom du fichier du journal pour une période."""

    rFileName = f"journal-recherche-{pStart:%Y%m%d}-{pEnd:%Y%m%d}.csv"

    return rFileName
