"""API JSON de l'application mobile de révision

Toutes les routes exigent le jeton créé dans les Paramètres, transmis dans
l'en-tête « Authorization: Bearer <jeton> ». Aucune session ni cookie : le
téléphone n'a donc pas besoin de la protection CSRF des formulaires.
"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response

from config import APPLICATION_NAME
from job.mobile_sync import (
    API_PREFIX,
    API_VERSION,
    build_progress,
    build_quiz_package,
    check_mobile_token,
    sync_answers,
)
from utils.logger import get_logger
from web.dependencies import get_database_file

logger = get_logger(__name__)

router = APIRouter(prefix=API_PREFIX)


def require_api_token(
    pAuthorization: str = Header("", alias="Authorization"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Refuse une requête sans le jeton de l'application mobile."""

    vScheme, _, vToken = pAuthorization.partition(" ")

    if vScheme.lower() != "bearer" or not check_mobile_token(pDatabaseFile, vToken):
        # Le jeton reçu n'est pas journalisé : il pourrait être presque juste.
        logger.warning("Requête de l'application mobile refusée : jeton invalide")

        raise HTTPException(
            status_code=401,
            detail="Jeton de l'application mobile absent ou invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/ping")
def ping():
    """Signale le serveur à l'application mobile qui le cherche sur le Wi-Fi.

    Sans jeton : la réponse ne contient que le nom de l'application et la version
    de l'API, aucune donnée.
    """

    rAnswer = {"application": APPLICATION_NAME, "api_version": API_VERSION}

    return rAnswer


@router.get("/quiz", dependencies=[Depends(require_api_token)])
def download_quiz(
    pResponse: Response,
    pVersion: str = Header("", alias="If-None-Match"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Renvoie tout le contenu de révision, ou 304 si le téléphone l'a déjà."""

    vPackage = build_quiz_package(pDatabaseFile, datetime.now())
    vETag = f'"{vPackage["version"]}"'

    if pVersion == vETag:
        rResponse = Response(status_code=304, headers={"ETag": vETag})
    else:
        pResponse.headers["ETag"] = vETag
        rResponse = vPackage

    return rResponse


@router.get("/progress", dependencies=[Depends(require_api_token)])
def download_progress(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie la progression : état de chaque question et chiffres d'ensemble."""

    rProgress = build_progress(pDatabaseFile, datetime.now())

    return rProgress


@router.post("/answers", dependencies=[Depends(require_api_token)])
def upload_answers(
    pAnswers: list = Body(..., embed=True, alias="answers"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre les réponses faites hors ligne, puis renvoie la progression."""

    vNow = datetime.now()

    try:
        vReport = sync_answers(pDatabaseFile, pAnswers, vNow)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResult = {**vReport, "progress": build_progress(pDatabaseFile, vNow)}

    return rResult
