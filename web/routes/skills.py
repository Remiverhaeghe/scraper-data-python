"""Pages des compétences et du marché : demande des offres, préparation et salaires"""

from datetime import datetime

import requests

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.geocoding import get_home_department
from job.labour_market import (
    BMO_URL,
    OUTLOOK_LISTS,
    build_outlook,
    describe_outlook_row,
    refresh_labour_market,
)
from job.market import (
    CITY_COLUMNS,
    HISTORY_COLUMNS,
    REGION_COLUMNS,
    SKILL_COLUMNS,
    build_history_cells,
    build_market,
    build_market_cells,
    build_market_history,
    load_market_period,
)
from job.profile import add_profile_skill, load_profile
from job.quiz import load_active_quiz
from job.skill_glossary import build_glossary
from job.skills_dashboard import SKILL_STATUSES, build_skills_dashboard
from utils.logger import get_logger
from web.dependencies import get_database_file, require_csrf
from web.rendering import build_bar_chart, templates

logger = get_logger(__name__)

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


# Messages fixes du téléchargement de l'enquête : rien de saisi n'est renvoyé.
OUTLOOK_MESSAGES = {
    "updated": ("Enquête France Travail à jour.", "success"),
    "failed": (
        "Téléchargement impossible : vérifiez la connexion et réessayez.",
        "danger",
    ),
}


@router.get("/market", response_class=HTMLResponse)
def show_market(
    request: Request,
    pDepartment: str = Query("", alias="department"),
    pOutlookResult: str = Query("", alias="outlook"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche le marché : volumes et salaires par compétence et par ville, puis les
    métiers qui recrutent d'après France Travail.
    """

    # Sans choix, le département du domicile ; « france » pour toute la France
    vDepartment = pDepartment or get_home_department(pDatabaseFile)
    vOutlook = build_outlook(
        load_profile(pDatabaseFile),
        None if vDepartment in (None, "", "france") else vDepartment,
    )
    vNow = datetime.now()
    vOffers = load_market_period(pDatabaseFile, vNow)
    vMarket = build_market(pDatabaseFile, vNow, pOffers=vOffers)
    vHistory = build_market_history(pDatabaseFile, vNow, pOffers=vOffers)

    rResponse = templates.TemplateResponse(
        request,
        "market.html",
        {
            "active_page": "market",
            "market": vMarket,
            "outlook": vOutlook,
            "outlook_lists": OUTLOOK_LISTS,
            "bmo_url": BMO_URL,
            "outlook_message": OUTLOOK_MESSAGES.get(pOutlookResult),
            "describe_outlook_row": describe_outlook_row,
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


@router.post("/market/france-travail", dependencies=[Depends(require_csrf)])
def update_labour_market():
    """Télécharge et résume les deux dernières enquêtes BMO de France Travail."""

    try:
        refresh_labour_market()
        vResult = "updated"

    except (requests.RequestException, ValueError, KeyError) as vException:
        logger.warning("Enquête France Travail non téléchargée : %s", vException)
        vResult = "failed"

    rResponse = RedirectResponse(
        f"{router.url_path_for('show_market')}?outlook={vResult}", status_code=303
    )

    return rResponse
