"""Pages du bac à sable Git"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from markupsafe import Markup

from job.git_levels import (
    build_level_list,
    group_levels,
    build_level_view,
    get_level,
    run_level_command,
)
from job.git_sandbox import SUPPORTED_COMMANDS
from utils.markdown import render_markdown
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


# Graphes SVG d'un niveau Git, affichés tels quels
GIT_GRAPHS = ("graph", "goal", "server", "goal_server")


def render_git(
    pRequest, pDatabaseFile, pLevelId=None, pHistory=(), pMessage=None, pStatusCode=200
):
    """Affiche les niveaux Git, avec le niveau choisi après les commandes jouées."""

    vView = build_level_view(pLevelId, pHistory) if pLevelId else None

    rResponse = templates.TemplateResponse(
        pRequest,
        "git.html",
        {
            "active_page": "git",
            "level_groups": group_levels(build_level_list(pDatabaseFile)),
            "view": vView,
            "commands": SUPPORTED_COMMANDS,
            # SVG construit par job/git_graph.py, textes échappés : HTML sûr.
            **{
                vKey: Markup(vView[vKey]) if vView else ""  # nosec B704
                for vKey in GIT_GRAPHS
            },
            "intro": Markup(
                render_markdown(vView["intro"] if vView else "")
            ),  # nosec B704
            "message": pMessage,
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/git", response_class=HTMLResponse)
def show_git(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche la liste des niveaux du bac à sable Git."""

    rResponse = render_git(request, pDatabaseFile)

    return rResponse


@router.get("/git/{pLevelId}", response_class=HTMLResponse)
def show_git_level(
    request: Request, pLevelId: str, pDatabaseFile: str = Depends(get_database_file)
):
    """Affiche un niveau Git dans son état de départ."""

    if get_level(pLevelId) is None:
        raise HTTPException(status_code=404, detail="Niveau introuvable.")

    rResponse = render_git(request, pDatabaseFile, pLevelId)

    return rResponse


@router.post(
    "/git/{pLevelId}/command",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def run_git_command(
    request: Request,
    pLevelId: str,
    pHistory: list[str] = Form([], alias="history"),
    pCommand: str = Form("", alias="command"),
    pAction: str = Form("run", alias="action"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Joue une commande, ou annule la dernière, dans un niveau Git."""

    if get_level(pLevelId) is None:
        raise HTTPException(status_code=404, detail="Niveau introuvable.")

    try:
        if pAction == "undo":
            vHistory, vMessage = pHistory[:-1], None
        else:
            vHistory, vText, vTone = run_level_command(
                pDatabaseFile, pLevelId, pHistory, pCommand, datetime.now()
            )
            vMessage = (vText, vTone)

        rResponse = render_git(request, pDatabaseFile, pLevelId, vHistory, vMessage)

    except ValueError as vException:
        rResponse = render_git(
            request,
            pDatabaseFile,
            pLevelId,
            pMessage=(str(vException), "warning"),
            pStatusCode=400,
        )

    return rResponse
