"""Mise en forme des offres, commune au tableau de bord web et à l'interface"""

import json
from datetime import datetime, timedelta

import pandas as pd

from config import LICENSE_FILE, NEW_OFFER_DAYS
from job.contract import CONTRACT_TYPES
from job.sources.registry import SOURCES
from storage.job_applications import APPLICATION_STATUSES

BENEFIT_LABELS = {
    "has_13th_month": "13e mois",
    "has_bonus": "primes",
    "has_profit_sharing": "intéressement ou participation",
    "has_savings_plan": "épargne salariale",
}

STATUS_LABELS = {
    "INTERESTED": "Intéressé",
    "APPLIED": "Postulé",
    "INTERVIEW": "Entretien",
    "ACCEPTED": "Accepté",
    "REJECTED": "Refusé",
    "CLOSED": "Clôturé",
    "IGNORED": "Ignorée",
}

EXECUTION_STATUS_LABELS = {
    "success": "Réussie",
    "partial": "Partielle",
    "error": "En échec",
}

# Couleurs des séries et des parts de graphique, lisibles dans les deux thèmes
CHART_PALETTE = (
    "#3B82F6",
    "#F59E0B",
    "#8B5CF6",
    "#10B981",
    "#EC4899",
    "#06B6D4",
    "#94A3B8",
)

# Tonalité d'affichage de chaque statut d'exécution ; tout autre statut est un échec
EXECUTION_TONES = {"success": "success", "partial": "warning"}

# Texte des exécutions antérieures à l'enregistrement des critères
UNKNOWN_SEARCH = "Critères non enregistrés"

# Périodes proposées par le filtre de date de publication, en jours
PUBLISHED_PERIODS = {
    None: "Toutes les dates",
    1: "Publiées depuis 24 h",
    7: "Publiées depuis 7 jours",
    30: "Publiées depuis 30 jours",
}

# Valeur du filtre de statut affichant les candidatures à relancer
FOLLOW_UP_FILTER = "FOLLOW_UP"


def format_euros(pAmount):
    """Formate un montant en euros avec un espace comme séparateur de milliers."""

    rText = ""

    if pAmount is not None:
        rText = f"{round(pAmount):,} €".replace(",", "\u202f")

    return rText


def format_date(pValue):
    """Formate une date ISO au format français, ou renvoie la valeur d'origine."""

    rText = ""

    if pValue:
        try:
            rText = datetime.fromisoformat(str(pValue)).strftime("%d/%m/%Y")

        except ValueError:
            rText = str(pValue)

    return rText


def safe_url(pUrl):
    """Retourne l'URL si elle est en http ou https, sinon un lien neutre.

    L'échappement HTML ne protège pas un attribut href : une URL
    « javascript: » fournie par une source serait exécutée au clic.
    """

    rUrl = "#"

    if pUrl and str(pUrl).lower().startswith(("http://", "https://")):
        rUrl = str(pUrl)

    return rUrl


def to_list(pValue):
    """Convertit une liste enregistrée en JSON en liste Python."""

    rValues = []

    if pValue:
        try:
            vValues = json.loads(pValue)
            rValues = vValues if isinstance(vValues, list) else [pValue]

        except ValueError:
            rValues = [pValue]

    return rValues


def prepare_offer(pOffer, pNewSince):
    """Complète une offre avec les informations utiles à l'affichage."""

    vOffer = {
        vKey: (
            None if not isinstance(vValue, (list, dict)) and pd.isna(vValue) else vValue
        )
        for vKey, vValue in pOffer.items()
    }

    vSource = SOURCES.get(vOffer["source"])

    vOffer["source_label"] = vSource.label if vSource else vOffer["source"]
    vOffer["is_new"] = vOffer["first_seen_at"] >= pNewSince.isoformat()
    vOffer["skills_list"] = to_list(vOffer.get("skills"))
    vOffer["follow_up_due"] = bool(
        vOffer.get("follow_up_date")
        and vOffer.get("application_status") in ("APPLIED", "INTERVIEW")
        and vOffer["follow_up_date"] <= datetime.now().isoformat()
    )
    vOffer["benefits"] = [
        vLabel for vColumn, vLabel in BENEFIT_LABELS.items() if vOffer.get(vColumn)
    ]

    rOffer = vOffer

    return rOffer


def build_offer_filters(
    pSearch=None,
    pSource=None,
    pContract=None,
    pRemote=False,
    pMinNetSalary=None,
    pNewOnly=False,
    pStatus=None,
    pNow=None,
    pNewOfferDays=NEW_OFFER_DAYS,
    pMaxNetSalary=None,
    pPublishedDays=None,
    pHasSalary=False,
    pKeys=None,
):
    """Traduit les filtres saisis en paramètres de get_offers.

    Les valeurs inconnues sont ignorées. Les offres ignorées restent masquées
    sauf si ce statut est demandé explicitement.
    """

    vNow = pNow or datetime.now()

    rFilters = {
        "pSearch": (pSearch or "").strip() or None,
        "pSource": pSource if pSource in SOURCES else None,
        "pContract": pContract if pContract in CONTRACT_TYPES else None,
        "pRemote": bool(pRemote),
        "pMinNetSalary": pMinNetSalary,
        "pSeenSince": vNow - timedelta(days=pNewOfferDays) if pNewOnly else None,
        "pStatus": pStatus if pStatus in APPLICATION_STATUSES else None,
        "pFollowUpBefore": vNow if pStatus == FOLLOW_UP_FILTER else None,
        "pMaxNetSalary": pMaxNetSalary,
        "pPublishedSince": (
            vNow - timedelta(days=pPublishedDays) if pPublishedDays else None
        ),
        "pHasSalary": bool(pHasSalary),
        "pKeys": pKeys,
        "pHideIgnored": True,
    }

    return rFilters


def describe_search(pParameters):
    """Résume en une ligne les critères d'une recherche enregistrée.

    Une exécution antérieure à l'enregistrement des paramètres renvoie un texte
    vide, à distinguer d'une recherche lancée sans critère.
    """

    rDescription = ""

    if pParameters is not None:
        vParts = [
            pParameters.get("keyword"),
            pParameters.get("location"),
            pParameters.get("contract"),
        ]

        if pParameters.get("min_salary") is not None:
            vParts.append(f"≥ {format_euros(pParameters['min_salary'])} net")

        if pParameters.get("max_salary") is not None:
            vParts.append(f"≤ {format_euros(pParameters['max_salary'])} net")

        if pParameters.get("remote"):
            vParts.append("télétravail")

        if pParameters.get("skills"):
            vParts.append("compétences : " + ", ".join(pParameters["skills"]))

        if pParameters.get("exclude_keywords"):
            vParts.append("sans : " + ", ".join(pParameters["exclude_keywords"]))

        rDescription = " · ".join(vPart for vPart in vParts if vPart) or "Sans critère"

    return rDescription


def describe_sources(pParameters):
    """Retourne les libellés des sources interrogées lors d'une recherche."""

    rLabels = ", ".join(
        SOURCES[vName].label if vName in SOURCES else vName
        for vName in (pParameters or {}).get("sources", [])
    )

    return rLabels


def summarize_history(pSummary):
    """Traduit la synthèse de l'historique en valeurs affichables."""

    vExecutions = pSummary["executions"]

    rValues = {
        "executions": vExecutions,
        "item_count": pSummary["item_count"],
        "average_duration": f"{pSummary['average_duration']:.1f} s",
        "success_rate": (
            f"{round(100 * pSummary['successes'] / vExecutions)} %"
            if vExecutions
            else "-"
        ),
    }

    return rValues


def describe_execution(pEntry):
    """Résume une exécution : tonalité, titre, détail et nombre d'offres."""

    if pEntry.scraper_type == "job":
        vTitle = describe_search(pEntry.parameters) or "Recherche d'offres"
        vDetail = describe_sources(pEntry.parameters)
    else:
        vTitle = "Scraping de livres"
        vDetail = pEntry.url

    vDate = f"{pEntry.started_at:%d/%m/%Y à %H:%M}"

    rDescription = {
        "tone": EXECUTION_TONES.get(pEntry.status, "danger"),
        "title": vTitle,
        "detail": f"{vDate} · {vDetail}" if vDetail else vDate,
        "result": f"{pEntry.item_count} offre(s)",
    }

    return rDescription


def build_legal_sections(pApplicationName):
    """Retourne les mentions légales, communes au bureau et au web."""

    rSections = [
        (
            "Édition",
            f"{pApplicationName} est un projet personnel, sans finalité commerciale, "
            "dont le code est publié sur GitHub. L'application s'exécute sur le poste "
            "ou le serveur de la personne qui l'installe.",
        ),
        (
            "Contact",
            "Pour toute question sur le projet, l'auteur est joignable sur LinkedIn.",
        ),
        (
            "Contenus",
            "Les offres d'emploi proviennent des sources indiquées sur chaque annonce "
            "et restent la propriété de leurs éditeurs. Elles sont présentées telles "
            "que fournies par ces sources, avec un lien vers l'annonce d'origine qui "
            "fait seule foi. Les salaires nets sont des estimations calculées selon "
            "les règles des paramètres.",
        ),
        (
            "Données personnelles",
            "Le suivi des candidatures et les notes sont enregistrés uniquement dans "
            "la base de données locale de l'application. Aucun cookie n'est déposé : "
            "seul le choix du thème est conservé sur l'appareil.",
        ),
        (
            "Licence",
            "Le code peut être consulté et utilisé tel quel à des fins non "
            "commerciales, mais ni modifié ni redistribué. Les icônes proviennent de "
            "Lucide, sous licence ISC.",
        ),
    ]

    return rSections


def read_license():
    """Retourne le texte de la licence, lu dans le fichier LICENSE du projet."""

    try:
        rText = LICENSE_FILE.read_text(encoding="utf-8")

    except OSError:
        rText = "Le fichier de licence est introuvable dans cette installation."

    return rText
