"""Simulateur d'automate sur le web : niveaux, programme, vérification"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from job.ladder import LadderError, parse_program, render_svg
from job.ladder_game import (
    build_ladder_overview,
    get_names,
    load_levels,
    render_chronogram,
    run_level,
    save_attempt,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()

MAX_PROGRAM_LENGTH = 4000


def check_level(pLevelId):
    """Retourne un niveau ; refuse un identifiant inconnu."""

    rLevel = load_levels().get(pLevelId)

    if rLevel is None:
        raise HTTPException(status_code=404, detail="Niveau inconnu.")

    return rLevel


def draw_program(pLevel, pProgram):
    """Retourne le ladder du programme en SVG, ou une chaîne vide s'il est faux."""

    try:
        vRungs = parse_program(pProgram, set(get_names(pLevel, "input")))

    except LadderError:
        return ""

    rSvg = render_svg(vRungs) if vRungs else ""

    return rSvg


def render_ladder(pRequest, pDatabaseFile, pValues):
    """Affiche la page avec la liste des niveaux et le niveau demandé."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "ladder.html",
        {
            "active_page": "ladder",
            "overview": build_ladder_overview(pDatabaseFile),
            "max_program_length": MAX_PROGRAM_LENGTH,
            **pValues,
        },
    )

    return rResponse


@router.get("/ladder", response_class=HTMLResponse)
def show_ladder(
    request: Request,
    pLevelId: str = Query("", alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les niveaux, et le niveau choisi avec le dernier programme essayé."""

    vValues = {}

    if pLevelId:
        vLevel = check_level(pLevelId)
        vProgram = next(
            vRow["program"]
            for vRow in build_ladder_overview(pDatabaseFile)["rows"]
            if vRow["id"] == pLevelId
        )
        vValues = {
            "level": vLevel,
            "program": vProgram,
            "ladder_svg": draw_program(vLevel, vProgram),
        }

    rResponse = render_ladder(request, pDatabaseFile, vValues)

    return rResponse


@router.post(
    "/ladder/check", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def check_ladder(
    request: Request,
    pLevelId: str = Form(alias="level"),
    pProgram: str = Form("", alias="program", max_length=MAX_PROGRAM_LENGTH),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Exécute le scénario de test du niveau et affiche le résultat."""

    vLevel = check_level(pLevelId)
    vRun = run_level(vLevel, pProgram)
    vFirst = False

    if not vRun["error"]:
        vFirst = save_attempt(pDatabaseFile, pLevelId, pProgram, vRun["passed"])

    rResponse = render_ladder(
        request,
        pDatabaseFile,
        {
            "level": vLevel,
            "program": pProgram,
            "run": vRun,
            "first": vFirst,
            "ladder_svg": draw_program(vLevel, pProgram),
            "chart_svg": (
                ""
                if vRun["error"]
                else render_chronogram(
                    vRun["signals"], vRun["samples"], set(get_names(vLevel, "input"))
                )
            ),
        },
    )

    return rResponse
