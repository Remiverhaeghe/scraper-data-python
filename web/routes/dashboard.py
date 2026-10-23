"""Tableau de bord et lancement d'une recherche depuis le web"""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from job.presentation import CHART_PALETTE, FOLLOW_UP_FILTER, describe_execution
from job.schedule import request_immediate_run
from job.setup_checklist import build_setup_checklist
from job.statistics import (
    ACTIVITY_AXES,
    ACTIVITY_SERIES,
    EMPTY_CHART_TEXT,
    count_ready_sources,
    load_statistics,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import TONE_ICONS, build_bar_chart, templates

router = APIRouter()


# Pages principales. Les données et leur mise en forme viennent de job/,
# partagé avec l'application de bureau : une différence d'affichage entre les
# deux interfaces se corrige d'abord là.
@router.get("/", response_class=HTMLResponse)
def show_dashboard(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche le tableau de bord : indicateurs, graphique et activité récente."""

    vStatistics = load_statistics(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "statistics": vStatistics,
            "checklist": build_setup_checklist(pDatabaseFile),
            "ready_sources": count_ready_sources(),
            "new_offer_days": vStatistics["new_offer_days"],
            "chart": build_bar_chart(
                [
                    f"{vDay:%d/%m}"
                    for vDay, _ in vStatistics["daily_activity"]["new_offers"]
                ],
                [
                    (
                        ACTIVITY_SERIES[vName][0],
                        CHART_PALETTE[vIndex],
                        [vCount for _, vCount in vCounts],
                    )
                    for vIndex, (vName, vCounts) in enumerate(
                        vStatistics["daily_activity"].items()
                    )
                ],
                pIndependentScales=True,
                pAxes=ACTIVITY_AXES,
                pEmptyText=EMPTY_CHART_TEXT,
            ),
            "activities": [
                describe_execution(vEntry) for vEntry in vStatistics["executions"]
            ],
            "tone_icons": TONE_ICONS,
            "follow_up_filter": FOLLOW_UP_FILTER,
            "now_iso": datetime.now().isoformat(),
        },
    )

    return rResponse


@router.post(
    "/search/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def request_search(pDatabaseFile: str = Depends(get_database_file)):
    """Demande au planificateur de lancer la recherche enregistrée."""

    vErrors = request_immediate_run(pDatabaseFile, datetime.now())

    rResponse = HTMLResponse(
        " ".join(vErrors)
        or "Recherche demandée : le planificateur la lance dans la minute. "
        "Les nouvelles offres apparaîtront ensuite dans la liste."
    )

    return rResponse
