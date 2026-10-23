"""Pages des candidatures : suivi par étape, statut et agenda"""

import imaplib
from datetime import datetime
from html import escape

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from job.application_replies import (
    apply_reply,
    check_replies,
    mark_reply_handled,
)
from job.application_tracking import (
    BOARD_STATUSES,
    build_application_statistics,
    build_board,
    get_week_follow_ups,
    mark_followed_up,
)
from job.calendar import build_calendar
from job.followed_availability import count_alerts
from job.notification import describe_follow_up
from job.presentation import STATUS_LABELS
from storage.job_applications import get_application, update_application_status
from web.dependencies import get_database_file, require_csrf
from utils.logger import get_logger
from web.rendering import templates

router = APIRouter()

logger = get_logger(__name__)


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


@router.post(
    "/applications/replies",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def read_replies(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Lit les réponses récentes de Gmail et propose un statut pour chaque candidature."""

    vContext = {"replies": [], "statuses": STATUS_LABELS, "message": None}

    try:
        vContext["replies"] = check_replies(pDatabaseFile, datetime.now())

    except ValueError as vException:
        vContext.update(message=str(vException), tone="warning")

    except (OSError, imaplib.IMAP4.error):
        logger.exception("Lecture de Gmail impossible")
        vContext.update(
            message="Gmail injoignable ou mot de passe d'application refusé : "
            "voir les journaux.",
            tone="danger",
        )

    if not vContext["replies"] and vContext["message"] is None:
        vContext.update(
            message="Aucune réponse de recruteur à appliquer sur 30 jours.",
            tone="success",
        )

    rResponse = templates.TemplateResponse(request, "_replies.html", vContext)

    return rResponse


@router.post(
    "/applications/replies/handle",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def handle_reply(
    pAction: str = Form(alias="action"),
    pMessageId: str = Form(alias="message_id"),
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pStatus: str = Form(alias="status"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Applique le statut proposé, ou ignore le message ; remplace sa ligne."""

    if pAction == "apply":
        if pStatus not in STATUS_LABELS:
            raise HTTPException(status_code=400, detail="Statut invalide.")

        apply_reply(
            pDatabaseFile,
            {
                "message_id": pMessageId,
                "source": pSource,
                "source_id": pSourceId,
                "status": pStatus,
            },
            datetime.now(),
        )
        vText = f"Statut « {STATUS_LABELS[pStatus]} » appliqué."
    else:
        mark_reply_handled(pDatabaseFile, pMessageId)
        vText = "Réponse ignorée."

    rResponse = HTMLResponse(f'<p class="muted reply">{escape(vText)}</p>')

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


@router.get("/alerts", response_class=HTMLResponse)
def show_alerts(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie le badge du menu : relances dues et offres suivies retirées."""

    vAlerts = count_alerts(pDatabaseFile, datetime.now())

    rResponse = HTMLResponse(
        f'<span class="badge badge-danger" title="{escape(vAlerts["text"])}">'
        f'{vAlerts["total"]}</span>'
        if vAlerts["total"]
        else ""
    )

    return rResponse
