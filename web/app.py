"""Application web du tableau de bord des offres d'emploi"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import DATABASE_FILE, NEW_OFFER_DAYS
from job.contract import CONTRACT_TYPES
from job.presentation import (
    FOLLOW_UP_FILTER,
    STATUS_LABELS,
    build_offer_filters,
    format_date,
    format_euros,
    prepare_offer,
    safe_url,
)
from job.sources.registry import SOURCES
from storage.database import initialize_database
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

# Au-delà, l'utilisateur affine sa recherche plutôt que de parcourir la liste.
MAX_DISPLAYED_OFFERS = 300


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

templates = Jinja2Templates(directory=WEB_DIRECTORY / "templates")


templates.env.filters["euros"] = format_euros
templates.env.filters["date_fr"] = format_date
templates.env.filters["safe_url"] = safe_url


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


@app.get("/", response_class=HTMLResponse)
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
