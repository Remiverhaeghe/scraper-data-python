"""Journal de recherche d'emploi : démarches datées, exportées pour les justifier

Chaque candidature donne ses étapes connues : envoi, dernière relance, réponse
et entretien ; les candidatures spontanées donnent les leurs. Le fichier se lit
dans un tableur, et le récapitulatif du mois s'imprime pour France Travail.
"""

import csv
import io
from datetime import date, datetime, timedelta

from job.export import protect_formula
from job.presentation import STATUS_LABELS, get_source_label
from job.profile import load_profile
from job.spontaneous_applications import STATUSES as SPONTANEOUS_STATUSES
from job.spontaneous_applications import load_spontaneous
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

# Étapes d'une candidature spontanée, datées au jour près
SPONTANEOUS_STEPS = (
    ("sent_on", "Candidature spontanée"),
    ("followed_up_on", "Relance"),
    ("answered_on", "Réponse reçue"),
)

# Démarches comptées dans le récapitulatif du mois, dans cet ordre
REPORT_STEPS = (
    "Candidature envoyée",
    "Candidature spontanée",
    "Relance",
    "Entretien",
    "Réponse reçue",
)

MONTH_NAMES = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
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

    rRows.extend(build_spontaneous_steps(pDatabaseFile, pStart, pEnd))
    rRows.sort(key=lambda pRow: pRow["date"])

    return rRows


def build_spontaneous_steps(pDatabaseFile, pStart, pEnd):
    """Retourne les étapes datées des candidatures spontanées de pStart à pEnd inclus."""

    rRows = []

    for vApplication in load_spontaneous(pDatabaseFile).values():
        for vField, vLabel in SPONTANEOUS_STEPS:
            try:
                vDate = datetime.fromisoformat(str(vApplication.get(vField) or ""))

            except ValueError:
                continue

            if pStart <= vDate < pEnd + timedelta(days=1):
                rRows.append(
                    {
                        "date": vDate,
                        "step": vLabel,
                        "company": vApplication.get("name") or "",
                        "title": "",
                        "location": "",
                        "source": "Candidature spontanée",
                        "status": SPONTANEOUS_STATUSES.get(
                            vApplication.get("status"), ""
                        ),
                        "url": "",
                    }
                )

    return rRows


def parse_month(pValue):
    """Lit un mois AAAA-MM et retourne son premier jour, ou None s'il est invalide."""

    try:
        rMonth = datetime.strptime(pValue, "%Y-%m").date() if pValue else None

    except ValueError:
        rMonth = None

    return rMonth


def build_monthly_report(pDatabaseFile, pMonth):
    """Retourne le récapitulatif des démarches d'un mois, à imprimer pour France Travail.

    Les nombres reprennent les rubriques de l'actualisation : candidatures, relances,
    entretiens ; chaque démarche est listée avec sa date.
    """

    vStart = datetime(pMonth.year, pMonth.month, 1)
    vNext = date(pMonth.year + pMonth.month // 12, pMonth.month % 12 + 1, 1)
    vEnd = datetime.combine(vNext - timedelta(days=1), datetime.min.time())
    vRows = build_search_journal(pDatabaseFile, vStart, vEnd)

    vMonthName = MONTH_NAMES[pMonth.month - 1]
    # « d'octobre », « d'avril », « d'août », « de mai »
    vOf = "d'" if vMonthName[0] in "aeiouéè" else "de "

    rReport = {
        "title": f"Démarches {vOf}{vMonthName} {pMonth.year}",
        "name": load_profile(pDatabaseFile).get("name") or "",
        "period": f"Du {vStart:%d/%m/%Y} au {vEnd:%d/%m/%Y}",
        "counts": [
            (vStep, sum(1 for vRow in vRows if vRow["step"] == vStep))
            for vStep in REPORT_STEPS
        ],
        "rows": vRows,
    }

    logger.info("Récapitulatif du mois préparé : %s démarche(s)", len(vRows))

    return rReport


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
