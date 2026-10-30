"""Pannes à résoudre sur le web : choix, mesures, réparation et résultat"""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.troubleshooting import (
    CHECK_PREFIX,
    REPAIR_PREFIX,
    build_overview,
    load_scenarios,
    parse_actions,
    play,
    save_result,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()

# Au-delà, la liste d'actions ne vient pas d'une vraie partie
MAX_ACTIONS = 40


def check_scenario(pScenarioId):
    """Refuse un scénario inconnu."""

    if pScenarioId not in load_scenarios():
        raise HTTPException(status_code=404, detail="Panne inconnue.")


def build_play_url(pScenarioId, pActions):
    """Retourne l'adresse d'une partie avec ses actions."""

    rUrl = "/troubleshooting/play?" + urlencode(
        {"scenario": pScenarioId, "actions": ",".join(pActions)}
    )

    return rUrl


def render_troubleshooting(pRequest, pDatabaseFile, pValues):
    """Affiche la page avec la vue d'ensemble et le contenu demandé."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "troubleshooting.html",
        {
            "active_page": "troubleshooting",
            "overview": build_overview(pDatabaseFile),
            "check_prefix": CHECK_PREFIX,
            "repair_prefix": REPAIR_PREFIX,
            **pValues,
        },
    )

    return rResponse


@router.get("/troubleshooting", response_class=HTMLResponse)
def show_troubleshooting(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les pannes et les meilleurs scores."""

    rResponse = render_troubleshooting(request, pDatabaseFile, {})

    return rResponse


@router.get("/troubleshooting/play", response_class=HTMLResponse)
def play_troubleshooting(
    request: Request,
    pScenarioId: str = Query(alias="scenario"),
    pActions: str = Query("", alias="actions"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche une intervention en cours ; une mesure ajoute une action à l'adresse."""

    check_scenario(pScenarioId)
    vActions = [
        vAction
        for vAction in parse_actions(pActions)[:MAX_ACTIONS]
        if vAction.startswith(CHECK_PREFIX) or vAction.startswith(REPAIR_PREFIX)
    ]
    vState = play(pScenarioId, vActions)

    # Une partie résolue s'enregistre par le formulaire de réparation, pas ici.
    if vState["solved"]:
        raise HTTPException(status_code=400, detail="Partie déjà terminée.")

    rResponse = render_troubleshooting(
        request,
        pDatabaseFile,
        {
            "state": vState,
            "actions": ",".join(vActions),
            "check_urls": {
                vCheck["id"]: build_play_url(
                    pScenarioId, [*vActions, CHECK_PREFIX + vCheck["id"]]
                )
                for vCheck in vState["scenario"]["checks"]
            },
        },
    )

    return rResponse


@router.post(
    "/troubleshooting/repair",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def repair_troubleshooting(
    request: Request,
    pScenarioId: str = Form(alias="scenario"),
    pActions: str = Form("", alias="actions"),
    pCause: str = Form(alias="cause"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Tente une réparation : retour à la partie si c'est la mauvaise, résultat sinon."""

    check_scenario(pScenarioId)
    vActions = [*parse_actions(pActions)[:MAX_ACTIONS], REPAIR_PREFIX + pCause]
    vState = play(pScenarioId, vActions)

    if not vState["solved"]:
        return RedirectResponse(build_play_url(pScenarioId, vActions), status_code=303)

    vState["xp"] = save_result(pDatabaseFile, vState)

    rResponse = render_troubleshooting(request, pDatabaseFile, {"result": vState})

    return rResponse
