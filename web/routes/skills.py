"""Page des compétences : demande des offres croisée avec la préparation"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from job.quiz import load_active_quiz
from job.skills_dashboard import SKILL_STATUSES, build_skills_dashboard
from web.dependencies import get_database_file
from web.rendering import build_bar_chart, templates

router = APIRouter()

# Compétences reprises dans le graphique : au-delà, les libellés se chevauchent
CHART_SKILLS = 10


@router.get("/skills", response_class=HTMLResponse)
def show_skills(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les compétences les plus demandées et la préparation de chacune."""

    vDashboard = build_skills_dashboard(pDatabaseFile, load_active_quiz(pDatabaseFile))
    vChartRows = vDashboard["rows"][:CHART_SKILLS]

    rResponse = templates.TemplateResponse(
        request,
        "skills.html",
        {
            "active_page": "skills",
            "dashboard": vDashboard,
            "statuses": SKILL_STATUSES,
            "chart": build_bar_chart(
                [vRow["skill"] for vRow in vChartRows],
                [
                    (
                        "Offres",
                        [
                            f"var(--{SKILL_STATUSES[vRow['status']][2]})"
                            for vRow in vChartRows
                        ],
                        [vRow["offers"] for vRow in vChartRows],
                    )
                ],
                pAxes=("Compétence", "Offres qui la demandent"),
                pEmptyText="Aucune compétence repérée dans vos offres pour le moment",
                pFillWidth=True,
            ),
        },
    )

    return rResponse
