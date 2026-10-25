"""Pages des offres : liste, saisie, import, fiche, disponibilité, entreprise et doublons"""

from datetime import datetime, timedelta
import io
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from job.agencies import load_interim_agencies, mark_agency_offers
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.companies import (
    add_company_rule,
    build_company_filter_keys,
    describe_company_applications,
    find_company_applications,
    get_company_rule,
    load_company_rules,
    mark_preferred_companies,
)
from job.company_info import lookup_company, summarize_company
from job.contract import CONTRACT_TYPES
from job.cv_export import (
    build_file_name,
    build_tailored_cv,
    write_docx,
    write_letter_docx,
)
from job.deduplication import (
    COMPARED_FIELDS,
    MERGED,
    SEPARATE,
    get_offer_group,
    group_offers,
)
from job.experience_fit import describe_experience_fit, mark_experience_fit
from job.freshness import add_freshness
from job.global_score import add_global_scores
from job.similar_offers import mark_like_ignored
from job.suspicious_offers import (
    find_suspicious_signs,
    load_market_median,
    mark_suspicious_offers,
)
from job.geocoding import (
    DISTANCE_FILTERS,
    add_distances,
    describe_location,
    load_home,
    read_position,
)
from job.interview_journal import (
    collect_asked_questions,
    collect_company_questions,
)
from job.interview_revision import build_offer_revision
from job.manual_offers import (
    IMPORT_FORMATS,
    MAX_IMPORT_BYTES,
    add_manual_offer,
    describe_import,
    import_offers_file,
    list_import_problems,
)
from job.offer_comparison import load_comparison_keys
from job.offer_details import fetch_missing_description
from job.offer_from_link import add_offer_from_link
from job.offer_summary import build_offer_summary
from job.offer_filters import OfferFilterChoices, build_offer_filters
from job.preparation import (
    MATCH_FILTERS,
    filter_by_match,
    prepare_application,
    score_offers,
)
from job.presentation import (
    ADDED_SOURCE_LABELS,
    AVAILABILITY_FILTERS,
    AVAILABILITY_HELP,
    AVAILABILITY_LABELS,
    AVAILABILITY_MESSAGES,
    AVAILABILITY_TONES,
    CONTRACT_TONES,
    DEFAULT_AVAILABILITY,
    FOLLOW_UP_FILTER,
    MANUAL_SOURCE,
    MAX_BENEFIT_BADGES,
    PUBLISHED_PERIODS,
    STATUS_LABELS,
    STATUS_TONES,
    build_translate_url,
    can_lookup_company,
    SCORE_FAIR,
    SCORE_GOOD,
    get_score_tone,
    clean_missing_values,
    prepare_offer,
)
from job.preparation_sheet import build_preparation_sheet
from job.profile import is_profile_empty, load_profile
from job.quiz import THEME_STATUSES, load_active_quiz
from job.quiz_exam import build_exam_history, describe_exam_results, load_exam_results
from job.salary_market import (
    add_estimated_salaries,
    describe_market_salary,
    describe_negotiation,
    describe_net_after_commute,
    find_market_salary,
)
from job.settings import load_settings
from job.sources.registry import SOURCES
from job.star_answers import load_star_answers
from job.translation import can_translate, translate_with_cache
from storage.attachments import ALLOWED_EXTENSIONS, get_attachments
from storage.duplicates import get_decisions, save_decision
from storage.interview_notes import get_interview_notes
from storage.job_applications import get_application
from storage.job_offers import get_offer, get_offers, set_availability
from utils.link_checker import check_offer_link
from utils.logger import get_logger
from web.dependencies import get_database_file, require_csrf
from web.forms import parse_amount, parse_published_days
from web.rendering import build_bar_chart, templates

logger = get_logger(__name__)

router = APIRouter()


# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300

# Longueur gardée pour une lettre envoyée par le formulaire
MAX_LETTER_LENGTH = 20000


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

    if pReach:
        vPrepared = [vOffer for vOffer in vPrepared if not vOffer["above_experience"]]

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


# Fiche d'une offre et suivi de candidature. Les formulaires sont envoyés par
# HTMX, qui remplace seulement le bloc de candidature (_application.html).
def get_existing_offer(pDatabaseFile, pSource, pSourceId):
    """Retourne une offre ou lève une erreur 404 si elle n'existe pas."""

    rOffer = get_offer(pDatabaseFile, pSource, pSourceId)

    if rOffer is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    return rOffer


def render_new_offer(pRequest, pFields=None, pMessage=None, pReport=None, pStatus=200):
    """Affiche la saisie manuelle et l'import d'offres, avec le dernier résultat."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "offer_new.html",
        {
            "active_page": "offers",
            "fields": pFields or {},
            "contracts": CONTRACT_TYPES,
            "message": pMessage,
            "report": pReport,
            "import_summary": describe_import(pReport) if pReport else None,
            "import_problems": list_import_problems(pReport) if pReport else [],
            "import_formats": IMPORT_FORMATS,
        },
        status_code=pStatus,
    )

    return rResponse


@router.get("/offers/new", response_class=HTMLResponse)
def show_new_offer(request: Request):
    """Affiche la saisie manuelle et l'import d'offres."""

    rResponse = render_new_offer(request)

    return rResponse


@router.post(
    "/offers/new", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def create_offer(
    request: Request,
    pTitle: str = Form("", alias="title"),
    pCompany: str = Form("", alias="company"),
    pUrl: str = Form("", alias="url"),
    pDescription: str = Form("", alias="description"),
    pLocation: str = Form("", alias="location"),
    pContract: str = Form("", alias="contract"),
    pSalary: str = Form("", alias="salary_label"),
    pRemote: str = Form("", alias="remote"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée une offre saisie à la main, ou réaffiche le formulaire avec l'erreur."""

    vFields = {
        "title": pTitle,
        "company": pCompany,
        "url": pUrl,
        "description": pDescription,
        "location": pLocation,
        "contract": pContract,
        "salary_label": pSalary,
        "remote": "oui" if pRemote else None,
    }

    try:
        vSourceId = add_manual_offer(pDatabaseFile, vFields, datetime.now())

    except ValueError as vException:
        rResponse = render_new_offer(request, vFields, str(vException), pStatus=400)

    else:
        rResponse = RedirectResponse(
            build_offer_url(MANUAL_SOURCE, vSourceId), status_code=303
        )

    return rResponse


@router.post(
    "/offers/from-link",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def create_offer_from_link(
    request: Request,
    pUrl: str = Form("", alias="url"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée l'offre décrite par la page d'une annonce, ou explique pourquoi non."""

    try:
        vSourceId = add_offer_from_link(pDatabaseFile, pUrl, datetime.now())

    except ValueError as vException:
        rResponse = render_new_offer(request, None, str(vException), pStatus=400)

    else:
        rResponse = RedirectResponse(
            build_offer_url(MANUAL_SOURCE, vSourceId), status_code=303
        )

    return rResponse


@router.post(
    "/offers/import",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def import_offers(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Importe les offres d'un fichier envoyé et affiche le bilan."""

    # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
    vContent = pFile.file.read(MAX_IMPORT_BYTES + 1)
    vSuffix = Path(pFile.filename or "").suffix

    try:
        if len(vContent) > MAX_IMPORT_BYTES:
            raise ValueError(
                f"Fichier trop volumineux : {MAX_IMPORT_BYTES // (1024 * 1024)} Mo "
                "au maximum."
            )

        vReport = import_offers_file(
            pDatabaseFile, io.BytesIO(vContent), vSuffix, datetime.now()
        )

    except ValueError as vException:
        rResponse = render_new_offer(request, pMessage=str(vException), pStatus=400)

    else:
        rResponse = render_new_offer(request, pReport=vReport)

    return rResponse


@router.get("/offer", response_class=HTMLResponse)
def show_offer(
    request: Request,
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la fiche détaillée d'une offre et son suivi."""

    vOffer = fetch_missing_description(
        pDatabaseFile, get_existing_offer(pDatabaseFile, pSource, pSourceId)
    )

    vSettings = load_settings(pDatabaseFile)
    vNewSince = datetime.now() - timedelta(days=vSettings["new_offer_days"])

    def prepare(pOffer):
        """Met en forme une annonce comme dans la liste des offres."""
        rOffer = prepare_offer(pOffer, vNewSince, pExpiryDays=vSettings["expiry_days"])

        return rOffer

    vPrepared = prepare(vOffer)
    add_distances([vPrepared], load_home(pDatabaseFile))
    vMarket = find_market_salary(pDatabaseFile, vPrepared)
    vCompanyRules = load_company_rules(pDatabaseFile)

    vExamResults = load_exam_results(pDatabaseFile, (pSource, str(pSourceId)))
    vComparisonKeys = load_comparison_keys(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        request,
        "offer.html",
        {
            "company_warning": describe_company_applications(
                find_company_applications(pDatabaseFile, vPrepared)
            ),
            "company_rule": get_company_rule(vPrepared.get("company"), vCompanyRules),
            "active_page": "offers",
            "availability_labels": AVAILABILITY_LABELS,
            "availability_tones": AVAILABILITY_TONES,
            "availability_help": AVAILABILITY_HELP,
            **build_description_context(vPrepared),
            "company_lookup": can_lookup_company(vPrepared),
            "offer": vPrepared,
            "group": get_offer_group(pDatabaseFile, vPrepared, prepare),
            "preparation": build_preparation(pDatabaseFile, vPrepared),
            "market_salary": describe_market_salary(vMarket),
            "negotiation": describe_negotiation(vMarket, vPrepared, vSettings),
            "net_after_commute": describe_net_after_commute(vPrepared, vSettings),
            "summary": build_offer_summary(vPrepared),
            "suspicious_signs": find_suspicious_signs(
                vPrepared, load_market_median(pDatabaseFile)
            ),
            "experience_fit": describe_experience_fit(
                vPrepared, vSettings["experience_years"]
            ),
            "revision": build_revision(pDatabaseFile, vPrepared),
            "exam_results": describe_exam_results(vExamResults),
            "exam_chart": build_exam_chart(vExamResults),
            "theme_statuses": THEME_STATUSES,
            "compared_fields": COMPARED_FIELDS,
            "application": get_application(pDatabaseFile, pSource, pSourceId),
            "attachments": get_attachments(pDatabaseFile, pSource, pSourceId),
            "interview_notes": get_interview_notes(pDatabaseFile, pSource, pSourceId),
            "company_questions": collect_company_questions(pDatabaseFile, vPrepared),
            "attachment_extensions": ALLOWED_EXTENSIONS,
            "in_comparison": (pSource, str(pSourceId)) in vComparisonKeys,
            "comparison_count": len(vComparisonKeys),
            "prompts": build_prompts(load_profile(pDatabaseFile), vPrepared),
            "prompt_kinds": PROMPT_KINDS,
            "chatgpt_url": CHATGPT_URL,
            "statuses": STATUS_LABELS,
            "message": None,
        },
    )

    return rResponse


# Qualité des données et journaux : lecture seule, sauf la remise à zéro des
# journaux, protégée par le jeton CSRF.
@router.post(
    "/offer/availability",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def check_availability(
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Vérifie le lien de l'offre et renvoie le résultat à insérer dans la fiche."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vAvailability = check_offer_link(vOffer.get("url") or "")

    if vAvailability is not None:
        set_availability(
            pDatabaseFile, pSource, pSourceId, vAvailability, datetime.now()
        )

    rResponse = HTMLResponse(
        f'<strong class="tone-{AVAILABILITY_TONES[vAvailability]}">'
        f"{AVAILABILITY_MESSAGES[vAvailability]}</strong>"
    )

    return rResponse


@router.get("/offer/company-info", response_class=HTMLResponse)
def show_company_info(
    request: Request,
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Cherche l'entreprise de l'offre dans l'annuaire public et complète la demande."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vContext = {"companies": [], "message": None}

    try:
        vCompanies = lookup_company(vOffer.get("company"), load_home(pDatabaseFile))

    except ValueError as vException:
        vContext["message"] = str(vException)

    else:
        vContext["companies"] = [
            {**vCompany, "summary": summarize_company(vCompany).split(" : ", 1)[-1]}
            for vCompany in vCompanies
        ]

        # Les résultats possibles sont repris dans la demande « Comprendre
        # l'entreprise » : ChatGPT peut reconnaître la bonne société.
        vContext["prompts"] = build_prompts(
            load_profile(pDatabaseFile),
            vOffer,
            " ; ".join(summarize_company(vCompany) for vCompany in vCompanies),
        )
        vContext["prompt_kinds"] = PROMPT_KINDS
        vContext["chatgpt_url"] = CHATGPT_URL

    rResponse = templates.TemplateResponse(request, "_company_info.html", vContext)

    return rResponse


def build_description_context(pOffer, pTranslated=False):
    """Retourne ce qu'il faut pour le bouton de traduction de la description."""

    vDescription = pOffer.get("description")
    vTranslateUrl = build_translate_url(vDescription)

    rContext = {
        "translate_url": vTranslateUrl,
        "can_translate": bool(vTranslateUrl) and can_translate(vDescription),
        "translated": pTranslated,
        "translation_url": (
            f"{router.url_path_for('show_translation')}"
            f"?source={quote(pOffer['source'])}&id={quote(str(pOffer['source_id']))}"
        ),
    }

    return rContext


@router.get("/offer/cv")
def download_tailored_cv(
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Télécharge le CV du profil réordonné pour l'offre, au format Word."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vProfile = load_profile(pDatabaseFile)

    if is_profile_empty(vProfile):
        raise HTTPException(status_code=400, detail="Profil vide : rien à exporter.")

    rResponse = Response(
        write_docx(build_tailored_cv(vProfile, vOffer)),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(build_file_name(vOffer))
        },
    )

    return rResponse


@router.post("/offer/letter", dependencies=[Depends(require_csrf)])
def download_letter(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pLetter: str = Form("", alias="letter"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Télécharge la lettre telle que modifiée dans la page, au format Word."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    rResponse = Response(
        write_letter_docx(pLetter[:MAX_LETTER_LENGTH]),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(build_file_name(vOffer, "Lettre"))
        },
    )

    return rResponse


@router.get("/offer/translation", response_class=HTMLResponse)
def show_translation(
    request: Request,
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pOriginal: bool = Query(False, alias="original"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Remplace la description par sa traduction hors ligne, ou la rétablit."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vDescription = vOffer.get("description")
    vContext = {
        **build_description_context(vOffer),
        "description": vDescription,
        "translation_message": None,
    }

    if not pOriginal:
        try:
            vContext["description"] = translate_with_cache(pDatabaseFile, vDescription)
            vContext["translated"] = True

        except ValueError as vException:
            vContext["translation_message"] = str(vException)

    rResponse = templates.TemplateResponse(request, "_offer_description.html", vContext)

    return rResponse


def build_offer_url(pSource, pSourceId):
    """Retourne l'adresse de la fiche d'une offre."""

    rUrl = (
        f"{router.url_path_for('show_offer')}?source={quote(pSource)}"
        f"&id={quote(pSourceId)}"
    )

    return rUrl


@router.post("/offer/company", dependencies=[Depends(require_csrf)])
def update_company_rule(
    request: Request,
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pKind: str = Form(alias="kind"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Exclut ou privilégie l'entreprise d'une offre, puis rouvre la page adaptée."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    try:
        add_company_rule(pDatabaseFile, vOffer.get("company"), pKind)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    # Une entreprise exclue disparaît de la liste : on y retourne plutôt qu'à la fiche.
    vTarget = (
        router.url_path_for("list_offers")
        if pKind == "excluded"
        else build_offer_url(pSource, pSourceId)
    )

    if request.headers.get("HX-Request"):
        rResponse = Response(status_code=204, headers={"HX-Redirect": vTarget})
    else:
        rResponse = RedirectResponse(vTarget, status_code=303)

    return rResponse


@router.post("/offer/duplicates", dependencies=[Depends(require_csrf)])
def decide_duplicates(
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pDecision: str = Form(..., alias="decision"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Fusionne ou sépare les annonces d'une offre, puis revient à sa fiche."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    if pDecision not in (MERGED, SEPARATE) or not vOffer.get("fingerprint"):
        raise HTTPException(status_code=400, detail="Décision invalide.")

    save_decision(pDatabaseFile, vOffer["fingerprint"], pDecision, datetime.now())

    rResponse = RedirectResponse(build_offer_url(pSource, pSourceId), status_code=303)

    return rResponse


def build_exam_chart(pResults):
    """Prépare le graphique des notes successives, ou None avant deux examens."""

    vHistory = build_exam_history(pResults)

    rChart = (
        build_bar_chart(
            [vPoint["label"] for vPoint in vHistory],
            [
                (
                    "Note",
                    [
                        f"var(--{get_score_tone(vPoint['score'], 'danger')})"
                        for vPoint in vHistory
                    ],
                    [vPoint["score"] for vPoint in vHistory],
                )
            ],
            pAxes=("Examen", "% de bonnes réponses"),
            pFillWidth=True,
        )
        if len(vHistory) >= 2
        else None
    )

    return rChart


@router.get("/offer/sheet", response_class=HTMLResponse)
def show_preparation_sheet(
    request: Request,
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la fiche de préparation d'entretien, prête à imprimer en PDF."""

    vOffer = clean_missing_values(get_existing_offer(pDatabaseFile, pSource, pSourceId))

    rResponse = templates.TemplateResponse(
        request,
        "preparation_sheet.html",
        {"sheet": build_preparation_sheet(pDatabaseFile, vOffer)},
    )

    return rResponse


def build_preparation(pDatabaseFile, pOffer):
    """Prépare la candidature pour une offre, ou None tant que le profil est vide."""

    vProfile = load_profile(pDatabaseFile)

    rPreparation = (
        None
        if is_profile_empty(vProfile)
        else prepare_application(
            vProfile,
            pOffer,
            load_star_answers(pDatabaseFile),
            collect_asked_questions(pDatabaseFile),
            load_interim_agencies(pDatabaseFile),
        )
    )

    return rPreparation


def build_revision(pDatabaseFile, pOffer):
    """Retourne les thèmes à revoir pour l'offre, ou None si le calcul échoue."""

    try:
        rRevision = build_offer_revision(
            pDatabaseFile, load_active_quiz(pDatabaseFile), pOffer
        )

    except Exception:
        # La fiche reste consultable même si la révision est illisible.
        logger.exception(
            "Échec de la révision ciblée pour l'offre %s/%s",
            pOffer.get("source"),
            pOffer.get("source_id"),
        )

        rRevision = None

    return rRevision
