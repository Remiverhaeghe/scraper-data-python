"""Liste et carte des offres, avec leurs filtres"""

from datetime import datetime, timedelta
from urllib.parse import urlencode


from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse


from job.agencies import load_interim_agencies, mark_agency_offers
from job.companies import (
    build_company_filter_keys,
    load_company_rules,
    mark_preferred_companies,
)
from job.contract import CONTRACT_TYPES
from job.deduplication import group_offers
from job.education import EDUCATION_LEVELS, is_education_blocked
from job.experience_fit import mark_experience_fit
from job.freshness import add_freshness
from job.global_score import add_global_scores
from job.hybrid import mark_hybrid_offers
from job.similar_offers import mark_like_ignored
from job.suspicious_offers import mark_suspicious_offers
from job.geocoding import (
    DISTANCE_FILTERS,
    add_distances,
    describe_location,
    load_home,
    read_position,
)
from job.offer_filters import OfferFilterChoices, build_offer_filters
from job.preparation import MATCH_FILTERS, filter_by_match, score_offers
from job.presentation import (
    ADDED_SOURCE_LABELS,
    AVAILABILITY_FILTERS,
    CONTRACT_TONES,
    DEFAULT_AVAILABILITY,
    FOLLOW_UP_FILTER,
    MAX_BENEFIT_BADGES,
    PUBLISHED_PERIODS,
    STATUS_LABELS,
    STATUS_TONES,
    SCORE_FAIR,
    SCORE_GOOD,
    get_score_tone,
    prepare_offer,
)
from job.profile import load_profile
from job.salary_market import add_estimated_salaries
from job.settings import load_settings
from job.sources.registry import SOURCES
from storage.duplicates import get_decisions
from storage.job_offers import get_offers
from web.dependencies import get_database_file
from web.forms import parse_amount, parse_published_days
from web.rendering import templates

router = APIRouter()


# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300


@router.get("/offers", response_class=HTMLResponse)
def list_offers(
    request: Request,
    pSearch: str = Query("", alias="q"),
    pSource: str = Query("", alias="source"),
    pContract: str = Query("", alias="contract"),
    pRemote: str = Query("", alias="remote"),
    pMinSalary: str = Query("", alias="min_salary"),
    pMaxSalary: str = Query("", alias="max_salary"),
    pPublished: str = Query("", alias="published"),
    pHasSalary: str = Query("", alias="has_salary"),
    pNew: str = Query("", alias="new"),
    pStatus: str = Query("", alias="status"),
    pAvailability: str = Query(DEFAULT_AVAILABILITY, alias="availability"),
    pMultiple: str = Query("", alias="multiple"),
    pPreferred: str = Query("", alias="preferred"),
    pFrance: str = Query("", alias="france"),
    pNoAgency: str = Query("", alias="no_agency"),
    pNoConsulting: str = Query("", alias="no_consulting"),
    pNoTraining: str = Query("", alias="no_training"),
    pReach: str = Query("", alias="reach"),
    pHybrid: str = Query("", alias="hybrid"),
    pDistance: str = Query("", alias="distance"),
    pView: str = Query("", alias="view"),
    pSort: str = Query("", alias="sort"),
    pMatch: str = Query("", alias="match"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la liste des offres, ou seulement le tableau pour une requête HTMX."""

    vNow = datetime.now()
    vSettings = load_settings(pDatabaseFile)
    vNewOfferDays = vSettings["new_offer_days"]
    vNewSince = vNow - timedelta(days=vNewOfferDays)
    vCompanyRules = load_company_rules(pDatabaseFile)
    vHome = load_home(pDatabaseFile)
    vDistance = int(pDistance) if pDistance.isdigit() else 0
    vAgencies = load_interim_agencies(pDatabaseFile)

    vChoices = OfferFilterChoices(
        search=pSearch,
        source=pSource,
        contract=pContract,
        status=pStatus,
        availability=pAvailability,
        min_net_salary=parse_amount(pMinSalary),
        max_net_salary=parse_amount(pMaxSalary),
        published_days=parse_published_days(pPublished),
        distance_km=vDistance,
        remote=bool(pRemote),
        new_only=bool(pNew),
        has_salary=bool(pHasSalary),
        preferred_only=bool(pPreferred),
        france_only=bool(pFrance),
        hide_agencies=bool(pNoAgency),
        hide_consulting=bool(pNoConsulting),
        hide_training=bool(pNoTraining),
    )
    vFilters = build_offer_filters(
        vChoices,
        pNow=vNow,
        pNewOfferDays=vNewOfferDays,
        pExpiryDays=vSettings["expiry_days"],
        pCompanyKeys=build_company_filter_keys(vCompanyRules),
        pAgencies=vAgencies,
        pHome=vHome,
    )

    vOffers = get_offers(pDatabaseFile, pLimit=MAX_DISPLAYED_OFFERS + 1, **vFilters)

    vPrepared = [
        prepare_offer(vOffer, vNewSince, vNow, vSettings["expiry_days"])
        for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
    ]
    mark_preferred_companies(vPrepared, vCompanyRules)
    score_offers(vPrepared, load_profile(pDatabaseFile))
    add_distances(vPrepared, vHome)
    mark_agency_offers(vPrepared, vAgencies)
    mark_experience_fit(vPrepared, vSettings["experience_years"])
    mark_hybrid_offers(vPrepared)

    if pHybrid:
        vPrepared = [vOffer for vOffer in vPrepared if vOffer["hybrid_terms"]]

    if pReach:
        vPrepared = [
            vOffer
            for vOffer in vPrepared
            if not vOffer["above_experience"] and not is_education_blocked(vOffer)
        ]

    # Valeur inconnue : aucun filtre, comme pour les autres listes de choix
    vMinMatch = int(pMatch) if pMatch.isdigit() and int(pMatch) in MATCH_FILTERS else 0
    vPrepared = filter_by_match(vPrepared, vMinMatch)

    if pSort == "match":
        # Offres sans score (aucune compétence repérée) en fin de liste
        vPrepared.sort(
            key=lambda pOffer: (
                -1 if pOffer["match_score"] is None else pOffer["match_score"]
            ),
            reverse=True,
        )

    # Les annonces d'une même offre sont regroupées en une seule ligne.
    vGrouped = group_offers(vPrepared, get_decisions(pDatabaseFile))
    add_freshness(vGrouped, vNow)
    add_estimated_salaries(pDatabaseFile, vGrouped)
    mark_suspicious_offers(pDatabaseFile, vGrouped)
    mark_like_ignored(pDatabaseFile, vGrouped)
    add_global_scores(vGrouped, vSettings, (vHome or {}).get("alert_radius_km"))

    if pSort == "global":
        vGrouped.sort(
            key=lambda pOffer: (
                -1 if pOffer["global_score"] is None else pOffer["global_score"]
            ),
            reverse=True,
        )

    if pSort == "fresh":
        vGrouped.sort(key=lambda pOffer: pOffer["freshness"], reverse=True)

    # Double profil d'abord, puis le score global à l'intérieur de chaque groupe
    if pSort == "hybrid":
        vGrouped.sort(
            key=lambda pOffer: (
                bool(pOffer["hybrid_terms"]),
                -1 if pOffer["global_score"] is None else pOffer["global_score"],
            ),
            reverse=True,
        )

    # Distance inconnue en fin de liste
    if pSort == "distance":
        vGrouped.sort(
            key=lambda pOffer: (pOffer["distance_km"] is None, pOffer["distance_km"])
        )

    # Les offres proches de vos refus passent en bas, dans l'ordre choisi.
    vGrouped.sort(key=lambda pOffer: bool(pOffer["like_ignored"]))

    if pMultiple:
        vGrouped = [vOffer for vOffer in vGrouped if vOffer["duplicates"]]

    vContext = {
        "active_page": "offers",
        "contract_tones": CONTRACT_TONES,
        "status_tones": STATUS_TONES,
        "max_benefit_badges": MAX_BENEFIT_BADGES,
        "education_levels": EDUCATION_LEVELS,
        "offers": vGrouped,
        "is_truncated": len(vOffers) > MAX_DISPLAYED_OFFERS,
        "max_offers": MAX_DISPLAYED_OFFERS,
        "sources": SOURCES,
        "added_sources": ADDED_SOURCE_LABELS,
        "contracts": CONTRACT_TYPES,
        "statuses": STATUS_LABELS,
        "follow_up_filter": FOLLOW_UP_FILTER,
        "published_periods": PUBLISHED_PERIODS,
        "availability_filters": AVAILABILITY_FILTERS,
        "match_filters": MATCH_FILTERS,
        "distance_filters": DISTANCE_FILTERS,
        "home": vHome,
        "filters": {
            "availability": pAvailability,
            "multiple": pMultiple,
            "preferred": pPreferred,
            "france": pFrance,
            "no_agency": pNoAgency,
            "no_consulting": pNoConsulting,
            "no_training": pNoTraining,
            "reach": pReach,
            "hybrid": pHybrid,
            "distance": vDistance,
            "sort": pSort,
            "match": vMinMatch,
            "q": pSearch,
            "source": pSource,
            "contract": pContract,
            "remote": pRemote,
            "min_salary": pMinSalary,
            "max_salary": pMaxSalary,
            "published": pPublished,
            "has_salary": pHasSalary,
            "new": pNew,
            "status": pStatus,
        },
    }

    if request.headers.get("HX-Request"):
        vTemplate = "_offers_table.html"

    elif pView == "map":
        vTemplate = "offers_map.html"
        vContext["map_points"] = build_map_points(vGrouped)
        # Le libellé et la position suffisent : l'adresse ne quitte pas le serveur.
        vContext["map_home"] = (
            {vKey: vHome[vKey] for vKey in ("label", "latitude", "longitude")}
            if vHome
            else None
        )
        vContext["score_levels"] = (SCORE_GOOD, SCORE_FAIR)
        vContext["list_query"] = urlencode(
            [
                (vKey, vValue)
                for vKey, vValue in request.query_params.items()
                if vKey != "view"
            ]
        )
        # Raccourcis de correspondance : les autres filtres sont gardés.
        vOtherFilters = [
            (vKey, vValue)
            for vKey, vValue in request.query_params.items()
            if vKey != "match"
        ]
        vContext["map_match_links"] = [
            {
                "label": "Toutes" if vScore == 0 else f"{vScore} % et +",
                "query": urlencode([*vOtherFilters, ("match", vScore)]),
                "active": vScore == vMinMatch,
            }
            for vScore in MAP_MATCH_LEVELS
        ]

    else:
        vTemplate = "offers.html"

    rResponse = templates.TemplateResponse(request, vTemplate, vContext)

    return rResponse


# Raccourcis de correspondance proposés sur la carte, parmi MATCH_FILTERS
MAP_MATCH_LEVELS = (0, 50, 70)


def build_map_points(pOffers):
    """Retourne les offres placées sur la carte : position, résumé et lien."""

    rPoints = [
        {
            "latitude": vPosition[0],
            "longitude": vPosition[1],
            "title": vOffer.get("title") or "Offre sans titre",
            "detail": " · ".join(
                vPart
                for vPart in (vOffer.get("company"), describe_location(vOffer))
                if vPart
            ),
            "score": vOffer.get("match_score"),
            "tone": (
                None
                if vOffer.get("match_score") is None
                else get_score_tone(vOffer["match_score"])
            ),
            "url": "/offer?"
            + urlencode({"source": vOffer["source"], "id": vOffer["source_id"]}),
        }
        for vOffer in pOffers
        if (vPosition := read_position(vOffer))
    ]

    return rPoints
