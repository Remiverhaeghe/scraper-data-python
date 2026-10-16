"""Application web du tableau de bord des offres d'emploi"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import ASSETS_DIRECTORY
from job.mobile_sync import API_PREFIX
from storage.database import initialize_database
from utils.logger import get_logger
from web.api import router as api_router
from web.auth import SESSION_COOKIE, read_session_token
from web.dependencies import get_database_file
from web.rendering import WEB_DIRECTORY, templates
from web.routes.offers import router as offers_router
from web.routes.applications import router as applications_router
from web.routes.quiz import router as quiz_router
from web.routes.skills import router as skills_router
from web.routes.challenges import router as challenges_router
from web.routes.git_sandbox import router as git_sandbox_router
from web.routes.monitoring import router as monitoring_router
from web.routes.profile import router as profile_router
from web.routes.settings import router as settings_router
from web.routes.account import router as account_router

logger = get_logger(__name__)


# Pages accessibles sans connexion : connexion, informations légales et ressources
PUBLIC_PATHS = ("/login", "/legal", "/license")


# L'abonnement à l'agenda est relu sans session : son jeton secret le protège.
# L'API mobile n'a pas de session : chacune de ses routes exige son jeton.
PUBLIC_PREFIXES = ("/static/", "/assets/", "/calendar/", "/api/")


@asynccontextmanager
async def lifespan(pApp):
    """Prépare la base avant de servir les premières requêtes."""

    # Respecte une base de test fournie via dependency_overrides.
    vGetDatabaseFile = pApp.dependency_overrides.get(
        get_database_file, get_database_file
    )

    initialize_database(vGetDatabaseFile())

    yield


app = FastAPI(title="Offres d'emploi", lifespan=lifespan)


# API de l'application mobile de révision, protégée par son propre jeton
app.include_router(api_router)


app.mount("/static", StaticFiles(directory=WEB_DIRECTORY / "static"), name="static")


app.mount("/assets", StaticFiles(directory=ASSETS_DIRECTORY), name="assets")


# Authentification : toute page exige une session, sauf PUBLIC_PATHS et les
# ressources statiques. Mot de passe et jeton de session : voir web/auth.py.
# Une page qui renvoie sans cesse vers /login signale un .env incomplet
# (WEB_USERNAME, WEB_PASSWORD_HASH, WEB_SESSION_SECRET).
def is_public_path(pPath):
    """Indique si une adresse reste accessible sans être connecté."""

    rPublic = pPath in PUBLIC_PATHS or pPath.startswith(PUBLIC_PREFIXES)

    return rPublic


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Réserve le tableau de bord à l'utilisateur connecté."""

    vSecret = os.getenv("WEB_SESSION_SECRET")
    vToken = request.cookies.get(SESSION_COOKIE)

    request.state.session = (
        read_session_token(vSecret, vToken, datetime.now())
        if vSecret and vToken
        else None
    )

    vPath = request.url.path

    if request.state.session is None and not is_public_path(vPath):
        vTarget = f"{vPath}?{request.url.query}" if request.url.query else vPath
        vLoginUrl = f"{app.url_path_for('show_login')}?next={quote(vTarget)}"

        # HTMX remplacerait un fragment par la page de connexion : il recharge
        # plutôt toute la page vers l'adresse indiquée.
        if request.headers.get("HX-Request"):
            rResponse = Response(status_code=401, headers={"HX-Redirect": vLoginUrl})
        else:
            rResponse = RedirectResponse(vLoginUrl, status_code=303)

    else:
        rResponse = await call_next(request)

    return rResponse


# Scripts limités aux fichiers du site ; les styles en ligne restent permis pour
# les couleurs et hauteurs calculées des graphiques.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


# Déclaré après require_login, il l'englobe : les redirections vers la
# connexion reçoivent aussi les en-têtes.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Ajoute les en-têtes de sécurité HTTP à chaque réponse."""

    rResponse = await call_next(request)

    # Une route plus stricte, celle des schémas SVG, garde sa propre politique.
    for vName, vValue in SECURITY_HEADERS.items():
        rResponse.headers.setdefault(vName, vValue)

    return rResponse


# Pages d'erreur intégrées au site.
@app.exception_handler(StarletteHTTPException)
async def render_http_error(pRequest, pException):
    """Affiche une erreur dans le gabarit du site plutôt qu'en JSON brut.

    Les requêtes HTMX reçoivent un simple texte, inséré sans casser la page ;
    l'API mobile reçoit du JSON, avec les en-têtes de l'erreur (WWW-Authenticate).
    """

    vTitle = "Page introuvable" if pException.status_code == 404 else "Requête refusée"

    if pRequest.url.path.startswith(API_PREFIX):
        rResponse = JSONResponse(
            {"detail": pException.detail},
            status_code=pException.status_code,
            headers=pException.headers,
        )
    elif pRequest.headers.get("HX-Request"):
        rResponse = HTMLResponse(pException.detail, status_code=pException.status_code)
    else:
        rResponse = templates.TemplateResponse(
            pRequest,
            "error.html",
            {"title": vTitle, "message": pException.detail},
            status_code=pException.status_code,
        )

    return rResponse


# Chaque domaine du tableau de bord a son module de routes (web/routes).
app.include_router(offers_router)
app.include_router(applications_router)
app.include_router(quiz_router)
app.include_router(skills_router)
app.include_router(challenges_router)
app.include_router(git_sandbox_router)
app.include_router(monitoring_router)
app.include_router(profile_router)
app.include_router(settings_router)
app.include_router(account_router)
