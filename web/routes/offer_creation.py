"""Saisie manuelle d'une offre, ajout par lien et import d'un fichier"""

from datetime import datetime
import io
from pathlib import Path


from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse


from job.contract import CONTRACT_TYPES
from job.manual_offers import (
    IMPORT_FORMATS,
    MAX_IMPORT_BYTES,
    add_manual_offer,
    describe_import,
    import_offers_file,
    list_import_problems,
)
from job.offer_from_link import add_offer_from_link
from job.presentation import MANUAL_SOURCE
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates
from web.routes.offer_detail import build_offer_url

router = APIRouter()


def render_new_offer(pRequest, pFields=None, pMessage=None, pReport=None, pStatus=200):
    """Affiche la saisie manuelle et l'import d'offres, avec le dernier résultat."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "offer_new.html",
        {
            "active_page": "offers",
            "fields": pFields or {},
            "contracts": CONTRACT_TYPES,
            "message": pMessage,
            "report": pReport,
            "import_summary": describe_import(pReport) if pReport else None,
            "import_problems": list_import_problems(pReport) if pReport else [],
            "import_formats": IMPORT_FORMATS,
        },
        status_code=pStatus,
    )

    return rResponse


@router.get("/offers/new", response_class=HTMLResponse)
def show_new_offer(request: Request):
    """Affiche la saisie manuelle et l'import d'offres."""

    rResponse = render_new_offer(request)

    return rResponse


@router.post(
    "/offers/new", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def create_offer(
    request: Request,
    pTitle: str = Form("", alias="title"),
    pCompany: str = Form("", alias="company"),
    pUrl: str = Form("", alias="url"),
    pDescription: str = Form("", alias="description"),
    pLocation: str = Form("", alias="location"),
    pContract: str = Form("", alias="contract"),
    pSalary: str = Form("", alias="salary_label"),
    pRemote: str = Form("", alias="remote"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée une offre saisie à la main, ou réaffiche le formulaire avec l'erreur."""

    vFields = {
        "title": pTitle,
        "company": pCompany,
        "url": pUrl,
        "description": pDescription,
        "location": pLocation,
        "contract": pContract,
        "salary_label": pSalary,
        "remote": "oui" if pRemote else None,
    }

    try:
        vSourceId = add_manual_offer(pDatabaseFile, vFields, datetime.now())

    except ValueError as vException:
        rResponse = render_new_offer(request, vFields, str(vException), pStatus=400)

    else:
        rResponse = RedirectResponse(
            build_offer_url(MANUAL_SOURCE, vSourceId), status_code=303
        )

    return rResponse


@router.post(
    "/offers/from-link",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def create_offer_from_link(
    request: Request,
    pUrl: str = Form("", alias="url"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée l'offre décrite par la page d'une annonce, ou explique pourquoi non."""

    try:
        vSourceId = add_offer_from_link(pDatabaseFile, pUrl, datetime.now())

    except ValueError as vException:
        rResponse = render_new_offer(request, None, str(vException), pStatus=400)

    else:
        rResponse = RedirectResponse(
            build_offer_url(MANUAL_SOURCE, vSourceId), status_code=303
        )

    return rResponse


@router.post(
    "/offers/import",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def import_offers(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Importe les offres d'un fichier envoyé et affiche le bilan."""

    # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
    vContent = pFile.file.read(MAX_IMPORT_BYTES + 1)
    vSuffix = Path(pFile.filename or "").suffix

    try:
        if len(vContent) > MAX_IMPORT_BYTES:
            raise ValueError(
                f"Fichier trop volumineux : {MAX_IMPORT_BYTES // (1024 * 1024)} Mo "
                "au maximum."
            )

        vReport = import_offers_file(
            pDatabaseFile, io.BytesIO(vContent), vSuffix, datetime.now()
        )

    except ValueError as vException:
        rResponse = render_new_offer(request, pMessage=str(vException), pStatus=400)

    else:
        rResponse = render_new_offer(request, pReport=vReport)

    return rResponse
