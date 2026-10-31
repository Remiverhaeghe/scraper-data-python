"""Progression : page des quêtes et encart du menu, chargé à part"""

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.achievements import get_heat_level, sort_achievements
from job.cosmetics import choose_cosmetic, set_sounds
from job.progress import build_progress, describe_level, get_total_xp
from web.dependencies import get_database_file, require_csrf
from web.rendering import build_bar_chart, templates

router = APIRouter()


@router.get("/progress", response_class=HTMLResponse)
def show_progress(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche le niveau, les quêtes, les points récents et les règles du jeu."""

    vProgress = build_progress(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        request,
        "progress.html",
        {
            "active_page": "progress",
            "progress": vProgress,
            "heat_level": get_heat_level,
            "achievements": sort_achievements(vProgress["achievements"]),
            "chart": build_bar_chart(
                [
                    date.fromisoformat(vDay["day"]).strftime("%d/%m")
                    for vDay in vProgress["history"]
                ],
                [
                    (
                        "Points",
                        "var(--blue)",
                        [vDay["xp"] for vDay in vProgress["history"]],
                    )
                ],
                pEmptyText="Aucun point ces 14 derniers jours : une révision suffit "
                "pour commencer",
            ),
        },
    )

    return rResponse


@router.get("/progress/summary", response_class=HTMLResponse)
def show_progress_summary(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Retourne l'encart du menu ; le navigateur y repère les points gagnés."""

    rResponse = templates.TemplateResponse(
        request,
        "_progress_summary.html",
        {"progress": build_progress(pDatabaseFile)},
    )

    return rResponse


def redirect_to_rewards():
    """Revient à la carte des récompenses de la page Progression."""

    rResponse = RedirectResponse(
        router.url_path_for("show_progress") + "#rewards", status_code=303
    )

    return rResponse


@router.post("/progress/reward", dependencies=[Depends(require_csrf)])
def choose_reward(
    pKind: str = Form(alias="kind"),
    pId: str = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Choisit une couleur d'accent ou un cadre débloqué."""

    try:
        choose_cosmetic(
            pDatabaseFile,
            pKind,
            pId,
            describe_level(get_total_xp(pDatabaseFile))["level"],
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = redirect_to_rewards()

    return rResponse


@router.post("/progress/sounds", dependencies=[Depends(require_csrf)])
def change_reward_sounds(
    pEnabled: bool = Form(False, alias="enabled"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Active ou coupe le son de réussite."""

    set_sounds(pDatabaseFile, pEnabled)

    rResponse = redirect_to_rewards()

    return rResponse
