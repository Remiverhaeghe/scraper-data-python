"""Application web du tableau de bord des offres d'emploi"""

import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import (
    APPLICATION_NAME,
    ASSETS_DIRECTORY,
    DATABASE_FILE,
    LICENSE_NAME,
    NEW_OFFER_DAYS,
    REPOSITORY_URL,
    TAGLINE,
)
from job.contract import CONTRACT_TYPES
from job.presentation import (
    CHART_PALETTE,
    EXECUTION_STATUS_LABELS,
    EXECUTION_TONES,
    FOLLOW_UP_FILTER,
    STATUS_LABELS,
    UNKNOWN_SEARCH,
    build_offer_filters,
    describe_execution,
    describe_rules,
    describe_search,
    describe_sources,
    format_date,
    format_euros,
    prepare_offer,
    safe_url,
    summarize_history,
)
from job.sources.registry import SOURCES
from job.statistics import (
    ACTIVITY_SERIES,
    CHART_DAYS,
    EXECUTION_CHART_SIZE,
    count_ready_sources,
    get_execution_counts,
    get_source_shares,
    load_statistics,
)
from storage.database import initialize_database
from storage.history_repository import get_history, get_history_summary
from storage.job_applications import (
    APPLICATION_STATUSES,
    delete_application,
    get_application,
    record_follow_up,
    save_application,
)
from storage.job_offers import get_offer, get_offers
from utils.logger import get_logger

logger = get_logger(__name__)

WEB_DIRECTORY = Path(__file__).parent

ICONS_DIRECTORY = ASSETS_DIRECTORY / "icons"

# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300

MAX_DISPLAYED_EXECUTIONS = 200

ICON_NAME_PATTERN = re.compile(r"[a-z][a-z-]*")

# Icône associée à chaque tonalité d'exécution
TONE_ICONS = {
    "success": "circle-check",
    "warning": "circle-alert",
    "danger": "circle-alert",
}


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


@lru_cache
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
    license_name=LICENSE_NAME,
)


def parse_amount(pValue):
    """Convertit une saisie de montant en nombre, en ignorant une saisie invalide."""

    rAmount = None

    try:
        rAmount = float(pValue.replace(" ", "").replace(",", ".")) if pValue else None

    except ValueError:
        logger.warning("Montant de filtre ignoré : %s", pValue)

    return rAmount


def parse_date(pValue):
    """Convertit une date saisie au format AAAA-MM-JJ, ou retourne None."""

    rDate = None

    try:
        rDate = datetime.strptime(pValue, "%Y-%m-%d") if pValue else None

    except ValueError:
        logger.warning("Date saisie ignorée : %s", pValue)

    return rDate


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


def build_bar_chart(pLabels, pSeries, pIndependentScales=False):
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

    rChart = {"labels": pLabels, "series": vSeries}

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
            "new_offer_days": NEW_OFFER_DAYS,
            "chart_days": CHART_DAYS,
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
            ),
            "activities": [
                describe_execution(vEntry) for vEntry in vStatistics["executions"]
            ],
            "tone_icons": TONE_ICONS,
            "follow_up_filter": FOLLOW_UP_FILTER,
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
    new: str = "",
    status: str = "",
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la liste des offres, ou seulement le tableau pour une requête HTMX."""

    vNow = datetime.now()
    vNewSince = vNow - timedelta(days=NEW_OFFER_DAYS)

    vFilters = build_offer_filters(
        pSearch=q,
        pSource=source,
        pContract=contract,
        pRemote=remote,
        pMinNetSalary=parse_amount(min_salary),
        pNewOnly=bool(new),
        pStatus=status,
        pNow=vNow,
    )

    vOffers = get_offers(pDatabaseFile, pLimit=MAX_DISPLAYED_OFFERS + 1, **vFilters)

    vContext = {
        "active_page": "offers",
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
        "filters": {
            "q": q,
            "source": source,
            "contract": contract,
            "remote": remote,
            "min_salary": min_salary,
            "new": new,
            "status": status,
        },
    }

    vTemplate = (
        "_offers_table.html" if request.headers.get("HX-Request") else "offers.html"
    )

    rResponse = templates.TemplateResponse(request, vTemplate, vContext)

    return rResponse


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

    vNewSince = datetime.now() - timedelta(days=NEW_OFFER_DAYS)

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


@app.post("/offer/application", response_class=HTMLResponse)
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
        )

    else:
        delete_application(pDatabaseFile, source, id)

    rResponse = render_application(request, pDatabaseFile, vOffer, "Suivi enregistré")

    return rResponse


@app.post("/offer/follow-up", response_class=HTMLResponse)
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

    record_follow_up(pDatabaseFile, source, id)

    rResponse = render_application(
        request, pDatabaseFile, vOffer, "Relance enregistrée"
    )

    return rResponse


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
            "execution_chart": build_bar_chart(
                [vLabel for vLabel, _ in vExecutionCounts],
                [
                    (
                        "Offres",
                        CHART_PALETTE[0],
                        [vCount for _, vCount in vExecutionCounts],
                    )
                ],
            ),
            "execution_chart_size": EXECUTION_CHART_SIZE,
            "executions": vExecutions,
            "unknown_search": UNKNOWN_SEARCH,
            "tone_icons": TONE_ICONS,
        },
    )

    return rResponse


@app.get("/settings", response_class=HTMLResponse)
def show_settings(request: Request):
    """Affiche le thème, l'état des sources et les informations de l'application."""

    vSources = [
        {
            "label": vDefinition.label,
            "reason": vDefinition.get_unavailability_reason(),
            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            "missing": vDefinition.get_missing_settings(),
        }
        for vDefinition in SOURCES.values()
    ]

    rResponse = templates.TemplateResponse(
        request,
        "settings.html",
        {"active_page": "settings", "sources": vSources, "rules": describe_rules()},
    )

    return rResponse
