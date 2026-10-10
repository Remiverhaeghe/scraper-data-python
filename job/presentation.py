"""Mise en forme des offres, commune au tableau de bord web et à l'interface"""

import json
from datetime import datetime, timedelta

import pandas as pd

from config import NEW_OFFER_DAYS
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
        "pSeenSince": vNow - timedelta(days=NEW_OFFER_DAYS) if pNewOnly else None,
        "pStatus": pStatus if pStatus in APPLICATION_STATUSES else None,
        "pFollowUpBefore": vNow if pStatus == FOLLOW_UP_FILTER else None,
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

        if pParameters.get("remote"):
            vParts.append("télétravail")

        rDescription = " · ".join(vPart for vPart in vParts if vPart) or "Sans critère"

    return rDescription


def describe_sources(pParameters):
    """Retourne les libellés des sources interrogées lors d'une recherche."""

    rLabels = ", ".join(
        SOURCES[vName].label if vName in SOURCES else vName
        for vName in (pParameters or {}).get("sources", [])
    )

    return rLabels
