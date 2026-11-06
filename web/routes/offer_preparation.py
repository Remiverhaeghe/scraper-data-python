"""Préparation d'un entretien : mission, négociation et fiche imprimable"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse


from job.interview_mission import build_mission, set_step
from job.salary_negotiation import (
    build_negotiation_view,
    play_negotiation,
    start_negotiation,
)
from job.presentation import clean_missing_values
from job.preparation_sheet import build_preparation_sheet
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates
from web.routes.offer_detail import build_preparation, get_existing_offer

router = APIRouter()


@router.post(
    "/offer/mission", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def update_mission_step(
    request: Request,
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pStep: str = Form(alias="step"),
    pDone: bool = Form(False, alias="done"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Coche ou décoche une étape de la mission d'entretien, puis la réaffiche."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vPreparation = build_preparation(pDatabaseFile, vOffer)

    if vPreparation is None:
        raise HTTPException(status_code=400, detail="Complétez d'abord votre profil.")

    try:
        set_step(pDatabaseFile, vOffer, pStep, pDone)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = templates.TemplateResponse(
        request,
        "_interview_mission.html",
        {
            "offer": vOffer,
            "mission": build_mission(
                pDatabaseFile, vOffer, vPreparation["match"]["missing"]
            ),
        },
    )

    return rResponse


def render_negotiation(pRequest, pDatabaseFile, pOffer, pError=""):
    """Réaffiche la carte du jeu de négociation."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "_negotiation.html",
        {
            "offer": pOffer,
            "negotiation_game": {
                **build_negotiation_view(pDatabaseFile),
                "error": pError,
            },
        },
    )

    return rResponse


@router.post(
    "/offer/negotiation/start",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def start_salary_negotiation(
    request: Request,
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Commence une partie de négociation sur le marché de l'offre."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    try:
        start_negotiation(pDatabaseFile, vOffer)

    except ValueError as vException:
        return render_negotiation(request, pDatabaseFile, vOffer, str(vException))

    rResponse = render_negotiation(request, pDatabaseFile, vOffer)

    return rResponse


@router.post(
    "/offer/negotiation/play",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def play_salary_negotiation(
    request: Request,
    pChoice: str = Form(alias="choice"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Joue une réponse de la négociation en cours."""

    try:
        vGame = play_negotiation(pDatabaseFile, pChoice)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = render_negotiation(
        request,
        pDatabaseFile,
        {"source": vGame["source"], "source_id": vGame["source_id"]},
    )

    return rResponse


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
