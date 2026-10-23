"""Filtres de la liste des offres, communs au bureau et au web

OfferFilterChoices regroupe ce que l'utilisateur a choisi dans la barre de
filtres ; build_offer_filters le traduit en paramètres de get_offers, avec le
contexte de calcul (date, réglages, listes d'entreprises, domicile).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from config import EXPIRY_DAYS, NEW_OFFER_DAYS
from job.agencies import CONSULTING_COMPANIES, INTERIM_AGENCIES
from job.contract import CONTRACT_TYPES
from job.geocoding import DISTANCE_FILTERS
from job.location import FRANCE
from job.presentation import (
    ADDED_SOURCE_LABELS,
    AVAILABILITY_FILTERS,
    DEFAULT_AVAILABILITY,
    FOLLOW_UP_FILTER,
)
from job.sources.registry import SOURCES
from storage.job_applications import APPLICATION_STATUSES


@dataclass(frozen=True)
class OfferFilterChoices:  # pylint: disable=too-many-instance-attributes
    """Choix de la barre de filtres ; une valeur inconnue est ignorée."""

    search: str | None = None
    source: str | None = None
    contract: str | None = None
    status: str | None = None
    availability: str | None = DEFAULT_AVAILABILITY
    min_net_salary: float | None = None
    max_net_salary: float | None = None
    published_days: int | None = None
    distance_km: int = 0
    remote: bool = False
    new_only: bool = False
    has_salary: bool = False
    preferred_only: bool = False
    france_only: bool = False
    hide_agencies: bool = False
    hide_consulting: bool = False
    hide_training: bool = False


def build_near(pChoices, pHome):
    """Retourne le cercle de recherche autour du domicile, ou None."""

    rNear = (
        {
            "latitude": pHome["latitude"],
            "longitude": pHome["longitude"],
            "radius_km": pChoices.distance_km,
        }
        if pHome and pChoices.distance_km and pChoices.distance_km in DISTANCE_FILTERS
        else None
    )

    return rNear


def build_offer_filters(
    pChoices,
    pNow=None,
    pNewOfferDays=NEW_OFFER_DAYS,
    pExpiryDays=EXPIRY_DAYS,
    pCompanyKeys=None,
    pAgencies=None,
    pHome=None,
    pKeys=None,
):
    """Traduit les choix de filtres en paramètres de get_offers.

    Les offres ignorées restent masquées sauf si ce statut est demandé, comme
    celles des entreprises exclues (pCompanyKeys, noms normalisés). pKeys
    restreint la liste aux offres d'une recherche.
    """

    vCompanyKeys = pCompanyKeys or {"excluded": [], "preferred": []}
    vNow = pNow or datetime.now()
    vSource = pChoices.source

    rFilters = {
        "pSearch": (pChoices.search or "").strip() or None,
        "pSource": (
            vSource if vSource in SOURCES or vSource in ADDED_SOURCE_LABELS else None
        ),
        "pContract": pChoices.contract if pChoices.contract in CONTRACT_TYPES else None,
        "pRemote": bool(pChoices.remote),
        "pMinNetSalary": pChoices.min_net_salary,
        "pSeenSince": (
            vNow - timedelta(days=pNewOfferDays) if pChoices.new_only else None
        ),
        "pStatus": (
            pChoices.status if pChoices.status in APPLICATION_STATUSES else None
        ),
        "pFollowUpBefore": vNow if pChoices.status == FOLLOW_UP_FILTER else None,
        "pMaxNetSalary": pChoices.max_net_salary,
        "pPublishedSince": (
            vNow - timedelta(days=pChoices.published_days)
            if pChoices.published_days
            else None
        ),
        "pHasSalary": bool(pChoices.has_salary),
        "pKeys": pKeys,
        "pHideIgnored": True,
        "pAvailability": (
            pChoices.availability
            if pChoices.availability in AVAILABILITY_FILTERS
            else None
        ),
        "pNow": vNow,
        "pExpiredBefore": vNow - timedelta(days=pExpiryDays),
        "pExcludedCompanies": vCompanyKeys["excluded"],
        "pPreferredCompanies": (
            vCompanyKeys["preferred"] if pChoices.preferred_only else None
        ),
        "pCountry": FRANCE if pChoices.france_only else None,
        "pHiddenAgencies": (
            (pAgencies or list(INTERIM_AGENCIES)) if pChoices.hide_agencies else None
        ),
        "pHiddenCompanies": (
            list(CONSULTING_COMPANIES) if pChoices.hide_consulting else None
        ),
        "pHideTraining": pChoices.hide_training,
        "pNear": build_near(pChoices, pHome),
    }

    return rFilters
