"""Page des paramètres : réglages, entreprises, alertes, abonnements et sauvegardes"""

import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from config import BACKUP_NAS_DIRECTORY
from job.agencies import load_interim_agencies, save_interim_agencies
from job.calendar import (
    CALENDAR_SUBSCRIPTION_PATH,
    build_calendar,
    build_subscription_url,
    check_calendar_token,
    get_calendar_token,
    renew_calendar_token,
)
from job.companies import load_company_rules, save_company_rules
from job.company_pages import (
    PLATFORMS,
    check_companies,
    load_company_list,
    save_company_lists,
)
from job.mobile_sync import (
    API_PREFIX,
    build_connection_svg,
    get_certificate_fingerprint,
    get_mobile_token,
    renew_mobile_token,
)
from job.schedule import (
    MIN_SCORE_CHOICES,
    describe_extra_searches,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    format_min_score,
    load_schedule,
    save_min_score,
)
from job.presentation import describe_backup
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.config import SOURCE_CATEGORIES
from job.sources.registry import SOURCES
from storage.archive import export_archive, restore_archive, restore_backup
from storage.backup import describe_backups, describe_nas_copies, fetch_nas_copy
from storage.maintenance import reset_database
from utils.logger import get_logger
from utils.mailer import get_missing_email_settings
from web.dependencies import get_database_file, require_csrf
from web.rendering import get_message_tone, templates

logger = get_logger(__name__)


router = APIRouter()


def render_settings(
    pRequest,
    pDatabaseFile,
    pMessage=None,
    pStatusCode=200,
    pResetMessage=None,
    pCompanies=None,
    pCompaniesMessage=None,
    pNotificationMessage=None,
    pCalendarMessage=None,
    pArchiveMessage=None,
    pMobileMessage=None,
    pBackupMessage=None,
    pCompanyPagesMessage=None,
):
    """Affiche thème, règles, planification, notifications et sources."""

    vSources = [
        {
            "label": vDefinition.label,
            "reason": vDefinition.get_unavailability_reason(),
            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            "missing": vDefinition.get_missing_settings(),
            "category": SOURCE_CATEGORIES.get(vDefinition.category),
        }
        # Regroupées par catégorie, dans l'ordre du registre à l'intérieur de chacune
        for vCategory in SOURCE_CATEGORIES
        for vDefinition in SOURCES.values()
        if vDefinition.category == vCategory
    ]

    vSchedule = load_schedule(pDatabaseFile)
    vSearch, vSearchSources = describe_scheduled_search(vSchedule)
    vMobileAddress = str(pRequest.base_url).rstrip("/") + API_PREFIX
    vMobileToken = get_mobile_token(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        pRequest,
        "settings.html",
        {
            "active_page": "settings",
            "sources": vSources,
            # Sans authentification, l'adresse e-mail elle-même n'est pas affichée.
            "schedule": {
                "search": vSearch,
                "sources": vSearchSources,
                "extra": describe_extra_searches(vSchedule),
                "enabled": vSchedule["enabled"],
                "interval": format_interval(vSchedule["interval_hours"]),
                "runs": describe_schedule_runs(vSchedule, datetime.now()),
                "has_email": vSchedule["email"] is not None,
                "min_score": vSchedule["min_score"],
                "missing_email_settings": get_missing_email_settings(),
            },
            "settings": load_settings(pDatabaseFile),
            "definitions": SETTING_DEFINITIONS,
            "message": pMessage,
            "reset_message": pResetMessage,
            # Textes saisis réaffichés après une erreur, sinon listes enregistrées
            "companies": pCompanies
            or {
                **{
                    vKind: "\n".join(vNames)
                    for vKind, vNames in load_company_rules(pDatabaseFile).items()
                },
                "agencies": "\n".join(load_interim_agencies(pDatabaseFile)),
            },
            "companies_message": pCompaniesMessage,
            "min_scores": {
                vScore: format_min_score(vScore) for vScore in MIN_SCORE_CHOICES
            },
            "notification_message": pNotificationMessage,
            "calendar_url": build_subscription_url(
                str(pRequest.base_url), get_calendar_token(pDatabaseFile)
            ),
            "calendar_message": pCalendarMessage,
            "mobile_address": vMobileAddress,
            "mobile_token": vMobileToken,
            # SVG produit ici à partir de l'adresse et du jeton, sans texte saisi.
            "mobile_qr": (
                build_connection_svg(
                    vMobileAddress, vMobileToken, get_certificate_fingerprint()
                )
                if vMobileToken
                else None
            ),
            "mobile_message": pMobileMessage,
            "message_tone": get_message_tone(pStatusCode),
            "archive_message": pArchiveMessage,
            "company_pages": [
                {
                    "key": vPlatform,
                    "label": vLabel,
                    "example": vExample,
                    "value": load_company_list(vPlatform, pDatabaseFile).replace(
                        ",", ", "
                    ),
                }
                for vPlatform, (vLabel, _, _, vExample) in PLATFORMS.items()
            ],
            "company_pages_message": pCompanyPagesMessage,
            "backups": [
                {"name": vBackup["name"], "label": describe_backup(vBackup)}
                for vBackup in describe_backups(pDatabaseFile)
            ],
            "backup_message": pBackupMessage,
            "nas_configured": bool(BACKUP_NAS_DIRECTORY),
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/settings", response_class=HTMLResponse)
def show_settings(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la page des paramètres."""

    rResponse = render_settings(request, pDatabaseFile)

    return rResponse


@router.post(
    "/settings", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
async def update_settings(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre les règles de calcul saisies, ou affiche les erreurs de saisie."""

    vForm = await request.form()

    vValues = {vKey: vForm[vKey] for vKey in SETTING_DEFINITIONS if vKey in vForm}

    try:
        _, vRecomputed = save_settings(pDatabaseFile, vValues)

    except ValueError as vException:
        rResponse = render_settings(request, pDatabaseFile, str(vException), 400)

    else:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            (
                f"Règles enregistrées, salaire net recalculé pour {vRecomputed} "
                "offre(s)."
                if vRecomputed
                else "Règles enregistrées."
            ),
        )

    return rResponse


@router.post(
    "/settings/reset",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
async def reset_data(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Sauvegarde puis efface toutes les données, après confirmation explicite."""

    vForm = await request.form()

    if vForm.get("confirm") != "1":
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pResetMessage="Cochez la case de confirmation pour réinitialiser.",
        )

    else:
        try:
            vBackupFile = reset_database(pDatabaseFile, datetime.now())

        except Exception:
            logger.exception("Échec de la réinitialisation des données depuis le web")

            rResponse = render_settings(
                request,
                pDatabaseFile,
                pStatusCode=500,
                pResetMessage="La réinitialisation a échoué. Voir les journaux.",
            )

        else:
            rResponse = render_settings(
                request,
                pDatabaseFile,
                pResetMessage=(
                    f"Données réinitialisées. Sauvegarde : {vBackupFile.name}"
                ),
            )

    return rResponse


# Pages publiques : licence, connexion, déconnexion et mentions légales.
@router.post(
    "/settings/companies",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_companies(
    request: Request,
    pExcluded: str = Form("", alias="excluded"),
    pPreferred: str = Form("", alias="preferred"),
    pAgencies: str = Form("", alias="agencies"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre les listes d'entreprises, ou les réaffiche avec l'erreur."""

    try:
        vRules = save_company_rules(pDatabaseFile, pExcluded, pPreferred)
        vAgencies = save_interim_agencies(pDatabaseFile, pAgencies)

    except ValueError as vException:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pCompanies={
                "excluded": pExcluded,
                "preferred": pPreferred,
                "agencies": pAgencies,
            },
            pCompaniesMessage=str(vException),
        )

    else:
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pCompaniesMessage=f"{len(vRules['excluded'])} entreprise(s) exclue(s), "
            f"{len(vRules['preferred'])} privilégiée(s), "
            f"{len(vAgencies)} agence(s) d'intérim.",
        )

    return rResponse


@router.post(
    "/settings/alerts",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def update_alerts(
    request: Request,
    pMinScore: int = Form(alias="min_score"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le score minimal des offres envoyées par e-mail."""

    vErrors = save_min_score(pDatabaseFile, pMinScore)

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pStatusCode=400 if vErrors else 200,
        pNotificationMessage=" ".join(vErrors) or "Alertes enregistrées.",
    )

    return rResponse


@router.post(
    "/settings/calendar",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def renew_calendar(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée une nouvelle adresse d'abonnement ; l'ancienne cesse de fonctionner."""

    renew_calendar_token(pDatabaseFile)

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pCalendarMessage="Adresse créée : ajoutez-la dans l'agenda comme agenda "
        "par URL.",
    )

    return rResponse


@router.post(
    "/settings/mobile",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def renew_mobile(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Crée un nouveau jeton de l'application mobile ; l'ancien cesse de fonctionner."""

    renew_mobile_token(pDatabaseFile)

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pMobileMessage="Jeton créé : saisissez-le dans l'application.",
    )

    return rResponse


@router.get(CALENDAR_SUBSCRIPTION_PATH.replace("{token}", "{pToken}"))
def subscribe_calendar(
    pToken: str,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Sert l'agenda aux applications abonnées, sur présentation du jeton."""

    if not check_calendar_token(pDatabaseFile, pToken):
        # Le jeton reçu n'est pas journalisé : il pourrait être presque juste.
        logger.warning("Abonnement à l'agenda refusé : jeton invalide")

        raise HTTPException(status_code=404)

    rResponse = Response(
        build_calendar(pDatabaseFile, datetime.now()),
        media_type="text/calendar; charset=utf-8",
    )

    return rResponse


@router.get("/settings/archive")
def download_archive(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge la base et les pièces jointes dans une archive .zip."""

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as vFile:
        vPath = Path(vFile.name)

    try:
        export_archive(pDatabaseFile, vPath)

    except Exception:
        vPath.unlink(missing_ok=True)
        raise

    # Le fichier temporaire est supprimé une fois envoyé.
    rResponse = FileResponse(
        vPath,
        media_type="application/zip",
        filename=f"jobboard-{datetime.now():%Y%m%d}.zip",
        background=BackgroundTask(vPath.unlink, missing_ok=True),
    )

    return rResponse


@router.post(
    "/settings/archive",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def upload_archive(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pConfirm: str = Form("", alias="confirm"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Restaure une sauvegarde complète envoyée, après confirmation explicite."""

    if pConfirm != "1":
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pArchiveMessage="Cochez la case de confirmation pour restaurer.",
        )

    else:
        try:
            vBackupFile = restore_archive(pDatabaseFile, pFile.file, datetime.now())

        except ValueError as vException:
            logger.warning("Restauration refusée depuis le web : %s", vException)

            rResponse = render_settings(
                request, pDatabaseFile, pStatusCode=400, pArchiveMessage=str(vException)
            )

        else:
            rResponse = render_settings(
                request,
                pDatabaseFile,
                pArchiveMessage=f"Sauvegarde restaurée. Anciennes données : "
                f"{vBackupFile.name}",
            )

    return rResponse


@router.post(
    "/settings/backup",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def restore_database_backup(
    request: Request,
    pName: str = Form("", alias="name"),
    pConfirm: str = Form("", alias="confirm"),
    pOrigin: str = Form("", alias="origin"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Remet la base dans l'état d'une sauvegarde choisie, après confirmation.

    Avec origin=nas, la copie est d'abord rapatriée du NAS.
    """

    if pConfirm != "1":
        rResponse = render_settings(
            request,
            pDatabaseFile,
            pStatusCode=400,
            pBackupMessage="Cochez la case de confirmation pour restaurer.",
        )

    else:
        try:
            if pOrigin == "nas":
                fetch_nas_copy(pDatabaseFile, pName)

            vBackupFile = restore_backup(pDatabaseFile, pName, datetime.now())

        except (ValueError, OSError) as vException:
            logger.warning("Restauration de sauvegarde refusée : %s", vException)

            rResponse = render_settings(
                request, pDatabaseFile, pStatusCode=400, pBackupMessage=str(vException)
            )

        else:
            rResponse = render_settings(
                request,
                pDatabaseFile,
                pBackupMessage=f"Sauvegarde restaurée. Anciennes données : "
                f"{vBackupFile.name}",
            )

    return rResponse


@router.get("/settings/nas-copies", response_class=HTMLResponse)
def list_nas_copies_fragment(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Liste les copies du NAS à restaurer (fragment HTMX, lu à la demande)."""

    try:
        vCopies = [
            {"name": vCopy["name"], "label": describe_backup(vCopy)}
            for vCopy in describe_nas_copies(pDatabaseFile)
        ]
        vError = None

    except OSError as vException:
        logger.warning("Copies du NAS illisibles : %s", vException)
        vCopies = []
        vError = "Le NAS est injoignable : vérifiez qu'il est allumé et accessible."

    rResponse = templates.TemplateResponse(
        request, "_nas_copies.html", {"copies": vCopies, "error": vError}
    )

    return rResponse


async def read_company_pages(pRequest):
    """Lit dans le formulaire la liste saisie pour chaque plateforme."""

    vForm = await pRequest.form()

    rLists = {vPlatform: str(vForm.get(vPlatform, "")) for vPlatform in PLATFORMS}

    return rLists


@router.post(
    "/settings/company-pages",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
async def update_company_pages(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Enregistre les entreprises suivies, prises en compte à la prochaine recherche."""

    save_company_lists(pDatabaseFile, await read_company_pages(request))

    rResponse = render_settings(
        request,
        pDatabaseFile,
        pCompanyPagesMessage="Listes enregistrées : prises en compte à la prochaine recherche.",
    )

    return rResponse


@router.post(
    "/settings/company-pages/check",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
async def check_company_pages(request: Request):
    """Vérifie chaque entreprise saisie auprès de sa plateforme (fragment HTMX)."""

    vLists = await read_company_pages(request)
    vResults = [
        (PLATFORMS[vPlatform][0], vCompany, vCount, vMessage)
        for vPlatform, vText in vLists.items()
        for vCompany, vCount, vMessage in await run_in_threadpool(
            check_companies, vPlatform, vText
        )
    ]

    rResponse = templates.TemplateResponse(
        request, "_company_pages_check.html", {"results": vResults}
    )

    return rResponse
