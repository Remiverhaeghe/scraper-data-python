"""Application web du tableau de bord des offres d'emploi"""

import hmac
import io
import os
import re
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import (
    APPLICATION_NAME,
    ASSETS_DIRECTORY,
    CONTACT_URL,
    DATABASE_FILE,
    LICENSE_NAME,
    REPOSITORY_URL,
    TAGLINE,
)
from job.application_tracking import (
    BOARD_STATUSES,
    build_application_statistics,
    build_board,
)
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.calendar import (
    CALENDAR_SUBSCRIPTION_PATH,
    build_calendar,
    build_subscription_url,
    check_calendar_token,
    get_calendar_token,
    renew_calendar_token,
)
from job.company_info import lookup_company, summarize_company
from job.cv_import import (
    CV_EXTENSIONS,
    MAX_CV_BYTES,
    build_cv_prompt,
    extract_profile,
    merge_profile_texts,
    read_cv_text,
)
from job.companies import (
    add_company_rule,
    build_company_filter_keys,
    describe_company_applications,
    find_company_applications,
    get_company_rule,
    load_company_rules,
    mark_preferred_companies,
    save_company_rules,
)
from job.contract import CONTRACT_TYPES
from job.manual_offers import (
    IMPORT_FORMATS,
    MAX_IMPORT_BYTES,
    add_manual_offer,
    describe_import,
    import_offers_file,
    list_import_problems,
)
from job.presentation import (
    ADDED_SOURCE_LABELS,
    AVAILABILITY_FILTERS,
    AVAILABILITY_LABELS,
    AVAILABILITY_HELP,
    AVAILABILITY_MESSAGES,
    AVAILABILITY_TONES,
    build_translate_url,
    can_lookup_company,
    CHART_PALETTE,
    CONTRACT_TONES,
    DEFAULT_AVAILABILITY,
    EXECUTION_STATUS_LABELS,
    EXECUTION_TONES,
    FOLLOW_UP_FILTER,
    LICENSE_SUMMARY,
    MANUAL_SOURCE,
    LICENSE_SUMMARY_NOTE,
    MAX_BENEFIT_BADGES,
    PUBLISHED_PERIODS,
    STATUS_LABELS,
    STATUS_TONES,
    UNKNOWN_SEARCH,
    build_legal_sections,
    build_offer_filters,
    describe_execution,
    describe_search,
    describe_sources,
    format_date,
    format_euros,
    prepare_offer,
    read_icons_license,
    read_license,
    safe_url,
    summarize_history,
)
from job.deduplication import (
    COMPARED_FIELDS,
    MERGED,
    SEPARATE,
    get_offer_group,
    group_offers,
)
from job.preparation import prepare_application, score_offers
from job.profile import (
    build_profile,
    is_profile_empty,
    load_profile,
    profile_to_texts,
    save_profile,
)
from job.quality import (
    PROBLEMS_HELP,
    build_quality_export,
    describe_problems,
    get_quality_report,
)
from job.quiz import (
    DEFAULT_MODE,
    QUIZ_LEVELS,
    QUIZ_MODES,
    answer_question,
    flag_question,
    build_quiz_overview,
    build_quiz_statistics,
    load_active_quiz,
    pick_question,
)
from job.quiz_domains import group_themes
from job.quiz_import import (
    GENERATION_COUNTS,
    IMPORT_EXTENSIONS,
    build_generation_prompt,
    describe_quiz_import,
    export_quiz_pack,
    import_questions,
    import_questions_file,
)
from job.schedule import (
    MIN_SCORE_CHOICES,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    format_min_score,
    load_schedule,
    request_immediate_run,
    save_min_score,
)
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.registry import SOURCES
from job.statistics import (
    ACTIVITY_AXES,
    ACTIVITY_SERIES,
    EMPTY_CHART_TEXT,
    EXECUTION_AXES,
    EXECUTION_CHART_SIZE,
    count_ready_sources,
    get_contract_shares,
    get_execution_counts,
    get_source_shares,
    load_statistics,
)
from storage.database import initialize_database
from storage.archive import export_archive, restore_archive
from storage.maintenance import reset_database
from storage.history_repository import get_history, get_history_summary
from storage.job_applications import (
    APPLICATION_STATUSES,
    delete_application,
    get_application,
    record_follow_up,
    save_application,
    update_application_status,
)
from storage.attachments import (
    ALLOWED_EXTENSIONS,
    MAX_ATTACHMENT_BYTES,
    add_attachment,
    delete_attachment,
    get_attachment,
    get_attachments,
)
from storage.duplicates import get_decisions, save_decision
from storage.quiz_answers import get_last_answers
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from storage.job_offers import get_offer, get_offers, set_availability
from utils.link_checker import check_offer_link
from utils.log_reader import (
    LEVEL_FILTERS,
    LEVEL_TONES,
    MAX_LOG_ENTRIES,
    clear_logs,
    export_logs,
    read_log_entries,
)
from utils.logger import get_logger, get_retention_days
from utils.mailer import get_missing_email_settings
from utils.markdown import render_markdown
from web.auth import (
    SESSION_COOKIE,
    SESSION_DURATION,
    LoginRateLimiter,
    check_credentials,
    create_session_token,
    get_missing_auth_settings,
    is_safe_redirect,
    read_session_token,
)

logger = get_logger(__name__)

WEB_DIRECTORY = Path(__file__).parent

ICONS_DIRECTORY = ASSETS_DIRECTORY / "icons"

# Schémas des questions importées : nom produit à l'import, et SVG sans script
QUIZ_ASSET_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*\.svg")
QUIZ_ASSET_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"

# Archive de questions de révision envoyée depuis le web
MAX_QUIZ_UPLOAD_BYTES = 20 * 1024 * 1024

# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300

MAX_DISPLAYED_EXECUTIONS = 200

ICON_NAME_PATTERN = re.compile(r"[a-z][a-z-]*")

# Pages accessibles sans connexion : connexion, informations légales et ressources
PUBLIC_PATHS = ("/login", "/legal", "/license")
# L'abonnement à l'agenda est relu sans session : son jeton secret le protège.
PUBLIC_PREFIXES = ("/static/", "/assets/", "/calendar/")

# Icône associée à chaque tonalité d'exécution
TONE_ICONS = {
    "success": "circle-check",
    "warning": "circle-alert",
    "danger": "circle-alert",
}


# Base de données : remplaçable dans les tests par app.dependency_overrides.
def get_database_file():
    """Retourne le chemin de la base, remplaçable dans les tests."""

    rDatabaseFile = DATABASE_FILE

    return rDatabaseFile


@asynccontextmanager
async def lifespan(pApp):
    """Prépare la base avant de servir les premières requêtes."""

    # Respecte une base de test fournie via dependency_overrides.
    vGetDatabaseFile = pApp.dependency_overrides.get(
        get_database_file, get_database_file
    )

    initialize_database(vGetDatabaseFile())

    yield


app = FastAPI(title="Offres d'emploi", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=WEB_DIRECTORY / "static"), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIRECTORY), name="assets")

templates = Jinja2Templates(directory=WEB_DIRECTORY / "templates")

login_rate_limiter = LoginRateLimiter()


# Authentification : toute page exige une session, sauf PUBLIC_PATHS et les
# ressources statiques. Mot de passe et jeton de session : voir web/auth.py.
# Une page qui renvoie sans cesse vers /login signale un .env incomplet
# (WEB_USERNAME, WEB_PASSWORD_HASH, WEB_SESSION_SECRET).
def is_public_path(pPath):
    """Indique si une adresse reste accessible sans être connecté."""

    rPublic = pPath in PUBLIC_PATHS or pPath.startswith(PUBLIC_PREFIXES)

    return rPublic


def get_csrf_token(pRequest):
    """Retourne le jeton CSRF de la session, à placer dans les formulaires."""

    vSession = getattr(pRequest.state, "session", None)

    rToken = vSession["csrf"] if vSession else ""

    return rToken


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Réserve le tableau de bord à l'utilisateur connecté."""

    vSecret = os.getenv("WEB_SESSION_SECRET")
    vToken = request.cookies.get(SESSION_COOKIE)

    request.state.session = (
        read_session_token(vSecret, vToken, datetime.now())
        if vSecret and vToken
        else None
    )

    vPath = request.url.path

    if request.state.session is None and not is_public_path(vPath):
        vTarget = f"{vPath}?{request.url.query}" if request.url.query else vPath
        vLoginUrl = f"{app.url_path_for('show_login')}?next={quote(vTarget)}"

        # HTMX remplacerait un fragment par la page de connexion : il recharge
        # plutôt toute la page vers l'adresse indiquée.
        if request.headers.get("HX-Request"):
            rResponse = Response(status_code=401, headers={"HX-Redirect": vLoginUrl})
        else:
            rResponse = RedirectResponse(vLoginUrl, status_code=303)

    else:
        rResponse = await call_next(request)

    return rResponse


# Scripts limités aux fichiers du site ; les styles en ligne restent permis pour
# les couleurs et hauteurs calculées des graphiques.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


# Déclaré après require_login, il l'englobe : les redirections vers la
# connexion reçoivent aussi les en-têtes.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Ajoute les en-têtes de sécurité HTTP à chaque réponse."""

    rResponse = await call_next(request)

    # Une route plus stricte, celle des schémas SVG, garde sa propre politique.
    for vName, vValue in SECURITY_HEADERS.items():
        rResponse.headers.setdefault(vName, vValue)

    return rResponse


async def require_csrf(request: Request):
    """Refuse une requête d'écriture sans le jeton CSRF de la session."""

    vExpected = get_csrf_token(request)
    vToken = request.headers.get("X-CSRF-Token")

    if vToken is None:
        vToken = (await request.form()).get("csrf_token")

    if not vExpected or not vToken or not hmac.compare_digest(str(vToken), vExpected):
        logger.warning(
            "Requête refusée : jeton CSRF absent ou invalide sur %s", request.url.path
        )

        raise HTTPException(
            status_code=403, detail="Jeton de sécurité invalide : rechargez la page."
        )


@lru_cache
# Fonctions et filtres disponibles dans les gabarits Jinja.
def render_icon(pName, pSize=18):
    """Retourne le SVG d'une icône à insérer dans la page, ou rien s'il n'existe pas.

    Insérée telle quelle, l'icône prend la couleur du texte grâce à currentColor.
    Seuls les noms simples d'un fichier du dossier d'icônes sont acceptés.
    """

    rIcon = Markup("")

    vPath = ICONS_DIRECTORY / f"{pName}.svg"

    if ICON_NAME_PATTERN.fullmatch(pName) and vPath.is_file():
        vSvg = vPath.read_text(encoding="utf-8")
        vSvg = vSvg[vSvg.index("<svg") :]
        vSvg = vSvg.replace('width="24"', f'width="{pSize}"', 1)
        vSvg = vSvg.replace('height="24"', f'height="{pSize}"', 1)
        vSvg = vSvg.replace("<svg", '<svg aria-hidden="true" focusable="false"', 1)

        # Fichier SVG du projet, au nom validé par ICON_NAME_PATTERN : jamais une
        # donnée saisie ou reçue d'une source.
        rIcon = Markup(vSvg)  # nosec B704

    return rIcon


templates.env.filters["euros"] = format_euros
templates.env.filters["date_fr"] = format_date
templates.env.filters["safe_url"] = safe_url

templates.env.globals.update(
    icon=render_icon,
    app_name=APPLICATION_NAME,
    tagline=TAGLINE,
    repository_url=REPOSITORY_URL,
    contact_url=CONTACT_URL,
    license_name=LICENSE_NAME,
    csrf_token=get_csrf_token,
)


# Lecture des filtres saisis : une valeur invalide est ignorée et journalisée,
# jamais transformée en erreur 500.
def parse_amount(pValue):
    """Convertit une saisie de montant en nombre, en ignorant une saisie invalide."""

    rAmount = None

    try:
        rAmount = float(pValue.replace(" ", "").replace(",", ".")) if pValue else None

    except ValueError:
        logger.warning("Montant de filtre ignoré : %s", pValue)

    return rAmount


def parse_published_days(pValue):
    """Convertit la période de publication choisie, en ignorant une valeur inconnue."""

    rDays = None

    if pValue.isdigit() and int(pValue) in PUBLISHED_PERIODS:
        rDays = int(pValue)

    return rDays


def parse_date(pValue, pFormat="%Y-%m-%d"):
    """Convertit une date saisie (AAAA-MM-JJ par défaut), ou retourne None."""

    rDate = None

    try:
        rDate = datetime.strptime(pValue, pFormat) if pValue else None

    except ValueError:
        logger.warning("Date saisie ignorée : %s", pValue)

    return rDate


# Pages d'erreur intégrées au site.
@app.exception_handler(StarletteHTTPException)
async def render_http_error(pRequest, pException):
    """Affiche une erreur dans le gabarit du site plutôt qu'en JSON brut.

    Les requêtes HTMX reçoivent un simple texte, inséré sans casser la page.
    """

    vTitle = "Page introuvable" if pException.status_code == 404 else "Requête refusée"

    if pRequest.headers.get("HX-Request"):
        rResponse = HTMLResponse(pException.detail, status_code=pException.status_code)
    else:
        rResponse = templates.TemplateResponse(
            pRequest,
            "error.html",
            {"title": vTitle, "message": pException.detail},
            status_code=pException.status_code,
        )

    return rResponse


# Préparation des graphiques : le serveur calcule les hauteurs, le dessin est
# entièrement en CSS (pas de bibliothèque JavaScript).
def build_bar_chart(
    pLabels,
    pSeries,
    pIndependentScales=False,
    pAxes=(None, None),
    pEmptyText="",
    pFillWidth=False,
):
    """Prépare un histogramme : pSeries contient des (nom, couleur, valeurs).

    Les hauteurs sont relatives à la plus grande valeur toutes séries confondues,
    ou à celle de chaque série avec pIndependentScales, pour qu'une série de
    faibles valeurs reste visible à côté d'une série de valeurs élevées.
    """

    vCommonMaximum = (
        max((vValue for _, _, vValues in pSeries for vValue in vValues), default=0) or 1
    )

    vSeries = []

    for vName, vColor, vValues in pSeries:
        vMaximum = (
            (max(vValues, default=0) or 1) if pIndependentScales else vCommonMaximum
        )

        vSeries.append(
            {
                "name": vName,
                "color": vColor,
                # Une couleur par barre quand la série en donne une liste
                "bars": [
                    {
                        "value": vValue,
                        "height": max(round(100 * vValue / vMaximum), 2),
                        "color": (
                            vColor[vIndex]
                            if isinstance(vColor, (list, tuple))
                            else vColor
                        ),
                    }
                    for vIndex, vValue in enumerate(vValues)
                ],
            }
        )

    rChart = {
        "labels": pLabels,
        "series": vSeries,
        "x_axis": pAxes[0],
        "y_axis": pAxes[1],
        "fill": pFillWidth,
        # Valeur de la ligne haute : une par série avec des échelles indépendantes
        "scale": (
            [
                {"value": max(vValues), "color": vColor}
                for _, vColor, vValues in pSeries
                if any(vValues)
            ]
            if pIndependentScales
            else [{"value": vCommonMaximum, "color": None}]
        ),
        # Sans aucune valeur, le gabarit affiche ce texte à la place des barres.
        "empty_text": (
            pEmptyText
            if not any(vValue for _, _, vValues in pSeries for vValue in vValues)
            else ""
        ),
    }

    return rChart


def build_pie(pShares):
    """Prépare un camembert CSS : dégradé conique et légende colorée."""

    vItems = [
        {**vShare, "color": CHART_PALETTE[vIndex]}
        for vIndex, vShare in enumerate(pShares)
    ]

    vSegments = []
    vStart = 0
    vTotal = sum(vItem["count"] for vItem in vItems) or 1

    for vItem in vItems:
        vEnd = vStart + 100 * vItem["count"] / vTotal
        vSegments.append(f"{vItem['color']} {vStart:.2f}% {vEnd:.2f}%")
        vStart = vEnd

    rPie = {
        "slices": vItems,
        "total": sum(vItem["count"] for vItem in vItems),
        "gradient": f"conic-gradient({', '.join(vSegments)})" if vSegments else "",
    }

    return rPie


# Pages principales. Les données et leur mise en forme viennent de job/,
# partagé avec l'application de bureau : une différence d'affichage entre les
# deux interfaces se corrige d'abord là.
@app.get("/", response_class=HTMLResponse)
def show_dashboard(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche le tableau de bord : indicateurs, graphique et activité récente."""

    vStatistics = load_statistics(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "statistics": vStatistics,
            "ready_sources": count_ready_sources(),
            "new_offer_days": vStatistics["new_offer_days"],
            "chart": build_bar_chart(
                [
                    f"{vDay:%d/%m}"
                    for vDay, _ in vStatistics["daily_activity"]["new_offers"]
                ],
                [
                    (
                        ACTIVITY_SERIES[vName][0],
                        CHART_PALETTE[vIndex],
                        [vCount for _, vCount in vCounts],
                    )
                    for vIndex, (vName, vCounts) in enumerate(
                        vStatistics["daily_activity"].items()
                    )
                ],
                pIndependentScales=True,
                pAxes=ACTIVITY_AXES,
                pEmptyText=EMPTY_CHART_TEXT,
            ),
            "activities": [
                describe_execution(vEntry) for vEntry in vStatistics["executions"]
            ],
            "tone_icons": TONE_ICONS,
            "follow_up_filter": FOLLOW_UP_FILTER,
            "now_iso": datetime.now().isoformat(),
        },
    )

    return rResponse


@app.get("/offers", response_class=HTMLResponse)
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
    pSort: str = Query("", alias="sort"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la liste des offres, ou seulement le tableau pour une requête HTMX."""

    vNow = datetime.now()
    vSettings = load_settings(pDatabaseFile)
    vNewOfferDays = vSettings["new_offer_days"]
    vNewSince = vNow - timedelta(days=vNewOfferDays)
    vCompanyRules = load_company_rules(pDatabaseFile)

    vFilters = build_offer_filters(
        pSearch=pSearch,
        pSource=pSource,
        pContract=pContract,
        pRemote=pRemote,
        pMinNetSalary=parse_amount(pMinSalary),
        pNewOnly=bool(pNew),
        pStatus=pStatus,
        pNow=vNow,
        pNewOfferDays=vNewOfferDays,
        pAvailability=pAvailability,
        pExpiryDays=vSettings["expiry_days"],
        pMaxNetSalary=parse_amount(pMaxSalary),
        pPublishedDays=parse_published_days(pPublished),
        pHasSalary=bool(pHasSalary),
        pCompanyKeys=build_company_filter_keys(vCompanyRules),
        pPreferredOnly=bool(pPreferred),
        pFranceOnly=bool(pFrance),
    )

    vOffers = get_offers(pDatabaseFile, pLimit=MAX_DISPLAYED_OFFERS + 1, **vFilters)

    vPrepared = [
        prepare_offer(vOffer, vNewSince, vNow, vSettings["expiry_days"])
        for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
    ]
    mark_preferred_companies(vPrepared, vCompanyRules)
    score_offers(vPrepared, load_profile(pDatabaseFile))

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
        "filters": {
            "availability": pAvailability,
            "multiple": pMultiple,
            "preferred": pPreferred,
            "france": pFrance,
            "sort": pSort,
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

    vTemplate = (
        "_offers_table.html" if request.headers.get("HX-Request") else "offers.html"
    )

    rResponse = templates.TemplateResponse(request, vTemplate, vContext)

    return rResponse


# Fiche d'une offre et suivi de candidature. Les formulaires sont envoyés par
# HTMX, qui remplace seulement le bloc de candidature (_application.html).
def get_existing_offer(pDatabaseFile, pSource, pSourceId):
    """Retourne une offre ou lève une erreur 404 si elle n'existe pas."""

    rOffer = get_offer(pDatabaseFile, pSource, pSourceId)

    if rOffer is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    return rOffer


def render_application(pRequest, pDatabaseFile, pOffer, pMessage=None):
    """Affiche le bloc de suivi d'une offre."""

    vApplication = get_application(pDatabaseFile, pOffer["source"], pOffer["source_id"])

    rResponse = templates.TemplateResponse(
        pRequest,
        "_application.html",
        {
            "offer": pOffer,
            "application": vApplication,
            "statuses": STATUS_LABELS,
            "message": pMessage,
        },
    )

    return rResponse


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


@app.get("/offers/new", response_class=HTMLResponse)
def show_new_offer(request: Request):
    """Affiche la saisie manuelle et l'import d'offres."""

    rResponse = render_new_offer(request)

    return rResponse


@app.post(
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


@app.post(
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


@app.get("/offer", response_class=HTMLResponse)
def show_offer(
    request: Request,
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la fiche détaillée d'une offre et son suivi."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    vSettings = load_settings(pDatabaseFile)
    vNewSince = datetime.now() - timedelta(days=vSettings["new_offer_days"])

    def prepare(pOffer):
        """Met en forme une annonce comme dans la liste des offres."""
        rOffer = prepare_offer(pOffer, vNewSince, pExpiryDays=vSettings["expiry_days"])

        return rOffer

    vPrepared = prepare(vOffer)
    vCompanyRules = load_company_rules(pDatabaseFile)

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
            "translate_url": build_translate_url(vPrepared.get("description")),
            "company_lookup": can_lookup_company(vPrepared),
            "offer": vPrepared,
            "group": get_offer_group(pDatabaseFile, vPrepared, prepare),
            "preparation": build_preparation(pDatabaseFile, vPrepared),
            "compared_fields": COMPARED_FIELDS,
            "application": get_application(pDatabaseFile, pSource, pSourceId),
            "attachments": get_attachments(pDatabaseFile, pSource, pSourceId),
            "attachment_extensions": ALLOWED_EXTENSIONS,
            "prompts": build_prompts(load_profile(pDatabaseFile), vPrepared),
            "prompt_kinds": PROMPT_KINDS,
            "chatgpt_url": CHATGPT_URL,
            "statuses": STATUS_LABELS,
            "message": None,
        },
    )

    return rResponse


@app.post(
    "/offer/application",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_application(
    request: Request,
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pStatus: str = Form("", alias="status"),
    pFollowUpDate: str = Form("", alias="follow_up_date"),
    pNotes: str = Form("", alias="notes"),
    pInterviewAt: str = Form("", alias="interview_at"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le suivi d'une offre, ou le supprime si aucun statut n'est choisi."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    if pStatus and pStatus not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")

    if pStatus:
        save_application(
            pDatabaseFile,
            pSource,
            pSourceId,
            pStatus,
            pFollowUpDate=parse_date(pFollowUpDate),
            pNotes=pNotes.strip(),
            pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
            pInterviewAt=parse_date(pInterviewAt, "%Y-%m-%dT%H:%M"),
        )

    else:
        delete_application(pDatabaseFile, pSource, pSourceId)

    rResponse = render_application(request, pDatabaseFile, vOffer, "Suivi enregistré")

    return rResponse


@app.post(
    "/offer/follow-up",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def add_follow_up(
    request: Request,
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre une relance effectuée aujourd'hui."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    if get_application(pDatabaseFile, pSource, pSourceId) is None:
        raise HTTPException(status_code=400, detail="Aucun suivi pour cette offre")

    record_follow_up(
        pDatabaseFile,
        pSource,
        pSourceId,
        pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
    )

    rResponse = render_application(
        request, pDatabaseFile, vOffer, "Relance enregistrée"
    )

    return rResponse


# Qualité des données et journaux : lecture seule, sauf la remise à zéro des
# journaux, protégée par le jeton CSRF.
@app.post(
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


def render_quiz(
    pRequest,
    pDatabaseFile,
    pTheme=None,
    pMode=DEFAULT_MODE,
    pResult=None,
    pImport=None,
    pStatusCode=200,
    pDomain=None,
):
    """Affiche les thèmes de révision, avec une question ou une correction.

    pImport porte la saisie, la demande ChatGPT et le message de l'ajout de
    questions.
    """

    vQuiz = load_active_quiz(pDatabaseFile)
    vMode = pMode if pMode in QUIZ_MODES else DEFAULT_MODE
    vTheme = pTheme if pTheme in vQuiz else None
    vQuestion = None

    if vTheme and pResult is None:
        vQuestion = pick_question(vQuiz, vTheme, vMode, get_last_answers(pDatabaseFile))

    vThemes = build_quiz_overview(pDatabaseFile, vQuiz)
    vStatistics = build_quiz_statistics(pDatabaseFile, vThemes, datetime.now())

    rResponse = templates.TemplateResponse(
        pRequest,
        "quiz.html",
        {
            "active_page": "quiz",
            "themes": vThemes,
            "themes_by_key": {vItem["key"]: vItem for vItem in vThemes},
            "theme": vTheme,
            "mode": vMode,
            "modes": QUIZ_MODES,
            "question": vQuestion,
            "result": pResult,
            "import_form": pImport or {},
            "domains": [vDomain for vDomain, _ in group_themes(vThemes)],
            "domain": pDomain,
            "groups": group_themes(vThemes, pDomain),
            "guides": get_quiz_guides(pDatabaseFile),
            "levels": QUIZ_LEVELS,
            "generation_counts": GENERATION_COUNTS,
            "import_extensions": ",".join(IMPORT_EXTENSIONS),
            "chatgpt_url": CHATGPT_URL,
            "statistics": vStatistics,
            "statistics_chart": build_bar_chart(
                [f"{vDay:%d/%m}" for vDay, _, _ in vStatistics["days"]],
                [
                    (
                        "Réponses",
                        CHART_PALETTE[0],
                        [vCount for _, vCount, _ in vStatistics["days"]],
                    ),
                    (
                        "Bonnes réponses",
                        CHART_PALETTE[1],
                        [vCorrect for _, _, vCorrect in vStatistics["days"]],
                    ),
                ],
                pAxes=("Jour", "Réponses par jour"),
                pEmptyText="Aucune réponse ces 14 derniers jours",
            ),
        },
        status_code=pStatusCode,
    )

    return rResponse


@app.get("/quiz", response_class=HTMLResponse)
def show_quiz(
    request: Request,
    pTheme: str = Query("", alias="theme"),
    pMode: str = Query(DEFAULT_MODE, alias="mode"),
    pDomain: str = Query("", alias="domain"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les thèmes de révision et, si un thème est choisi, une question."""

    rResponse = render_quiz(
        request, pDatabaseFile, pTheme, pMode, pDomain=pDomain or None
    )

    return rResponse


@app.post(
    "/quiz/answer", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def answer_quiz(
    request: Request,
    pQuestionId: str = Form(alias="question_id"),
    pChoice: int = Form(alias="choice"),
    pMode: str = Form(DEFAULT_MODE, alias="mode"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Corrige une réponse et affiche son explication."""

    try:
        vResult = answer_question(
            pDatabaseFile,
            load_active_quiz(pDatabaseFile),
            pQuestionId,
            pChoice,
            datetime.now(),
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = render_quiz(
        request, pDatabaseFile, vResult["theme_key"], pMode, pResult=vResult
    )

    return rResponse


@app.post(
    "/quiz/prompt", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def prepare_quiz_prompt(
    request: Request,
    pTheme: str = Form("", alias="theme"),
    pLevel: str = Form(QUIZ_LEVELS[0], alias="level"),
    pCount: int = Form(GENERATION_COUNTS[0], alias="count"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Prépare la demande de questions à copier dans ChatGPT."""

    vForm = {"theme": pTheme, "level": pLevel, "count": pCount}

    if not pTheme.strip() or pCount not in GENERATION_COUNTS:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={**vForm, "message": "Choisissez un thème et un nombre proposé."},
            pStatusCode=400,
        )

    else:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={
                **vForm,
                "prompt": build_generation_prompt(
                    load_active_quiz(pDatabaseFile), pTheme, pLevel, pCount
                ),
            },
        )

    return rResponse


@app.post(
    "/quiz/import", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def import_quiz_questions(
    request: Request,
    pTheme: str = Form("", alias="theme"),
    pText: str = Form("", alias="text"),
    pFile: UploadFile | None = File(None, alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Importe des questions collées ou envoyées en fichier (.json ou .zip)."""

    try:
        if pFile is not None and pFile.filename:
            # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
            vContent = pFile.file.read(MAX_QUIZ_UPLOAD_BYTES + 1)

            if len(vContent) > MAX_QUIZ_UPLOAD_BYTES:
                raise ValueError("Fichier trop volumineux.")

            vReport = import_questions_file(
                pDatabaseFile, pTheme, pFile.filename, vContent, datetime.now()
            )
        else:
            vReport = import_questions(pDatabaseFile, pTheme, pText, datetime.now())

    except ValueError as vException:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"theme": pTheme, "text": pText, "message": str(vException)},
            pStatusCode=400,
        )

    else:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"theme": pTheme, "message": describe_quiz_import(vReport)},
        )

    return rResponse


@app.get("/quiz/export")
def download_quiz_pack(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Télécharge les questions importées dans un pack .zip réimportable."""

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as vFile:
        vPath = Path(vFile.name)

    try:
        export_quiz_pack(pDatabaseFile, vPath)

    except ValueError as vException:
        vPath.unlink(missing_ok=True)

        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"message": str(vException)},
            pStatusCode=400,
        )

    else:
        # Le fichier temporaire est supprimé une fois envoyé.
        rResponse = FileResponse(
            vPath,
            media_type="application/zip",
            filename=f"questions-revision-{datetime.now():%Y%m%d}.zip",
            background=BackgroundTask(vPath.unlink, missing_ok=True),
        )

    return rResponse


@app.get("/quiz/asset/{pName}")
def show_quiz_asset(pName: str, pDatabaseFile: str = Depends(get_database_file)):
    """Sert le schéma SVG d'une question importée."""

    vContent = (
        get_quiz_asset(pDatabaseFile, pName)
        if QUIZ_ASSET_PATTERN.fullmatch(pName)
        else None
    )

    if vContent is None:
        raise HTTPException(status_code=404)

    # Vérifié sans script à l'import ; ouvert seul dans un onglet, le SVG reste
    # en plus isolé et privé de tout script par sa politique de sécurité.
    rResponse = Response(
        vContent,
        media_type="image/svg+xml",
        headers={"Content-Security-Policy": QUIZ_ASSET_POLICY},
    )

    return rResponse


@app.get("/quiz/guide/{pName}", response_class=HTMLResponse)
def show_quiz_guide(
    request: Request, pName: str, pDatabaseFile: str = Depends(get_database_file)
):
    """Affiche un guide pratique importé avec les questions."""

    vGuide = get_quiz_guide(pDatabaseFile, pName)

    if vGuide is None:
        raise HTTPException(status_code=404)

    rResponse = templates.TemplateResponse(
        request,
        "guide.html",
        {
            "active_page": "quiz",
            "guide": vGuide,
            # Texte échappé puis mis en forme par render_markdown : HTML sûr.
            "content": Markup(render_markdown(vGuide["content"])),  # nosec B704
        },
    )

    return rResponse


@app.post("/quiz/flag", dependencies=[Depends(require_csrf)])
def flag_quiz_question(
    pQuestionId: str = Form(alias="question_id"),
    pTheme: str = Form("", alias="theme"),
    pMode: str = Form(DEFAULT_MODE, alias="mode"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Retire une question douteuse des tirages, puis propose la suivante."""

    flag_question(pDatabaseFile, pQuestionId)

    rResponse = RedirectResponse(
        f"{app.url_path_for('show_quiz')}?theme={quote(pTheme)}&mode={quote(pMode)}",
        status_code=303,
    )

    return rResponse


@app.get("/offer/company-info", response_class=HTMLResponse)
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
        vCompanies = lookup_company(vOffer.get("company"))

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


def build_offer_url(pSource, pSourceId):
    """Retourne l'adresse de la fiche d'une offre."""

    rUrl = (
        f"{app.url_path_for('show_offer')}?source={quote(pSource)}"
        f"&id={quote(pSourceId)}"
    )

    return rUrl


@app.post("/offer/attachments", dependencies=[Depends(require_csrf)])
def upload_attachment(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Joint un fichier envoyé à une offre, puis rouvre sa fiche."""

    get_existing_offer(pDatabaseFile, pSource, pSourceId)

    # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
    vContent = pFile.file.read(MAX_ATTACHMENT_BYTES + 1)

    try:
        add_attachment(
            pDatabaseFile, pSource, pSourceId, pFile.filename, vContent, datetime.now()
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(build_offer_url(pSource, pSourceId), status_code=303)

    return rResponse


@app.get("/attachment")
def download_attachment(
    pAttachmentId: int = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Renvoie une pièce jointe en téléchargement, sous son nom d'origine."""

    vAttachment = get_attachment(pDatabaseFile, pAttachmentId)

    if vAttachment is None or not vAttachment["path"].is_file():
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable.")

    # Téléchargé plutôt qu'affiché : un fichier joint n'est jamais interprété
    # par le navigateur comme une page du site.
    rResponse = FileResponse(
        vAttachment["path"],
        filename=vAttachment["file_name"],
        content_disposition_type="attachment",
    )

    return rResponse


@app.post("/attachment/delete", dependencies=[Depends(require_csrf)])
def remove_attachment(
    pAttachmentId: int = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Supprime une pièce jointe puis rouvre la fiche de son offre."""

    vAttachment = get_attachment(pDatabaseFile, pAttachmentId)

    if vAttachment is None:
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable.")

    delete_attachment(pDatabaseFile, pAttachmentId)

    rResponse = RedirectResponse(
        build_offer_url(vAttachment["source"], vAttachment["source_id"]),
        status_code=303,
    )

    return rResponse


@app.get("/applications", response_class=HTMLResponse)
def show_applications(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Affiche les candidatures par étape et leurs taux de réponse."""

    rResponse = templates.TemplateResponse(
        request,
        "applications.html",
        {
            "active_page": "applications",
            "board": build_board(pDatabaseFile, datetime.now()),
            "statistics": build_application_statistics(pDatabaseFile),
            "board_statuses": BOARD_STATUSES,
            "statuses": STATUS_LABELS,
        },
    )

    return rResponse


@app.get("/applications/calendar.ics")
def download_calendar(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge les relances et entretiens au format agenda (.ics)."""

    rResponse = Response(
        build_calendar(pDatabaseFile, datetime.now()),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="candidatures.ics"'},
    )

    return rResponse


@app.post("/applications/status", dependencies=[Depends(require_csrf)])
def change_application_status(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pStatus: str = Form(alias="status"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Déplace une candidature dans la colonne de son nouveau statut."""

    if pStatus not in BOARD_STATUSES:
        raise HTTPException(status_code=400, detail="Statut de candidature invalide.")

    update_application_status(pDatabaseFile, pSource, pSourceId, pStatus)

    rResponse = RedirectResponse(app.url_path_for("show_applications"), status_code=303)

    return rResponse


@app.post("/offer/company", dependencies=[Depends(require_csrf)])
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
        app.url_path_for("list_offers")
        if pKind == "excluded"
        else build_offer_url(pSource, pSourceId)
    )

    if request.headers.get("HX-Request"):
        rResponse = Response(status_code=204, headers={"HX-Redirect": vTarget})
    else:
        rResponse = RedirectResponse(vTarget, status_code=303)

    return rResponse


@app.post("/offer/duplicates", dependencies=[Depends(require_csrf)])
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


@app.post(
    "/search/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def request_search(pDatabaseFile: str = Depends(get_database_file)):
    """Demande au planificateur de lancer la recherche enregistrée."""

    vErrors = request_immediate_run(pDatabaseFile, datetime.now())

    rResponse = HTMLResponse(
        " ".join(vErrors)
        or "Recherche demandée : le planificateur la lance dans la minute. "
        "Les nouvelles offres apparaîtront ensuite dans la liste."
    )

    return rResponse


@app.get("/quality", response_class=HTMLResponse)
def show_quality(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche le remplissage des champs, globalement puis par source."""

    vReport = get_quality_report(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        request,
        "quality.html",
        {
            "active_page": "quality",
            "report": vReport,
            "problems_text": describe_problems(vReport["problems"]),
            "problems_help": PROBLEMS_HELP,
            "chart": build_bar_chart(
                vReport["columns"],
                [
                    (
                        "Remplissage",
                        [
                            f"var(--{vRate['tone']})"
                            for vRate in vReport["total"]["rates"]
                        ],
                        [vRate["rate"] for vRate in vReport["total"]["rates"]],
                    )
                ],
                pAxes=("Champ", "% des offres renseignées"),
                pEmptyText="Aucune offre en base pour le moment",
                pFillWidth=True,
            ),
        },
    )

    return rResponse


@app.get("/quality/export")
def export_quality(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge le CSV des offres incomplètes ou mal découpées."""

    rResponse = Response(
        build_quality_export(pDatabaseFile),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="offres-a-verifier-{datetime.now():%Y%m%d}.csv"'
            )
        },
    )

    return rResponse


@app.get("/logs", response_class=HTMLResponse)
def show_logs(
    request: Request,
    pLevel: str = Query("", alias="level"),
    pSearch: str = Query("", alias="search"),
):
    """Affiche les derniers logs, filtrables par niveau et par texte."""

    vLevel = pLevel if pLevel in LEVEL_FILTERS else None
    vSearch = pSearch.strip() or None

    rResponse = templates.TemplateResponse(
        request,
        "logs.html",
        {
            "active_page": "logs",
            "entries": read_log_entries(pLevel=vLevel, pSearch=vSearch),
            "level": vLevel,
            "search": vSearch,
            "level_filters": LEVEL_FILTERS,
            "level_tones": LEVEL_TONES,
            "max_entries": MAX_LOG_ENTRIES,
            "retention_days": get_retention_days(),
        },
    )

    return rResponse


@app.get("/logs/download")
def download_logs():
    """Télécharge tous les journaux conservés dans un seul fichier texte."""

    rResponse = PlainTextResponse(
        export_logs(),
        headers={
            "Content-Disposition": (
                f'attachment; filename="journaux-{datetime.now():%Y%m%d}.log"'
            )
        },
    )

    return rResponse


@app.post("/logs/clear", dependencies=[Depends(require_csrf)])
def clear_logs_page():
    """Efface tous les journaux, puis revient à leur page."""

    clear_logs()

    rResponse = RedirectResponse(app.url_path_for("show_logs"), status_code=303)

    return rResponse


# Historique des exécutions et paramètres.
@app.get("/history", response_class=HTMLResponse)
def show_history(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la synthèse, les graphiques et la liste des dernières exécutions."""

    vExecutionCounts = get_execution_counts(pDatabaseFile)

    vExecutions = [
        {
            "started_at": vEntry.started_at,
            "search": (
                describe_search(vEntry.parameters) or UNKNOWN_SEARCH
                if vEntry.scraper_type == "job"
                else f"Livres · {vEntry.url}"
            ),
            "sources": describe_sources(vEntry.parameters),
            "item_count": vEntry.item_count,
            "duration": f"{vEntry.duration_seconds:.1f} s",
            "status": EXECUTION_STATUS_LABELS.get(vEntry.status, vEntry.status),
            "tone": EXECUTION_TONES.get(vEntry.status, "danger"),
            "error_message": vEntry.error_message,
        }
        for vEntry in get_history(pDatabaseFile, pLimit=MAX_DISPLAYED_EXECUTIONS)
    ]

    rResponse = templates.TemplateResponse(
        request,
        "history.html",
        {
            "active_page": "history",
            "summary": summarize_history(get_history_summary(pDatabaseFile)),
            "source_pie": build_pie(get_source_shares(pDatabaseFile)),
            "contract_pie": build_pie(get_contract_shares(pDatabaseFile)),
            "execution_chart": build_bar_chart(
                [vLabel for vLabel, _ in vExecutionCounts],
                [
                    (
                        "Offres",
                        CHART_PALETTE[0],
                        [vCount for _, vCount in vExecutionCounts],
                    )
                ],
                pAxes=EXECUTION_AXES,
                pEmptyText="Aucune exécution pour le moment",
            ),
            "execution_chart_size": EXECUTION_CHART_SIZE,
            "executions": vExecutions,
            "unknown_search": UNKNOWN_SEARCH,
            "tone_icons": TONE_ICONS,
        },
    )

    return rResponse


def render_settings(
    pRequest,
    pDatabaseFile,
    pMessage=None,
    pStatusCode=200,
    pResetMessage=None,
    pCompanies=None,
    pCompaniesMessage=None,
    pNotificationMessage=None,
    pCalendarMessage=None,
    pArchiveMessage=None,
):
    """Affiche thème, règles, planification, notifications et sources."""

    vSources = [
        {
            "label": vDefinition.label,
            "reason": vDefinition.get_unavailability_reason(),
            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            "missing": vDefinition.get_missing_settings(),
        }
        for vDefinition in SOURCES.values()
    ]

    vSchedule = load_schedule(pDatabaseFile)
    vSearch, vSearchSources = describe_scheduled_search(vSchedule)

    rResponse = templates.TemplateResponse(
        pRequest,
        "settings.html",
        {
            "active_page": "settings",
            "sources": vSources,
            # Sans authentification, l'adresse e-mail elle-même n'est pas affichée.
            "schedule": {
                "search": vSearch,
                "sources": vSearchSources,
                "enabled": vSchedule["enabled"],
                "interval": format_interval(vSchedule["interval_hours"]),
                "runs": describe_schedule_runs(vSchedule, datetime.now()),
                "has_email": vSchedule["email"] is not None,
                "min_score": vSchedule["min_score"],
                "missing_email_settings": get_missing_email_settings(),
            },
            "settings": load_settings(pDatabaseFile),
            "definitions": SETTING_DEFINITIONS,
            "message": pMessage,
            "reset_message": pResetMessage,
            # Textes saisis réaffichés après une erreur, sinon listes enregistrées
            "companies": pCompanies
            or {
                vKind: "\n".join(vNames)
                for vKind, vNames in load_company_rules(pDatabaseFile).items()
            },
            "companies_message": pCompaniesMessage,
            "min_scores": {
                vScore: format_min_score(vScore) for vScore in MIN_SCORE_CHOICES
            },
            "notification_message": pNotificationMessage,
            "calendar_url": build_subscription_url(
                str(pRequest.base_url), get_calendar_token(pDatabaseFile)
            ),
            "calendar_message": pCalendarMessage,
            "archive_message": pArchiveMessage,
        },
        status_code=pStatusCode,
    )

    return rResponse


def build_preparation(pDatabaseFile, pOffer):
    """Prépare la candidature pour une offre, ou None tant que le profil est vide."""

    vProfile = load_profile(pDatabaseFile)

    rPreparation = (
        None if is_profile_empty(vProfile) else prepare_application(vProfile, pOffer)
    )

    return rPreparation


def render_profile(pRequest, pTexts, pMessage=None, pStatusCode=200, pCvPrompt=None):
    """Affiche le formulaire du profil avec les textes donnés."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "profile.html",
        {
            "active_page": "profile",
            "profile": pTexts,
            "message": pMessage,
            "cv_prompt": pCvPrompt,
            "cv_extensions": ",".join(CV_EXTENSIONS),
            "chatgpt_url": CHATGPT_URL,
        },
        status_code=pStatusCode,
    )

    return rResponse


@app.get("/profile", response_class=HTMLResponse)
def show_profile(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche le profil du candidat."""

    rResponse = render_profile(request, profile_to_texts(load_profile(pDatabaseFile)))

    return rResponse


@app.post("/profile", response_class=HTMLResponse, dependencies=[Depends(require_csrf)])
def update_profile(
    request: Request,
    pName: str = Form("", alias="name"),
    pHeadline: str = Form("", alias="headline"),
    pSkills: str = Form("", alias="skills"),
    pExperiences: str = Form("", alias="experiences"),
    pCvVariants: str = Form("", alias="cv_variants"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le profil saisi, ou réaffiche le formulaire avec l'erreur."""

    vTexts = {
        "name": pName,
        "headline": pHeadline,
        "skills": pSkills,
        "experiences": pExperiences,
        "cv_variants": pCvVariants,
    }

    try:
        vProfile = build_profile(pName, pHeadline, pSkills, pExperiences, pCvVariants)

    except ValueError as vException:
        rResponse = render_profile(request, vTexts, str(vException), 400)

    else:
        save_profile(pDatabaseFile, vProfile)

        rResponse = render_profile(
            request,
            profile_to_texts(vProfile),
            f"Profil enregistré : {len(vProfile['skills'])} compétence(s), "
            f"{len(vProfile['experiences'])} expérience(s), "
            f"{len(vProfile['cv_variants'])} CV.",
        )

    return rResponse


@app.post(
    "/profile/cv", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def import_cv(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Pré-remplit le profil depuis un CV envoyé ; rien n'est enregistré."""

    vTexts = profile_to_texts(load_profile(pDatabaseFile))

    try:
        # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
        vText = read_cv_text(pFile.filename, pFile.file.read(MAX_CV_BYTES + 1))

    except ValueError as vException:
        rResponse = render_profile(request, vTexts, str(vException), 400)

    else:
        vExtracted = extract_profile(vText)

        rResponse = render_profile(
            request,
            merge_profile_texts(vTexts, vExtracted),
            f"CV importé : {len(vExtracted['skills'])} compétence(s) repérée(s). "
            "Pour les expériences, copiez la demande pour ChatGPT ci-dessous et "
            "collez sa réponse dans le formulaire. Vérifiez puis enregistrez.",
            pCvPrompt=build_cv_prompt(vText),
        )

    return rResponse


@app.get("/settings", response_class=HTMLResponse)
def show_settings(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la page des paramètres."""

    rResponse = render_settings(request, pDatabaseFile)

    return rResponse


@app.post(
    "/settings", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
async def update_settings(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre les règles de calcul saisies, ou affiche les erreurs de saisie."""

    vForm = await request.form()

    vValues = {vKey: vForm[vKey] for vKey in SETTING_DEFINITIONS if vKey in vForm}

    try:
        _, vRecomputed = save_settings(pDatabaseFile, vValues)

    except ValueError as vException:
        rResponse = render_settings(request, pDatabaseFile, str(vException), 400)

    else:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            (
                f"Règles enregistrées, salaire net recalculé pour {vRecomputed} "
                "offre(s)."
                if vRecomputed
                else "Règles enregistrées."
            ),
        )

    return rResponse


@app.post(
    "/settings/reset",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
async def reset_data(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Sauvegarde puis efface toutes les données, après confirmation explicite."""

    vForm = await request.form()

    if vForm.get("confirm") != "1":
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pResetMessage="Cochez la case de confirmation pour réinitialiser.",
        )

    else:
        try:
            vBackupFile = reset_database(pDatabaseFile, datetime.now())

        except Exception:
            logger.exception("Échec de la réinitialisation des données depuis le web")

            rResponse = render_settings(
                request,
                pDatabaseFile,
                pStatusCode=500,
                pResetMessage="La réinitialisation a échoué. Voir les journaux.",
            )

        else:
            rResponse = render_settings(
                request,
                pDatabaseFile,
                pResetMessage=(
                    f"Données réinitialisées. Sauvegarde : {vBackupFile.name}"
                ),
            )

    return rResponse


# Pages publiques : licence, connexion, déconnexion et mentions légales.
@app.post(
    "/settings/companies",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_companies(
    request: Request,
    pExcluded: str = Form("", alias="excluded"),
    pPreferred: str = Form("", alias="preferred"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre les listes d'entreprises, ou les réaffiche avec l'erreur."""

    try:
        vRules = save_company_rules(pDatabaseFile, pExcluded, pPreferred)

    except ValueError as vException:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pCompanies={"excluded": pExcluded, "preferred": pPreferred},
            pCompaniesMessage=str(vException),
        )

    else:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pCompaniesMessage=f"{len(vRules['excluded'])} entreprise(s) exclue(s), "
            f"{len(vRules['preferred'])} privilégiée(s).",
        )

    return rResponse


@app.post(
    "/settings/alerts",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_alerts(
    request: Request,
    pMinScore: int = Form(alias="min_score"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le score minimal des offres envoyées par e-mail."""

    vErrors = save_min_score(pDatabaseFile, pMinScore)

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pStatusCode=400 if vErrors else 200,
        pNotificationMessage=" ".join(vErrors) or "Alertes enregistrées.",
    )

    return rResponse


@app.post(
    "/settings/calendar",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def renew_calendar(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée une nouvelle adresse d'abonnement ; l'ancienne cesse de fonctionner."""

    renew_calendar_token(pDatabaseFile)

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pCalendarMessage="Adresse créée : ajoutez-la dans l'agenda comme agenda "
        "par URL.",
    )

    return rResponse


@app.get(CALENDAR_SUBSCRIPTION_PATH.replace("{token}", "{pToken}"))
def subscribe_calendar(
    pToken: str,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Sert l'agenda aux applications abonnées, sur présentation du jeton."""

    if not check_calendar_token(pDatabaseFile, pToken):
        # Le jeton reçu n'est pas journalisé : il pourrait être presque juste.
        logger.warning("Abonnement à l'agenda refusé : jeton invalide")

        raise HTTPException(status_code=404)

    rResponse = Response(
        build_calendar(pDatabaseFile, datetime.now()),
        media_type="text/calendar; charset=utf-8",
    )

    return rResponse


@app.get("/settings/archive")
def download_archive(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge la base et les pièces jointes dans une archive .zip."""

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as vFile:
        vPath = Path(vFile.name)

    try:
        export_archive(pDatabaseFile, vPath)

    except Exception:
        vPath.unlink(missing_ok=True)
        raise

    # Le fichier temporaire est supprimé une fois envoyé.
    rResponse = FileResponse(
        vPath,
        media_type="application/zip",
        filename=f"jobboard-{datetime.now():%Y%m%d}.zip",
        background=BackgroundTask(vPath.unlink, missing_ok=True),
    )

    return rResponse


@app.post(
    "/settings/archive",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def upload_archive(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pConfirm: str = Form("", alias="confirm"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Restaure une sauvegarde complète envoyée, après confirmation explicite."""

    if pConfirm != "1":
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pArchiveMessage="Cochez la case de confirmation pour restaurer.",
        )

    else:
        try:
            vBackupFile = restore_archive(pDatabaseFile, pFile.file, datetime.now())

        except ValueError as vException:
            logger.warning("Restauration refusée depuis le web : %s", vException)

            rResponse = render_settings(
                request, pDatabaseFile, pStatusCode=400, pArchiveMessage=str(vException)
            )

        else:
            rResponse = render_settings(
                request,
                pDatabaseFile,
                pArchiveMessage=f"Sauvegarde restaurée. Anciennes données : "
                f"{vBackupFile.name}",
            )

    return rResponse


@app.get("/license", response_class=HTMLResponse)
def show_license(request: Request):
    """Affiche la licence du projet, lue dans le fichier LICENSE."""

    rResponse = templates.TemplateResponse(
        request,
        "license.html",
        {
            "active_page": None,
            "license_text": read_license(),
            "icons_license_text": read_icons_license(),
            "license_summary": LICENSE_SUMMARY,
            "license_summary_note": LICENSE_SUMMARY_NOTE,
        },
    )

    return rResponse


def render_login(pRequest, pNext, pMessage=None, pStatusCode=200):
    """Affiche la page de connexion, ou ce qu'il manque pour l'utiliser."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "login.html",
        {
            "next": pNext if is_safe_redirect(pNext) else "/",
            "message": pMessage,
            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            "missing_settings": get_missing_auth_settings(),
        },
        status_code=pStatusCode,
    )

    return rResponse


@app.get("/login", response_class=HTMLResponse)
def show_login(request: Request, pNext: str = Query("/", alias="next")):
    """Affiche la connexion, ou renvoie vers la page demandée si déjà connecté."""

    if request.state.session:
        rResponse = RedirectResponse(
            pNext if is_safe_redirect(pNext) else "/", status_code=303
        )
    else:
        rResponse = render_login(request, pNext)

    return rResponse


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    pUsername: str = Form("", alias="username"),
    pPassword: str = Form("", alias="password"),
    pNext: str = Form("/", alias="next"),
):
    """Ouvre une session si l'identifiant et le mot de passe sont corrects."""

    vAddress = request.client.host if request.client else "inconnue"
    vNow = datetime.now()

    if get_missing_auth_settings():
        rResponse = render_login(
            request, pNext, "Authentification non configurée.", 503
        )

    elif login_rate_limiter.is_blocked(vAddress, vNow):
        logger.warning("Connexion refusée après trop d'échecs depuis %s", vAddress)

        rResponse = render_login(
            request, pNext, "Trop de tentatives. Réessayez dans 15 minutes.", 429
        )

    elif not check_credentials(pUsername, pPassword):
        login_rate_limiter.record_failure(vAddress, vNow)

        logger.warning("Échec de connexion au tableau de bord depuis %s", vAddress)

        rResponse = render_login(
            request, pNext, "Identifiant ou mot de passe incorrect.", 401
        )

    else:
        login_rate_limiter.reset(vAddress)

        logger.info("Connexion au tableau de bord depuis %s", vAddress)

        rResponse = RedirectResponse(
            pNext if is_safe_redirect(pNext) else "/", status_code=303
        )
        rResponse.set_cookie(
            SESSION_COOKIE,
            create_session_token(os.getenv("WEB_SESSION_SECRET"), pUsername, vNow),
            max_age=int(SESSION_DURATION.total_seconds()),
            httponly=True,
            samesite="lax",
            # À activer lorsque le tableau de bord est servi en HTTPS.
            secure=os.getenv("WEB_SECURE_COOKIE") == "1",
        )

    return rResponse


@app.post("/logout", dependencies=[Depends(require_csrf)])
def logout():
    """Ferme la session en supprimant son cookie."""

    logger.info("Déconnexion du tableau de bord")

    rResponse = RedirectResponse(app.url_path_for("show_login"), status_code=303)
    rResponse.delete_cookie(SESSION_COOKIE)

    return rResponse


@app.get("/legal", response_class=HTMLResponse)
def show_legal(request: Request):
    """Affiche les mentions légales et la licence."""

    rResponse = templates.TemplateResponse(
        request,
        "legal.html",
        {"active_page": None, "sections": build_legal_sections(APPLICATION_NAME)},
    )

    return rResponse
