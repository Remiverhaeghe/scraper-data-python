"""Pages des compétences et du marché : demande des offres, préparation et salaires"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.market import (
    CITY_COLUMNS,
    HISTORY_COLUMNS,
    REGION_COLUMNS,
    SKILL_COLUMNS,
    build_history_cells,
    build_market,
    build_market_cells,
    build_market_history,
)
from job.profile import add_profile_skill
from job.quiz import load_active_quiz
from job.skill_glossary import build_glossary
from job.skills_dashboard import SKILL_STATUSES, build_skills_dashboard
from web.dependencies import get_database_file, require_csrf
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
            "glossary": build_glossary(),
            "definitions": dict(build_glossary()),
            "statuses": SKILL_STATUSES,
            "history_chart": build_bar_chart(
                [vPoint["label"] for vPoint in vDashboard["history"]],
                [
                    (
                        "Préparation",
                        "var(--primary)",
                        [vPoint["readiness"] for vPoint in vDashboard["history"]],
                    )
                ],
                pAxes=("Semaine", "% de préparation"),
                pEmptyText="Aucune réponse de révision pour le moment",
                pFillWidth=True,
            ),
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


@router.post("/skills/profile", dependencies=[Depends(require_csrf)])
def add_skill_to_profile(
    pSkill: str = Form(..., alias="skill"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute une compétence au profil, puis revient au tableau des compétences."""

    add_profile_skill(pDatabaseFile, pSkill[:100])

    rResponse = RedirectResponse(router.url_path_for("show_skills"), status_code=303)

    return rResponse


@router.get("/market", response_class=HTMLResponse)
def show_market(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche le marché : volumes et salaires par compétence et par ville."""

    vMarket = build_market(pDatabaseFile, datetime.now())
    vHistory = build_market_history(pDatabaseFile, datetime.now())

    rResponse = templates.TemplateResponse(
        request,
        "market.html",
        {
            "active_page": "market",
            "market": vMarket,
            "history_columns": HISTORY_COLUMNS,
            "history_rows": [build_history_cells(vMonth) for vMonth in vHistory],
            "history_chart": build_bar_chart(
                [vMonth["label"] for vMonth in vHistory],
                [
                    (
                        "Offres",
                        "var(--primary)",
                        [vMonth["offers"] for vMonth in vHistory],
                    ),
                    (
                        "Avec vos compétences",
                        "var(--success)",
                        [vMonth["mine"] for vMonth in vHistory],
                    ),
                ],
                pAxes=("Mois", "Offres vues"),
                pEmptyText="Aucune offre pour le moment",
                pFillWidth=True,
            ),
            "tables": [
                (
                    "Compétences les plus demandées",
                    "Médiane affichée à partir de trois salaires",
                    SKILL_COLUMNS,
                    [build_market_cells(vRow, True) for vRow in vMarket["skills"]],
                ),
                (
                    "Régions qui recrutent le plus",
                    f"{vMarket['unknown_region_count']} offre(s) pas encore placée(s) "
                    "sur la carte ne sont pas classées",
                    REGION_COLUMNS,
                    [build_market_cells(vRow) for vRow in vMarket["regions"]],
                ),
                (
                    "Villes qui recrutent le plus",
                    f"{vMarket['unknown_city_count']} offre(s) sans ville ne sont "
                    "pas classées",
                    CITY_COLUMNS,
                    [build_market_cells(vRow) for vRow in vMarket["cities"]],
                ),
            ],
        },
    )

    return rResponse
