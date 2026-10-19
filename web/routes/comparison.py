"""Comparaison de quelques offres côte à côte"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.offer_comparison import build_comparison, clear_comparison, toggle_comparison
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates
from web.routes.offers import build_offer_url, get_existing_offer

router = APIRouter()


@router.post("/offer/compare", dependencies=[Depends(require_csrf)])
def toggle_offer_comparison(
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute l'offre à la comparaison, ou l'en retire, puis revient à sa fiche."""

    get_existing_offer(pDatabaseFile, pSource, pSourceId)
    toggle_comparison(pDatabaseFile, pSource, pSourceId)

    rResponse = RedirectResponse(build_offer_url(pSource, pSourceId), status_code=303)

    return rResponse


@router.get("/compare", response_class=HTMLResponse)
def show_comparison(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les offres comparées côte à côte."""

    rResponse = templates.TemplateResponse(
        request,
        "compare.html",
        {
            "active_page": "offers",
            "comparison": build_comparison(pDatabaseFile, datetime.now()),
        },
    )

    return rResponse


@router.post("/compare/clear", dependencies=[Depends(require_csrf)])
def clear_offer_comparison(pDatabaseFile: str = Depends(get_database_file)):
    """Vide la comparaison, puis revient à la page de comparaison."""

    clear_comparison(pDatabaseFile)

    rResponse = RedirectResponse(
        router.url_path_for("show_comparison"), status_code=303
    )

    return rResponse
