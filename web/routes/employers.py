"""Employeurs industriels de la région et candidatures spontanées, avec leur carte"""

from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.geocoding import load_home
from job.local_employers import (
    build_employers_view,
    fetch_local_employers,
    follow_employer,
    record_spontaneous,
)
from job.spontaneous_applications import STATUSES, get_contact_tone
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()

MAX_ROWS = 300


def build_map_points(pEmployers):
    """Retourne les employeurs placés sur la carte, colorés selon leur candidature."""

    rPoints = [
        {
            "title": vEmployer["name"],
            "url": vEmployer["page"],
            "detail": " · ".join(
                vPart
                for vPart in (
                    vEmployer["sector"],
                    vEmployer.get("headcount"),
                    f"{vEmployer['city']}, {vEmployer['distance_km']} km",
                    (vEmployer.get("spontaneous") or {}).get("status_label"),
                )
                if vPart
            ),
            "score": None,
            "tone": get_contact_tone(vEmployer.get("spontaneous")),
            "latitude": vEmployer["latitude"],
            "longitude": vEmployer["longitude"],
        }
        for vEmployer in pEmployers
        if vEmployer.get("latitude") is not None
    ]

    return rPoints


def render_employers(
    pRequest, pDatabaseFile, pSector="", pDistance=0, pContact="", pMessage=None
):
    """Affiche la liste filtrée, la carte et le résultat d'une action."""

    vView = build_employers_view(pDatabaseFile, pSector, pDistance or None, pContact)
    vHome = load_home(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        pRequest,
        "employers.html",
        {
            "active_page": "market",
            "view": {**vView, "employers": vView["employers"][:MAX_ROWS]},
            "shown": len(vView["employers"]),
            "sector": pSector,
            "distance": pDistance,
            "contact": pContact,
            "statuses": STATUSES,
            "message": pMessage,
            "map_points": build_map_points(vView["employers"]),
            # Le libellé et la position suffisent : l'adresse ne quitte pas le serveur
            "map_home": (
                {vKey: vHome[vKey] for vKey in ("label", "latitude", "longitude")}
                if vHome
                else None
            ),
        },
    )

    return rResponse


@router.get("/employers", response_class=HTMLResponse)
def show_employers(
    request: Request,
    pSector: str = Query("", alias="sector"),
    pDistance: int = Query(0, alias="distance", ge=0, le=1000),
    pContact: str = Query("", alias="contact"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les employeurs, filtrés par secteur, distance et candidature."""

    rResponse = render_employers(request, pDatabaseFile, pSector, pDistance, pContact)

    return rResponse


@router.post(
    "/employers/update",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_employers(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Met la liste à jour depuis l'annuaire public (une vingtaine de secondes)."""

    try:
        vCount = fetch_local_employers(pDatabaseFile, datetime.now())
        vMessage = (f"{vCount} employeur(s) trouvé(s).", "success")

    except ValueError as vError:
        vMessage = (str(vError), "warning")

    rResponse = render_employers(request, pDatabaseFile, pMessage=vMessage)

    return rResponse


@router.post("/employers/spontaneous", dependencies=[Depends(require_csrf)])
def record_spontaneous_application(
    pSiren: str = Form(alias="siren"),
    pStatus: str = Form("", alias="status"),
    pSector: str = Form("", alias="sector"),
    pDistance: int = Form(0, alias="distance"),
    pContact: str = Form("", alias="contact"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Note l'étape d'une candidature spontanée, puis revient à la liste filtrée."""

    try:
        record_spontaneous(pDatabaseFile, pSiren, pStatus)

    except ValueError as vError:
        raise HTTPException(status_code=400, detail=str(vError)) from vError

    rResponse = RedirectResponse(
        router.url_path_for("show_employers")
        + "?"
        + urlencode({"sector": pSector, "distance": pDistance, "contact": pContact})
        + "#employers-list",
        status_code=303,
    )

    return rResponse


@router.post("/employers/follow", dependencies=[Depends(require_csrf)])
def follow_local_employer(
    pSiren: str = Form(alias="siren"),
    pSector: str = Form("", alias="sector"),
    pDistance: int = Form(0, alias="distance"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Suit un employeur : ses nouvelles offres seront signalées."""

    try:
        follow_employer(pDatabaseFile, pSiren)

    except ValueError:
        pass

    rResponse = RedirectResponse(
        router.url_path_for("show_employers")
        + "?"
        + urlencode({"sector": pSector, "distance": pDistance}),
        status_code=303,
    )

    return rResponse
