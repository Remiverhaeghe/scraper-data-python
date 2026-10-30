"""Niveaux Maven et Docker sur le web : fichier, commande, console"""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.devops_levels import (
    MAX_COMMAND_LENGTH,
    MAX_FILE_LENGTH,
    build_devops_overview,
    get_level_view,
    load_levels,
    reset_level,
    run_level_command,
)
from job.progress import XP_RULES
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def check_level(pLevelId):
    """Refuse un identifiant de niveau inconnu."""

    if pLevelId not in load_levels():
        raise HTTPException(status_code=404, detail="Niveau inconnu.")


def render_devops(pRequest, pDatabaseFile, pValues):
    """Affiche la page avec les niveaux par série et le niveau ouvert."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "devops.html",
        {
            "active_page": "devops",
            "overview": build_devops_overview(pDatabaseFile),
            "level_xp": XP_RULES["devops_level"][1],
            "max_command_length": MAX_COMMAND_LENGTH,
            "max_file_length": MAX_FILE_LENGTH,
            **pValues,
        },
    )

    return rResponse


@router.get("/devops", response_class=HTMLResponse)
def show_devops(
    request: Request,
    pLevelId: str = Query("", alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les niveaux, et le niveau choisi là où on l'avait laissé."""

    vValues = {}

    if pLevelId:
        check_level(pLevelId)
        vValues = {"view": get_level_view(pDatabaseFile, pLevelId)}

    rResponse = render_devops(request, pDatabaseFile, vValues)

    return rResponse


@router.post(
    "/devops/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def run_devops(
    request: Request,
    pLevelId: str = Form(alias="level"),
    pFile: str = Form("", alias="file", max_length=MAX_FILE_LENGTH),
    pCommand: str = Form("", alias="command", max_length=MAX_COMMAND_LENGTH),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Exécute la commande sur le fichier envoyé et affiche la console."""

    check_level(pLevelId)
    vRun = run_level_command(
        pDatabaseFile, pLevelId, pFile.replace("\r\n", "\n"), pCommand
    )

    rResponse = render_devops(
        request,
        pDatabaseFile,
        {"view": get_level_view(pDatabaseFile, pLevelId), "run": vRun},
    )

    return rResponse


@router.post("/devops/reset", dependencies=[Depends(require_csrf)])
def reset_devops(
    pLevelId: str = Form(alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Remet le niveau à son départ et le rouvre."""

    check_level(pLevelId)
    reset_level(pDatabaseFile, pLevelId)

    rResponse = RedirectResponse(
        router.url_path_for("show_devops")
        + "?"
        + urlencode({"level": pLevelId})
        + "#level",
        status_code=303,
    )

    return rResponse
