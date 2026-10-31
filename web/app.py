"""Application web du tableau de bord des offres d'emploi"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import ASSETS_DIRECTORY
from job.mobile_sync import API_PREFIX
from storage.database import initialize_database
from utils.logger import get_logger
from web.api import router as api_router
from web.auth import SESSION_COOKIE, get_sessions_revoked_at, read_session_token
from web.dependencies import get_database_file
from web.rendering import WEB_DIRECTORY, templates
from web.routes.offers import router as offers_router
from web.routes.dashboard import router as dashboard_router
from web.routes.offer_tracking import router as offer_tracking_router
from web.routes.comparison import router as comparison_router
from web.routes.applications import router as applications_router
from web.routes.quiz import router as quiz_router
from web.routes.skills import router as skills_router
from web.routes.certifications import router as certifications_router
from web.routes.aptitude import router as aptitude_router
from web.routes.troubleshooting import router as troubleshooting_router
from web.routes.ladder import router as ladder_router
from web.routes.sql_sandbox import router as sql_sandbox_router
from web.routes.circuit import router as circuit_router
from web.routes.devops import router as devops_router
from web.routes.challenges import router as challenges_router
from web.routes.puzzles import router as puzzles_router
from web.routes.git_sandbox import router as git_sandbox_router
from web.routes.monitoring import router as monitoring_router
from web.routes.profile import router as profile_router
from web.routes.progress import router as progress_router
from web.routes.settings import router as settings_router
from web.routes.account import router as account_router

logger = get_logger(__name__)


# Pages accessibles sans connexion : connexion, informations légales et ressources
# Le service worker est chargé par le navigateur avant toute connexion.
PUBLIC_PATHS = ("/login", "/legal", "/license", "/service-worker.js")


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


@app.get("/service-worker.js", include_in_schema=False)
def serve_service_worker():
    """Sert le service worker à la racine : il ne gère que les adresses sous la sienne."""

    rResponse = FileResponse(
        WEB_DIRECTORY / "static" / "service-worker.js",
        media_type="text/javascript",
        # Une nouvelle version est prise dès le prochain chargement.
        headers={"Cache-Control": "no-cache"},
    )

    return rResponse


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

    # Même base que les routes, y compris celle d'un test (dependency_overrides)
    vDatabaseFile = app.dependency_overrides.get(get_database_file, get_database_file)()

    request.state.session = (
        read_session_token(
            vSecret, vToken, datetime.now(), get_sessions_revoked_at(vDatabaseFile)
        )
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
        # Fonds de carte de la page Carte des offres, rien d'autre
        "img-src 'self' data: https://tile.openstreetmap.org",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


# Au-delà, une page est signalée dans les journaux pour en chercher la cause.
SLOW_PAGE_SECONDS = 1.0

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
    """Ajoute les en-têtes de sécurité HTTP à chaque réponse et signale les pages
    lentes dans les journaux.
    """

    vStart = time.perf_counter()
    rResponse = await call_next(request)
    vDuration = time.perf_counter() - vStart

    # Chemin seul : les paramètres peuvent contenir une recherche ou un jeton.
    if vDuration > SLOW_PAGE_SECONDS:
        logger.warning("Page lente : %s en %.1f s", request.url.path, vDuration)

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
app.include_router(dashboard_router)
app.include_router(offers_router)
app.include_router(offer_tracking_router)
app.include_router(comparison_router)
app.include_router(applications_router)
app.include_router(quiz_router)
app.include_router(skills_router)
app.include_router(certifications_router)
app.include_router(aptitude_router)
app.include_router(troubleshooting_router)
app.include_router(ladder_router)
app.include_router(challenges_router)
app.include_router(puzzles_router)
app.include_router(git_sandbox_router)
app.include_router(sql_sandbox_router)
app.include_router(circuit_router)
app.include_router(devops_router)
app.include_router(monitoring_router)
app.include_router(profile_router)
app.include_router(progress_router)
app.include_router(settings_router)
app.include_router(account_router)
