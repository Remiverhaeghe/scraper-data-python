"""Pages des défis de programmation"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from markupsafe import Markup

from job.challenges import (
    build_challenge_list,
    build_challenge_view,
    get_challenge,
    get_challenge_input,
    submit_answer,
)
from utils.markdown import render_markdown
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def render_challenges(
    pRequest, pDatabaseFile, pChallengeId=None, pHints=0, pMessage=None, pStatusCode=200
):
    """Affiche la liste des défis, avec le défi choisi et le résultat d'une réponse."""

    vNow = datetime.now()
    vView = (
        build_challenge_view(pDatabaseFile, pChallengeId, vNow)
        if pChallengeId
        else None
    )

    rResponse = templates.TemplateResponse(
        pRequest,
        "challenges.html",
        {
            "active_page": "challenges",
            "challenges": build_challenge_list(pDatabaseFile, vNow),
            "view": vView,
            # Textes échappés puis mis en forme par render_markdown : HTML sûr.
            "statements": [
                Markup(render_markdown(vStatement))  # nosec B704
                for vStatement in (vView["statements"] if vView else ())
            ],
            "note": Markup(
                render_markdown(vView["note"] if vView else "")
            ),  # nosec B704
            "hints": vView["hints"][: max(0, pHints)] if vView else (),
            "hint_count": max(0, pHints),
            "message": pMessage,
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/challenges", response_class=HTMLResponse)
def show_challenges(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche la liste des défis de programmation."""

    rResponse = render_challenges(request, pDatabaseFile)

    return rResponse


@router.get("/challenges/{pChallengeId}", response_class=HTMLResponse)
def show_challenge(
    request: Request,
    pChallengeId: str,
    pHints: int = Query(0, alias="hints"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche un défi : énoncé, exemple, données et réponse."""

    if get_challenge(pChallengeId) is None:
        raise HTTPException(status_code=404, detail="Défi introuvable.")

    rResponse = render_challenges(request, pDatabaseFile, pChallengeId, pHints)

    return rResponse


@router.get("/challenges/{pChallengeId}/input")
def download_challenge_input(
    pChallengeId: str, pDatabaseFile: str = Depends(get_database_file)
):
    """Télécharge les données personnelles d'un défi."""

    if get_challenge(pChallengeId) is None:
        raise HTTPException(status_code=404, detail="Défi introuvable.")

    rResponse = PlainTextResponse(
        get_challenge_input(pDatabaseFile, pChallengeId, datetime.now()),
        headers={"Content-Disposition": f'attachment; filename="{pChallengeId}.txt"'},
    )

    return rResponse


@router.post(
    "/challenges/{pChallengeId}/answer",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def answer_challenge(
    request: Request,
    pChallengeId: str,
    pPart: int = Form(1, alias="part"),
    pAnswer: str = Form("", alias="answer"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Vérifie la réponse proposée à une partie de défi."""

    if get_challenge(pChallengeId) is None:
        raise HTTPException(status_code=404, detail="Défi introuvable.")

    try:
        _, vMessage, vTone = submit_answer(
            pDatabaseFile, pChallengeId, pPart, pAnswer, datetime.now()
        )

    except ValueError as vException:
        rResponse = render_challenges(
            request,
            pDatabaseFile,
            pChallengeId,
            pMessage=(str(vException), "warning"),
            pStatusCode=400,
        )

    else:
        rResponse = render_challenges(
            request, pDatabaseFile, pChallengeId, pMessage=(vMessage, vTone)
        )

    return rResponse
