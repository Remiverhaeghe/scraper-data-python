"""Documents ajustés à une offre : CV, dossier de candidature et lettre"""

from typing import Literal
from urllib.parse import quote


from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import Response


from job.application_dossier import write_dossier_pdf
from job.cv_export import (
    build_file_name,
    build_tailored_cv,
    write_cv_pdf,
    write_docx,
    write_letter_docx,
    write_letter_pdf,
)
from job.geocoding import load_home
from job.profile import is_profile_empty, load_profile
from web.dependencies import get_database_file, require_csrf
from web.routes.offer_detail import get_existing_offer

router = APIRouter()


# Longueur gardée pour une lettre envoyée par le formulaire
MAX_LETTER_LENGTH = 20000


def build_document_response(pContent, pFileName):
    """Retourne un document Word ou PDF à télécharger sous le nom donné."""

    rResponse = Response(
        pContent,
        media_type=(
            "application/pdf"
            if pFileName.endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(pFileName)
        },
    )

    return rResponse


@router.get("/offer/cv")
def download_tailored_cv(
    pSource: str = Query(alias="source"),
    pSourceId: str = Query(alias="id"),
    pFormat: Literal["docx", "pdf"] = Query("docx", alias="format"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Télécharge le CV du profil réordonné pour l'offre, en Word ou en PDF."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vProfile = load_profile(pDatabaseFile)

    if is_profile_empty(vProfile):
        raise HTTPException(status_code=400, detail="Profil vide : rien à exporter.")

    vCv = build_tailored_cv(vProfile, vOffer)

    rResponse = build_document_response(
        write_cv_pdf(vCv) if pFormat == "pdf" else write_docx(vCv),
        build_file_name(vOffer, "CV", f".{pFormat}"),
    )

    return rResponse


@router.post("/offer/dossier", dependencies=[Depends(require_csrf)])
def download_dossier(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pLetter: str = Form("", alias="letter"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Télécharge le dossier de candidature en PDF, avec la lettre modifiée."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vProfile = load_profile(pDatabaseFile)

    if is_profile_empty(vProfile):
        raise HTTPException(status_code=400, detail="Profil vide : rien à exporter.")

    rResponse = build_document_response(
        write_dossier_pdf(
            vProfile,
            vOffer,
            pLetter[:MAX_LETTER_LENGTH] or None,
            load_home(pDatabaseFile),
        ),
        build_file_name(vOffer, "Dossier", ".pdf"),
    )

    return rResponse


@router.post("/offer/letter", dependencies=[Depends(require_csrf)])
def download_letter(
    pSource: str = Form(alias="source"),
    pSourceId: str = Form(alias="id"),
    pLetter: str = Form("", alias="letter"),
    pFormat: Literal["docx", "pdf"] = Form("docx", alias="format"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Télécharge la lettre telle que modifiée dans la page, en Word ou en PDF."""

    vOffer = get_existing_offer(pDatabaseFile, pSource, pSourceId)
    vLetter = pLetter[:MAX_LETTER_LENGTH]

    rResponse = build_document_response(
        write_letter_pdf(vLetter) if pFormat == "pdf" else write_letter_docx(vLetter),
        build_file_name(vOffer, "Lettre", f".{pFormat}"),
    )

    return rResponse
