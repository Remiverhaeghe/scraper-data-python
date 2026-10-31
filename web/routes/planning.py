"""Page du planning de la semaine : tâches par jour, déplacement, révisions prévues"""

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from job.weekly_planning import add_revision, build_week, delete_revision, move_item
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def read_day(pText):
    """Lit un jour AAAA-MM-JJ ; lève une erreur 400 s'il est illisible."""

    try:
        rDay = date.fromisoformat(pText)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail="Jour illisible.") from vException

    return rDay


def redirect_to_week(pDay):
    """Revient au planning de la semaine d'un jour."""

    rResponse = RedirectResponse(
        router.url_path_for("show_planning") + f"?week={pDay.isoformat()}",
        status_code=303,
    )

    return rResponse


@router.get("/planning", response_class=HTMLResponse)
def show_planning(
    request: Request,
    pWeek: str = Query("", alias="week"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la semaine demandée, ou la semaine en cours."""

    vDay = read_day(pWeek) if pWeek else date.today()

    rResponse = templates.TemplateResponse(
        request,
        "planning.html",
        {"active_page": "planning", "week": build_week(pDatabaseFile, vDay)},
    )

    return rResponse


@router.post("/planning/move", dependencies=[Depends(require_csrf)])
def move_planning_item(
    request: Request,
    pItem: str = Form(alias="item"),
    pDay: str = Form(alias="day"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Déplace une tâche à un autre jour ; le script du glisser-déposer reçoit 204."""

    vDay = read_day(pDay)

    try:
        move_item(pDatabaseFile, pItem, vDay)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    if request.headers.get("X-Requested-With") == "fetch":
        return Response(status_code=204)

    rResponse = redirect_to_week(vDay)

    return rResponse


@router.post("/planning/revision", dependencies=[Depends(require_csrf)])
def add_planned_revision(
    pDay: str = Form(alias="day"),
    pLabel: str = Form("", alias="label"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Prévoit une séance de révision."""

    vDay = read_day(pDay)

    try:
        add_revision(pDatabaseFile, vDay, pLabel)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = redirect_to_week(vDay)

    return rResponse


@router.post("/planning/revision/delete", dependencies=[Depends(require_csrf)])
def delete_planned_revision(
    pRevision: str = Form(alias="revision"),
    pWeek: str = Form(alias="week"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Retire une séance de révision prévue."""

    delete_revision(pDatabaseFile, pRevision)

    rResponse = redirect_to_week(read_day(pWeek))

    return rResponse
