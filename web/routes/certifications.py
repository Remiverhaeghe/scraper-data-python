"""Page Certifications : celles que demandent les offres, celles du candidat"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from job.certifications import (
    CATEGORIES,
    CERTIFICATIONS,
    DETAIL_FIELDS,
    DOCUMENT_SOURCE,
    build_overview,
    save_details,
    save_owned,
)
from job.statistics import load_scored_offers
from storage.attachments import (
    ALLOWED_EXTENSIONS,
    MAX_ATTACHMENT_BYTES,
    add_attachment,
    get_attachments,
)
from web.dependencies import get_database_file, require_csrf
from web.forms import parse_date
from web.rendering import templates

router = APIRouter()


def build_certification_url(pId):
    """Retourne l'adresse de la page, ouverte sur une certification."""

    rUrl = f"/certifications#cert-{pId}"

    return rUrl


@router.get("/certifications", response_class=HTMLResponse)
def show_certifications(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les certifications citées par les offres et celles du candidat."""

    vOverview = build_overview(
        pDatabaseFile, load_scored_offers(pDatabaseFile, datetime.now()), date.today()
    )

    rResponse = templates.TemplateResponse(
        request,
        "certifications.html",
        {
            "active_page": "certifications",
            "overview": vOverview,
            "categories": CATEGORIES,
            "documents": {
                vRow["id"]: get_attachments(pDatabaseFile, DOCUMENT_SOURCE, vRow["id"])
                for vRow in vOverview["rows"]
                if vRow["documents"]
            },
            "attachment_extensions": ALLOWED_EXTENSIONS,
            "today": date.today().isoformat(),
        },
    )

    return rResponse


@router.post("/certifications/save", dependencies=[Depends(require_csrf)])
async def save_certification(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre l'obtention et les informations d'une certification."""

    vForm = await request.form()
    vId = str(vForm.get("id") or "")
    vDate = parse_date(str(vForm.get("obtained") or ""))
    vObtained = (
        (vDate.date() if vDate else date.today()) if vForm.get("owned") else None
    )

    if vObtained is not None and vObtained > date.today():
        raise HTTPException(
            status_code=400, detail="La date d'obtention est dans le futur."
        )

    try:
        save_details(
            pDatabaseFile,
            vId,
            {vField: str(vForm.get(vField) or "") for vField in DETAIL_FIELDS},
        )
        save_owned(pDatabaseFile, vId, vObtained)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(build_certification_url(vId), status_code=303)

    return rResponse


@router.post("/certifications/documents", dependencies=[Depends(require_csrf)])
def upload_certification_document(
    pId: str = Form(alias="id"),
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Joint un certificat ou une attestation à une certification."""

    if pId not in CERTIFICATIONS:
        raise HTTPException(status_code=404, detail="Certification inconnue.")

    # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
    vContent = pFile.file.read(MAX_ATTACHMENT_BYTES + 1)

    try:
        add_attachment(
            pDatabaseFile,
            DOCUMENT_SOURCE,
            pId,
            pFile.filename,
            vContent,
            datetime.now(),
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(build_certification_url(pId), status_code=303)

    return rResponse
