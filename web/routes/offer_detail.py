"""Fiche d'une offre : disponibilité, entreprise, traduction et doublons"""

from datetime import datetime, timedelta
from urllib.parse import quote


from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response


from job.agencies import load_interim_agencies
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.companies import (
    add_company_rule,
    describe_company_applications,
    find_company_applications,
    get_company_rule,
    load_company_rules,
)
from job.certifications import describe_offer_certifications, load_owned
from job.company_info import lookup_company, summarize_company
from job.deduplication import COMPARED_FIELDS, MERGED, SEPARATE, get_offer_group
from job.education import compare_education, format_education, get_profile_level
from job.experience_fit import describe_experience_fit
from job.hybrid import describe_offer_hybrid
from job.suspicious_offers import find_suspicious_signs, load_market_median
from job.geocoding import add_distances, load_home
from job.interview_journal import collect_asked_questions, collect_company_questions
from job.interview_mission import build_mission
from job.salary_negotiation import build_negotiation_view
from job.interview_revision import build_offer_revision
from job.offer_comparison import load_comparison_keys
from job.offer_details import fetch_missing_description
from job.offer_summary import build_offer_summary
from job.preparation import prepare_application
from job.presentation import (
    AVAILABILITY_HELP,
    AVAILABILITY_LABELS,
    AVAILABILITY_MESSAGES,
    AVAILABILITY_TONES,
    STATUS_LABELS,
    build_translate_url,
    can_lookup_company,
    get_score_tone,
    prepare_offer,
)
from job.profile import is_profile_empty, load_profile
from job.quiz import THEME_STATUSES, load_active_quiz
from job.quiz_exam import build_exam_history, describe_exam_results, load_exam_results
from job.salary_market import (
    describe_market_salary,
    describe_negotiation,
    describe_net_after_commute,
    find_market_salary,
)
from job.settings import load_settings
from job.star_answers import load_star_answers
from job.translation import can_translate, translate_with_cache
from storage.attachments import ALLOWED_EXTENSIONS, get_attachments
from storage.duplicates import save_decision
from storage.interview_notes import get_interview_notes
from storage.job_applications import get_application
from storage.job_offers import get_offer, set_availability
from utils.link_checker import check_offer_link
from utils.logger import get_logger
from web.dependencies import get_database_file, require_csrf
from web.rendering import build_bar_chart, templates

logger = get_logger(__name__)


router = APIRouter()


# Fiche d'une offre et suivi de candidature. Les formulaires sont envoyés par
# HTMX, qui remplace seulement le bloc de candidature (_application.html).
def get_existing_offer(pDatabaseFile, pSource, pSourceId):
    """Retourne une offre ou lève une erreur 404 si elle n'existe pas."""

    rOffer = get_offer(pDatabaseFile, pSource, pSourceId)

    if rOffer is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    return rOffer


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
    vPrepared["education_status"] = compare_education(
        vPrepared.get("education_level"),
        get_profile_level(load_profile(pDatabaseFile)),
    )
    vMarket = find_market_salary(pDatabaseFile, vPrepared)
    vCompanyRules = load_company_rules(pDatabaseFile)

    vExamResults = load_exam_results(pDatabaseFile, (pSource, str(pSourceId)))
    vPreparation = build_preparation(pDatabaseFile, vPrepared)
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
            "preparation": vPreparation,
            "negotiation_game": build_negotiation_view(pDatabaseFile),
            "mission": (
                build_mission(
                    pDatabaseFile, vPrepared, vPreparation["match"]["missing"]
                )
                if vPreparation
                else None
            ),
            "market_salary": describe_market_salary(vMarket),
            "negotiation": describe_negotiation(vMarket, vPrepared, vSettings),
            "net_after_commute": describe_net_after_commute(vPrepared, vSettings),
            "summary": build_offer_summary(vPrepared),
            "suspicious_signs": find_suspicious_signs(
                vPrepared, load_market_median(pDatabaseFile)
            ),
            "education": format_education(vPrepared),
            "certifications": describe_offer_certifications(
                vPrepared, load_owned(pDatabaseFile)
            ),
            "hybrid": describe_offer_hybrid(vPrepared),
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
        request.app.url_path_for("list_offers")
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
