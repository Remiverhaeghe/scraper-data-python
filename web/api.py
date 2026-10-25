"""API JSON de l'application mobile de révision

Toutes les routes exigent le jeton créé dans les Paramètres, transmis dans
l'en-tête « Authorization: Bearer <jeton> ». Aucune session ni cookie : le
téléphone n'a donc pas besoin de la protection CSRF des formulaires.
"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response

from config import APPLICATION_NAME
from job.application_replies import load_pending_replies
from job.followed_availability import list_withdrawn_offers
from job.interview_simulation import (
    list_themes,
    load_interview_questions,
    record_phone_series,
)
from job.mobile_sync import (
    API_PREFIX,
    API_VERSION,
    build_progress,
    build_quiz_package,
    build_tracking,
    check_mobile_token,
    build_offer_list,
    sync_answers,
    sync_exam_results,
    sync_flags,
    sync_phone_notes,
    sync_status_changes,
)
from job.profile import load_profile
from job.self_assessment import (
    KNOWN_LEVEL,
    MAX_LEVEL,
    WEAK_LEVEL,
    build_grid,
    save_skill_levels,
)
from job.weekly_digest import get_coming_interviews
from utils.logger import get_logger
from web.dependencies import get_database_file

logger = get_logger(__name__)

router = APIRouter(prefix=API_PREFIX)

# Compétences notées envoyées par le téléphone en une fois, au plus
MAX_PHONE_SKILLS = 200


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


@router.post("/exams", dependencies=[Depends(require_api_token)])
def upload_exams(
    pExams: list = Body(..., embed=True, alias="exams"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute à l'historique du PC les examens blancs passés sur le téléphone."""

    try:
        rReport = sync_exam_results(pDatabaseFile, pExams)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    return rReport


@router.post("/flags", dependencies=[Depends(require_api_token)])
def upload_flags(
    pQuestionIds: list = Body(..., embed=True, alias="question_ids"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Retire des tirages les questions signalées depuis le téléphone."""

    try:
        rReport = sync_flags(pDatabaseFile, pQuestionIds)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    return rReport


@router.get("/interview", dependencies=[Depends(require_api_token)])
def download_interview_questions():
    """Renvoie les questions ouvertes de la simulation d'entretien, par thème."""

    rContent = {
        "themes": list_themes(),
        "questions": list(load_interview_questions().values()),
    }

    return rContent


@router.post("/interview", dependencies=[Depends(require_api_token)])
def upload_interview_series(
    pSeries: list = Body(..., embed=True, alias="series"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute à l'historique les séries de simulation faites sur le téléphone."""

    try:
        vCount = record_phone_series(pDatabaseFile, pSeries, datetime.now())

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rReport = {"received": len(pSeries), "recorded": vCount}

    return rReport


@router.get("/skills", dependencies=[Depends(require_api_token)])
def download_skill_grid(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie la grille d'auto-évaluation et ses seuils."""

    rContent = {
        "grid": [
            {"skill": vSkill, "level": vLevel}
            for vSkill, vLevel in build_grid(load_profile(pDatabaseFile))
        ],
        "max_level": MAX_LEVEL,
        "known_level": KNOWN_LEVEL,
        "weak_level": WEAK_LEVEL,
    }

    return rContent


@router.post("/skills", dependencies=[Depends(require_api_token)])
def upload_skill_levels(
    pLevels: dict = Body(..., embed=True, alias="levels"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre la grille d'auto-évaluation saisie sur le téléphone."""

    if len(pLevels) > MAX_PHONE_SKILLS or not all(
        isinstance(vLevel, int) and not isinstance(vLevel, bool)
        for vLevel in pLevels.values()
    ):
        raise HTTPException(status_code=400, detail="Niveaux entiers attendus.")

    try:
        vGrid = save_skill_levels(pDatabaseFile, pLevels)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rReport = {"rated": sum(1 for _, vLevel in vGrid if vLevel)}

    return rReport


@router.get("/interviews", dependencies=[Depends(require_api_token)])
def download_interviews(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie les entretiens des sept prochains jours, pour les rappels du téléphone."""

    rInterviews = {
        "interviews": [
            {
                "title": vInterview["title"],
                "company": vInterview["company"],
                "interview_at": vInterview["interview_at"],
            }
            for vInterview in get_coming_interviews(pDatabaseFile, datetime.now())
        ]
    }

    return rInterviews


@router.get("/tracking", dependencies=[Depends(require_api_token)])
def download_tracking(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie les candidatures en cours et la fiche des entretiens à venir."""

    rTracking = build_tracking(pDatabaseFile, datetime.now())

    return rTracking


@router.get("/withdrawn", dependencies=[Depends(require_api_token)])
def download_withdrawn_offers(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie les offres suivies que leur site a retirées."""

    rOffers = {"offers": list_withdrawn_offers(pDatabaseFile)}

    return rOffers


@router.get("/replies", dependencies=[Depends(require_api_token)])
def download_replies(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie les réponses de recruteurs repérées par la dernière lecture de Gmail."""

    rReplies = {"replies": load_pending_replies(pDatabaseFile)}

    return rReplies


@router.get("/offers", dependencies=[Depends(require_api_token)])
def download_offers(pDatabaseFile: str = Depends(get_database_file)):
    """Renvoie les nouvelles offres de la semaine, les mieux notées en tête."""

    rOffers = {"offers": build_offer_list(pDatabaseFile, datetime.now())}

    return rOffers


@router.post("/notes", dependencies=[Depends(require_api_token)])
def upload_phone_notes(
    pNotes: list = Body(..., embed=True, alias="notes"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute aux candidatures les notes rapides prises sur le téléphone."""

    try:
        rReport = sync_phone_notes(pDatabaseFile, pNotes, datetime.now())

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    return rReport


@router.post("/applications", dependencies=[Depends(require_api_token)])
def upload_status_changes(
    pChanges: list = Body(..., embed=True, alias="changes"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Applique les statuts donnés aux offres depuis le téléphone."""

    try:
        rReport = sync_status_changes(pDatabaseFile, pChanges, datetime.now())

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    return rReport
