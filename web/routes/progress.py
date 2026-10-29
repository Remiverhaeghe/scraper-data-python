"""Progression : page des quêtes et encart du menu, chargé à part"""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from job.progress import build_progress
from web.dependencies import get_database_file
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
