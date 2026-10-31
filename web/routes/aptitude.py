"""Tests de recrutement sur le web : choix, partie chronométrée et résultat"""

import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from job.aptitude import (
    CATEGORIES,
    QUESTIONS_PER_SESSION,
    READY_SCORE,
    SESSION_SECONDS,
    build_aptitude_overview,
    finish_session,
    generate_session,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def check_category(pCategory):
    """Refuse une catégorie inconnue."""

    if pCategory not in CATEGORIES:
        raise HTTPException(status_code=404, detail="Test inconnu.")


def render_aptitude(pRequest, pDatabaseFile, pValues):
    """Affiche la page avec la vue d'ensemble et le contenu demandé."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "aptitude.html",
        {
            "active_page": "aptitude",
            "overview": build_aptitude_overview(pDatabaseFile),
            "ready_score": READY_SCORE,
            "session_seconds": SESSION_SECONDS,
            "question_count": QUESTIONS_PER_SESSION,
            **pValues,
        },
    )

    return rResponse


@router.get("/aptitude", response_class=HTMLResponse)
def show_aptitude(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les catégories et les scores obtenus."""

    rResponse = render_aptitude(request, pDatabaseFile, {})

    return rResponse


@router.get("/aptitude/play", response_class=HTMLResponse)
def play_aptitude(
    request: Request,
    pCategory: str = Query(alias="category"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Tire une partie ; la graine et l'heure de départ partent avec le formulaire."""

    check_category(pCategory)
    # Graine d'une série d'exercices, sans usage cryptographique.
    vSeed = random.randrange(1 << 30)  # nosec B311

    rResponse = render_aptitude(
        request,
        pDatabaseFile,
        {
            "category": pCategory,
            "label": CATEGORIES[pCategory][0],
            "seed": vSeed,
            "started": datetime.now().isoformat(timespec="seconds"),
            "questions": generate_session(pCategory, vSeed),
        },
    )

    return rResponse


@router.post(
    "/aptitude/finish",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
async def finish_aptitude(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Corrige la partie envoyée, l'enregistre et affiche le résultat."""

    vForm = await request.form()
    vCategory = str(vForm.get("category") or "")
    check_category(vCategory)

    try:
        vSeed = int(vForm.get("seed") or "")
        vStarted = datetime.fromisoformat(str(vForm.get("started") or ""))

    except ValueError as vException:
        raise HTTPException(status_code=400, detail="Partie invalide.") from vException

    vAnswers = []

    for vIndex in range(QUESTIONS_PER_SESSION):
        vValue = str(vForm.get(f"answer-{vIndex}") or "")
        vAnswers.append(int(vValue) if vValue.isdigit() else None)

    vNow = datetime.now()
    vResult = finish_session(
        pDatabaseFile,
        vCategory,
        vSeed,
        vAnswers,
        (vNow - vStarted).total_seconds(),
        vNow,
    )

    rResponse = render_aptitude(request, pDatabaseFile, {"result": vResult})

    return rResponse
