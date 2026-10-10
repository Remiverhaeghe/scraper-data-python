"""Application web du tableau de bord des offres d'emploi"""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import DATABASE_FILE, NEW_OFFER_DAYS
from job.contract import CONTRACT_TYPES
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

# Valeur du filtre de statut affichant les candidatures à relancer
FOLLOW_UP_FILTER = "FOLLOW_UP"


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


def format_euros(pAmount):
    """Formate un montant en euros avec un espace comme séparateur de milliers."""

    rText = ""

    if pAmount is not None:
        rText = f"{round(pAmount):,} €".replace(",", " ")

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


templates.env.filters["euros"] = format_euros
templates.env.filters["date_fr"] = format_date
templates.env.filters["safe_url"] = safe_url


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

    # Les offres ignorées restent masquées sauf si on les demande explicitement.
    vFilters = {
        "pSearch": q.strip() or None,
        "pSource": source if source in SOURCES else None,
        "pContract": contract if contract in CONTRACT_TYPES else None,
        "pRemote": bool(remote),
        "pMinNetSalary": parse_amount(min_salary),
        "pSeenSince": vNewSince if new else None,
        "pStatus": status if status in APPLICATION_STATUSES else None,
        "pFollowUpBefore": vNow if status == FOLLOW_UP_FILTER else None,
        "pHideIgnored": True,
    }

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
