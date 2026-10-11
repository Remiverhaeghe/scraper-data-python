"""Application web du tableau de bord des offres d'emploi"""

import hmac
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
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
from job.contract import CONTRACT_TYPES
from job.presentation import (
    CHART_PALETTE,
    CONTRACT_TONES,
    EXECUTION_STATUS_LABELS,
    EXECUTION_TONES,
    FOLLOW_UP_FILTER,
    LICENSE_SUMMARY,
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
from job.quality import build_quality_export, get_quality_report
from job.schedule import (
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    load_schedule,
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
from storage.maintenance import reset_database
from storage.history_repository import get_history, get_history_summary
from storage.job_applications import (
    APPLICATION_STATUSES,
    delete_application,
    get_application,
    record_follow_up,
    save_application,
)
from storage.job_offers import get_offer, get_offers
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

# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300

MAX_DISPLAYED_EXECUTIONS = 200

ICON_NAME_PATTERN = re.compile(r"[a-z][a-z-]*")

# Pages accessibles sans connexion : connexion, informations légales et ressources
PUBLIC_PATHS = ("/login", "/legal", "/license")
PUBLIC_PREFIXES = ("/static/", "/assets/")

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

        rIcon = Markup(vSvg)

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


def parse_date(pValue):
    """Convertit une date saisie au format AAAA-MM-JJ, ou retourne None."""

    rDate = None

    try:
        rDate = datetime.strptime(pValue, "%Y-%m-%d") if pValue else None

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
    pLabels, pSeries, pIndependentScales=False, pAxes=(None, None), pEmptyText=""
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
                "bars": [
                    {"value": vValue, "height": max(round(100 * vValue / vMaximum), 2)}
                    for vValue in vValues
                ],
            }
        )

    rChart = {
        "labels": pLabels,
        "series": vSeries,
        "x_axis": pAxes[0],
        "y_axis": pAxes[1],
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
    q: str = "",
    source: str = "",
    contract: str = "",
    remote: str = "",
    min_salary: str = "",
    max_salary: str = "",
    published: str = "",
    has_salary: str = "",
    new: str = "",
    status: str = "",
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la liste des offres, ou seulement le tableau pour une requête HTMX."""

    vNow = datetime.now()
    vNewOfferDays = load_settings(pDatabaseFile)["new_offer_days"]
    vNewSince = vNow - timedelta(days=vNewOfferDays)

    vFilters = build_offer_filters(
        pSearch=q,
        pSource=source,
        pContract=contract,
        pRemote=remote,
        pMinNetSalary=parse_amount(min_salary),
        pNewOnly=bool(new),
        pStatus=status,
        pNow=vNow,
        pNewOfferDays=vNewOfferDays,
        pMaxNetSalary=parse_amount(max_salary),
        pPublishedDays=parse_published_days(published),
        pHasSalary=bool(has_salary),
    )

    vOffers = get_offers(pDatabaseFile, pLimit=MAX_DISPLAYED_OFFERS + 1, **vFilters)

    vContext = {
        "active_page": "offers",
        "contract_tones": CONTRACT_TONES,
        "status_tones": STATUS_TONES,
        "max_benefit_badges": MAX_BENEFIT_BADGES,
        "offers": [
            prepare_offer(vOffer, vNewSince)
            for vOffer in vOffers.head(MAX_DISPLAYED_OFFERS).to_dict("records")
        ],
        "is_truncated": len(vOffers) > MAX_DISPLAYED_OFFERS,
        "max_offers": MAX_DISPLAYED_OFFERS,
        "sources": SOURCES,
        "contracts": CONTRACT_TYPES,
        "statuses": STATUS_LABELS,
        "follow_up_filter": FOLLOW_UP_FILTER,
        "published_periods": PUBLISHED_PERIODS,
        "filters": {
            "q": q,
            "source": source,
            "contract": contract,
            "remote": remote,
            "min_salary": min_salary,
            "max_salary": max_salary,
            "published": published,
            "has_salary": has_salary,
            "new": new,
            "status": status,
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


@app.get("/offer", response_class=HTMLResponse)
def show_offer(
    request: Request,
    source: str,
    id: str,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la fiche détaillée d'une offre et son suivi."""

    vOffer = get_existing_offer(pDatabaseFile, source, id)

    vNewSince = datetime.now() - timedelta(
        days=load_settings(pDatabaseFile)["new_offer_days"]
    )

    rResponse = templates.TemplateResponse(
        request,
        "offer.html",
        {
            "active_page": "offers",
            "offer": prepare_offer(vOffer, vNewSince),
            "application": get_application(pDatabaseFile, source, id),
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
    source: str = Form(...),
    id: str = Form(...),
    status: str = Form(""),
    follow_up_date: str = Form(""),
    notes: str = Form(""),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le suivi d'une offre, ou le supprime si aucun statut n'est choisi."""

    vOffer = get_existing_offer(pDatabaseFile, source, id)

    if status and status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")

    if status:
        save_application(
            pDatabaseFile,
            source,
            id,
            status,
            pFollowUpDate=parse_date(follow_up_date),
            pNotes=notes.strip(),
            pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
        )

    else:
        delete_application(pDatabaseFile, source, id)

    rResponse = render_application(request, pDatabaseFile, vOffer, "Suivi enregistré")

    return rResponse


@app.post(
    "/offer/follow-up",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def add_follow_up(
    request: Request,
    source: str = Form(...),
    id: str = Form(...),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre une relance effectuée aujourd'hui."""

    vOffer = get_existing_offer(pDatabaseFile, source, id)

    if get_application(pDatabaseFile, source, id) is None:
        raise HTTPException(status_code=400, detail="Aucun suivi pour cette offre")

    record_follow_up(
        pDatabaseFile,
        source,
        id,
        pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
    )

    rResponse = render_application(
        request, pDatabaseFile, vOffer, "Relance enregistrée"
    )

    return rResponse


# Qualité des données et journaux : lecture seule, sauf la remise à zéro des
# journaux, protégée par le jeton CSRF.
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
            "chart": build_bar_chart(
                vReport["columns"],
                [
                    (
                        "Remplissage",
                        CHART_PALETTE[0],
                        [vRate["rate"] for vRate in vReport["total"]["rates"]],
                    )
                ],
                pAxes=("Champ", "% des offres renseignées"),
                pEmptyText="Aucune offre en base pour le moment",
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
def show_logs(request: Request, level: str = "", search: str = ""):
    """Affiche les derniers logs, filtrables par niveau et par texte."""

    vLevel = level if level in LEVEL_FILTERS else None
    vSearch = search.strip() or None

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
    pRequest, pDatabaseFile, pMessage=None, pStatusCode=200, pResetMessage=None
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
                "missing_email_settings": get_missing_email_settings(),
            },
            "settings": load_settings(pDatabaseFile),
            "definitions": SETTING_DEFINITIONS,
            "message": pMessage,
            "reset_message": pResetMessage,
        },
        status_code=pStatusCode,
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
    username: str = Form(""),
    password: str = Form(""),
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

    elif not check_credentials(username, password):
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
            create_session_token(os.getenv("WEB_SESSION_SECRET"), username, vNow),
            max_age=int(SESSION_DURATION.total_seconds()),
            httponly=True,
            samesite="lax",
            # À activer lorsque le tableau de bord est servi en HTTPS.
            secure=os.getenv("WEB_SECURE_COOKIE") == "1",
        )

    return rResponse


@app.post("/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request):
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
