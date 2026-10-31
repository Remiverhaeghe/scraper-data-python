"""Page des employeurs industriels de la région, tirés de l'annuaire public"""

from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.local_employers import (
    build_employers_view,
    fetch_local_employers,
    follow_employer,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()

MAX_ROWS = 300


def render_employers(pRequest, pDatabaseFile, pSector="", pDistance=0, pMessage=None):
    """Affiche la liste filtrée et le résultat d'une action."""

    vView = build_employers_view(pDatabaseFile, pSector, pDistance or None)

    rResponse = templates.TemplateResponse(
        pRequest,
        "employers.html",
        {
            "active_page": "market",
            "view": {**vView, "employers": vView["employers"][:MAX_ROWS]},
            "shown": len(vView["employers"]),
            "sector": pSector,
            "distance": pDistance,
            "message": pMessage,
        },
    )

    return rResponse


@router.get("/employers", response_class=HTMLResponse)
def show_employers(
    request: Request,
    pSector: str = Query("", alias="sector"),
    pDistance: int = Query(0, alias="distance", ge=0, le=1000),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les employeurs, filtrés par secteur et par distance."""

    rResponse = render_employers(request, pDatabaseFile, pSector, pDistance)

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
