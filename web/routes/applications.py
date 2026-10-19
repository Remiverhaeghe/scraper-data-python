"""Pages des candidatures : suivi par étape, statut et agenda"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from job.application_tracking import (
    BOARD_STATUSES,
    build_application_statistics,
    build_board,
    get_week_follow_ups,
    mark_followed_up,
)
from job.calendar import build_calendar
from job.notification import describe_follow_up
from job.presentation import STATUS_LABELS
from storage.job_applications import get_application, update_application_status
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


@router.get("/applications", response_class=HTMLResponse)
def show_applications(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Affiche les candidatures par étape et leurs taux de réponse."""

    rResponse = templates.TemplateResponse(
        request,
        "applications.html",
        {
            "active_page": "applications",
            "board": build_board(pDatabaseFile, datetime.now()),
            "follow_ups": [
                {**vFollowUp, "detail": describe_follow_up(vFollowUp)}
                for vFollowUp in get_week_follow_ups(pDatabaseFile, datetime.now())
            ],
            "statistics": build_application_statistics(pDatabaseFile),
            "board_statuses": BOARD_STATUSES,
            "statuses": STATUS_LABELS,
        },
    )

    return rResponse


@router.get("/applications/calendar.ics")
def download_calendar(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge les relances et entretiens au format agenda (.ics)."""

    rResponse = Response(
        build_calendar(pDatabaseFile, datetime.now()),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="candidatures.ics"'},
    )

    return rResponse


@router.post("/applications/status", dependencies=[Depends(require_csrf)])
def change_application_status(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pStatus: str = Form(alias="status"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Déplace une candidature dans la colonne de son nouveau statut."""

    if pStatus not in BOARD_STATUSES:
        raise HTTPException(status_code=400, detail="Statut de candidature invalide.")

    update_application_status(pDatabaseFile, pSource, pSourceId, pStatus)

    rResponse = RedirectResponse(
        router.url_path_for("show_applications"), status_code=303
    )

    return rResponse


@router.post("/applications/follow-up", dependencies=[Depends(require_csrf)])
def mark_follow_up_done(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Note une relance faite aujourd'hui et programme la suivante."""

    if get_application(pDatabaseFile, pSource, pSourceId) is None:
        raise HTTPException(status_code=400, detail="Aucun suivi pour cette offre")

    mark_followed_up(pDatabaseFile, pSource, pSourceId, datetime.now())

    rResponse = RedirectResponse(
        router.url_path_for("show_applications"), status_code=303
    )

    return rResponse
