"""Pages publiques : connexion, déconnexion, mentions légales et licence"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APPLICATION_NAME
from job.presentation import (
    LICENSE_SUMMARY,
    LICENSE_SUMMARY_NOTE,
    build_legal_sections,
    read_icons_license,
    read_license,
)
from utils.logger import get_logger
from web.auth import (
    LoginRateLimiter,
    SESSION_COOKIE,
    SESSION_DURATION,
    check_credentials,
    second_factor,
    create_session_token,
    get_missing_auth_settings,
    is_safe_redirect,
)
from web.dependencies import require_csrf
from web.rendering import templates

logger = get_logger(__name__)


router = APIRouter()


login_rate_limiter = LoginRateLimiter()


@router.get("/license", response_class=HTMLResponse)
def show_license(request: Request):
    """Affiche la licence du projet, lue dans le fichier LICENSE."""

    rResponse = templates.TemplateResponse(
        request,
        "license.html",
        {
            "active_page": None,
            "license_text": read_license(),
            "icons_license_text": read_icons_license(),
            "license_summary": LICENSE_SUMMARY,
            "license_summary_note": LICENSE_SUMMARY_NOTE,
        },
    )

    return rResponse


def render_login(pRequest, pNext, pMessage=None, pStatusCode=200):
    """Affiche la page de connexion, ou ce qu'il manque pour l'utiliser."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "login.html",
        {
            "next": pNext if is_safe_redirect(pNext) else "/",
            "message": pMessage,
            # Seuls les noms des variables sont affichés, jamais leurs valeurs.
            "missing_settings": get_missing_auth_settings(),
            "totp_enabled": second_factor.is_enabled(),
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/login", response_class=HTMLResponse)
def show_login(request: Request, pNext: str = Query("/", alias="next")):
    """Affiche la connexion, ou renvoie vers la page demandée si déjà connecté."""

    if request.state.session:
        rResponse = RedirectResponse(
            pNext if is_safe_redirect(pNext) else "/", status_code=303
        )
    else:
        rResponse = render_login(request, pNext)

    return rResponse


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    pUsername: str = Form("", alias="username"),
    pPassword: str = Form("", alias="password"),
    pCode: str = Form("", alias="code"),
    pNext: str = Form("/", alias="next"),
):
    """Ouvre une session si l'identifiant et le mot de passe sont corrects."""

    vAddress = request.client.host if request.client else "inconnue"
    vNow = datetime.now()

    if get_missing_auth_settings():
        rResponse = render_login(
            request, pNext, "Authentification non configurée.", 503
        )

    elif login_rate_limiter.is_blocked(vAddress, vNow):
        logger.warning("Connexion refusée après trop d'échecs depuis %s", vAddress)

        rResponse = render_login(
            request, pNext, "Trop de tentatives. Réessayez dans 15 minutes.", 429
        )

    # Le code n'est vérifié qu'avec des identifiants corrects : un code valide
    # n'est pas consommé par une tentative au mauvais mot de passe.
    elif not check_credentials(pUsername, pPassword) or not second_factor.check(
        pCode, vNow.timestamp()
    ):
        login_rate_limiter.record_failure(vAddress, vNow)

        logger.warning("Échec de connexion au tableau de bord depuis %s", vAddress)

        rResponse = render_login(
            request,
            pNext,
            (
                "Identifiant, mot de passe ou code incorrect."
                if second_factor.is_enabled()
                else "Identifiant ou mot de passe incorrect."
            ),
            401,
        )

    else:
        login_rate_limiter.reset(vAddress)

        logger.info("Connexion au tableau de bord depuis %s", vAddress)

        rResponse = RedirectResponse(
            pNext if is_safe_redirect(pNext) else "/", status_code=303
        )
        rResponse.set_cookie(
            SESSION_COOKIE,
            create_session_token(os.getenv("WEB_SESSION_SECRET"), pUsername, vNow),
            max_age=int(SESSION_DURATION.total_seconds()),
            httponly=True,
            samesite="lax",
            # À activer lorsque le tableau de bord est servi en HTTPS.
            secure=os.getenv("WEB_SECURE_COOKIE") == "1",
        )

    return rResponse


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout():
    """Ferme la session en supprimant son cookie."""

    logger.info("Déconnexion du tableau de bord")

    rResponse = RedirectResponse(router.url_path_for("show_login"), status_code=303)
    rResponse.delete_cookie(SESSION_COOKIE)

    # Les copies de pages gardées pour le hors connexion contiennent offres et
    # candidatures : le navigateur les efface à la déconnexion.
    rResponse.headers["Clear-Site-Data"] = '"cache", "storage"'

    return rResponse


@router.get("/legal", response_class=HTMLResponse)
def show_legal(request: Request):
    """Affiche les mentions légales et la licence."""

    rResponse = templates.TemplateResponse(
        request,
        "legal.html",
        {"active_page": None, "sections": build_legal_sections(APPLICATION_NAME)},
    )

    return rResponse
