"""Suivi d'une offre : candidature, relance, journal d'entretien et pièces jointes"""

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from job.interview_journal import record_interview
from job.presentation import STATUS_LABELS
from job.settings import load_settings
from storage.attachments import (
    MAX_ATTACHMENT_BYTES,
    add_attachment,
    delete_attachment,
    get_attachment,
)
from storage.interview_notes import get_interview_notes
from storage.job_applications import (
    APPLICATION_STATUSES,
    delete_application,
    get_application,
    record_follow_up,
    save_application,
)
from web.dependencies import get_database_file, require_csrf
from web.forms import parse_date
from web.rendering import get_message_tone, templates
from web.routes.offers import build_offer_url, get_existing_offer

router = APIRouter()


def render_application(pRequest, pDatabaseFile, pOffer, pMessage=None):
    """Affiche le bloc de suivi d'une offre."""

    vApplication = get_application(pDatabaseFile, pOffer["source"], pOffer["source_id"])

    rResponse = templates.TemplateResponse(
        pRequest,
        "_application.html",
        {
            "offer": pOffer,
            "application": vApplication,
            "statuses": STATUS_LABELS,
            "message": pMessage,
        },
    )

    return rResponse


@router.post(
    "/offer/application",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_application(
    request: Request,
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pStatus: str = Form("", alias="status"),
    pFollowUpDate: str = Form("", alias="follow_up_date"),
    pNotes: str = Form("", alias="notes"),
    pInterviewAt: str = Form("", alias="interview_at"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le suivi d'une offre, ou le supprime si aucun statut n'est choisi."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    if pStatus and pStatus not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")

    if pStatus:
        save_application(
            pDatabaseFile,
            pSource,
            pSourceId,
            pStatus,
            pFollowUpDate=parse_date(pFollowUpDate),
            pNotes=pNotes.strip(),
            pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
            pInterviewAt=parse_date(pInterviewAt, "%Y-%m-%dT%H:%M"),
        )

    else:
        delete_application(pDatabaseFile, pSource, pSourceId)

    rResponse = render_application(request, pDatabaseFile, vOffer, "Suivi enregistré")

    return rResponse


@router.post(
    "/offer/follow-up",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def add_follow_up(
    request: Request,
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre une relance effectuée aujourd'hui."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)

    if get_application(pDatabaseFile, pSource, pSourceId) is None:
        raise HTTPException(status_code=400, detail="Aucun suivi pour cette offre")

    record_follow_up(
        pDatabaseFile,
        pSource,
        pSourceId,
        pFollowUpDays=load_settings(pDatabaseFile)["follow_up_days"],
    )

    rResponse = render_application(
        request, pDatabaseFile, vOffer, "Relance enregistrée"
    )

    return rResponse


@router.post(
    "/offer/interview-note",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def add_interview_journal_note(
    request: Request,
    pSource: str = Form(..., alias="source"),
    pSourceId: str = Form(..., alias="id"),
    pQuestions: str = Form("", alias="questions"),
    pImpressions: str = Form("", alias="impressions"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute une entrée au journal d'entretien et renvoie le bloc mis à jour."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vStatusCode = 200

    try:
        record_interview(
            pDatabaseFile, pSource, pSourceId, datetime.now(), pQuestions, pImpressions
        )

    except ValueError as vException:
        vMessage, vStatusCode = str(vException), 400

    else:
        vMessage = "Entrée ajoutée au journal."

    rResponse = templates.TemplateResponse(
        request,
        "_interview_journal.html",
        {
            "offer": vOffer,
            "interview_notes": get_interview_notes(pDatabaseFile, pSource, pSourceId),
            "journal_message": vMessage,
            "journal_tone": get_message_tone(vStatusCode),
        },
        status_code=vStatusCode,
    )

    return rResponse


@router.post("/offer/attachments", dependencies=[Depends(require_csrf)])
def upload_attachment(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Joint un fichier envoyé à une offre, puis rouvre sa fiche."""

    get_existing_offer(pDatabaseFile, pSource, pSourceId)

    # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
    vContent = pFile.file.read(MAX_ATTACHMENT_BYTES + 1)

    try:
        add_attachment(
            pDatabaseFile, pSource, pSourceId, pFile.filename, vContent, datetime.now()
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(build_offer_url(pSource, pSourceId), status_code=303)

    return rResponse


@router.get("/attachment")
def download_attachment(
    pAttachmentId: int = Query(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Renvoie une pièce jointe en téléchargement, sous son nom d'origine."""

    vAttachment = get_attachment(pDatabaseFile, pAttachmentId)

    if vAttachment is None or not vAttachment["path"].is_file():
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable.")

    # Téléchargé plutôt qu'affiché : un fichier joint n'est jamais interprété
    # par le navigateur comme une page du site.
    rResponse = FileResponse(
        vAttachment["path"],
        filename=vAttachment["file_name"],
        content_disposition_type="attachment",
    )

    return rResponse


@router.post("/attachment/delete", dependencies=[Depends(require_csrf)])
def remove_attachment(
    pAttachmentId: int = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Supprime une pièce jointe puis rouvre la fiche de son offre."""

    vAttachment = get_attachment(pDatabaseFile, pAttachmentId)

    if vAttachment is None:
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable.")

    delete_attachment(pDatabaseFile, pAttachmentId)

    rResponse = RedirectResponse(
        build_offer_url(vAttachment["source"], vAttachment["source_id"]),
        status_code=303,
    )

    return rResponse
