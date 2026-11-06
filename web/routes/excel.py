"""Atelier Excel sur le web : niveaux, feuille et vérification d'une formule"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from job.excel_formula import MAX_FORMULA_LENGTH
from job.excel_levels import (
    build_excel_overview,
    load_levels,
    run_level,
    save_attempt,
)
from job.progress import XP_RULES
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def check_level(pLevelId):
    """Retourne un niveau ; refuse un identifiant inconnu."""

    rLevel = load_levels().get(pLevelId)

    if rLevel is None:
        raise HTTPException(status_code=404, detail="Niveau inconnu.")

    return rLevel


def build_states(pRun):
    """Retourne l'état de chaque cellule cible : ok ou ko après un essai."""

    rStates = {vCell["cell"]: "ok" if vCell["ok"] else "ko" for vCell in pRun["cells"]}

    return rStates


def render_excel(pRequest, pOverview, pValues):
    """Affiche la page avec les niveaux par série et le niveau demandé."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "excel.html",
        {
            "active_page": "excel",
            "overview": pOverview,
            "level_xp": XP_RULES["excel_level"][1],
            "max_formula_length": MAX_FORMULA_LENGTH,
            **pValues,
        },
    )

    return rResponse


@router.get("/excel", response_class=HTMLResponse)
def show_excel(
    request: Request,
    pLevelId: str = Query("", alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les niveaux, et le niveau choisi avec la dernière formule essayée."""

    vOverview = build_excel_overview(pDatabaseFile)
    vValues = {}

    if pLevelId:
        vLevel = check_level(pLevelId)
        vFormula = next(
            vRow["formula"]
            for vSeries in vOverview["series"]
            for vRow in vSeries["rows"]
            if vRow["id"] == pLevelId
        )
        vValues = {
            "level": vLevel,
            "formula": vFormula,
            "grid": run_level(vLevel, "")["grid"],
            "states": {},
        }

    rResponse = render_excel(request, vOverview, vValues)

    return rResponse


@router.post(
    "/excel/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def run_excel(
    request: Request,
    pLevelId: str = Form(alias="level"),
    pFormula: str = Form("", alias="formula", max_length=MAX_FORMULA_LENGTH),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Recopie la formule sur la plage du niveau et la compare à la solution."""

    vLevel = check_level(pLevelId)
    vFormula = pFormula.strip()
    vRun = run_level(vLevel, vFormula)
    vFirst = False

    if vRun["cells"]:
        vFirst = save_attempt(pDatabaseFile, pLevelId, vFormula, vRun["passed"])

    rResponse = render_excel(
        request,
        build_excel_overview(pDatabaseFile),
        {
            "level": vLevel,
            "formula": vFormula,
            "grid": vRun["grid"],
            "states": build_states(vRun),
            "run": vRun,
            "first": vFirst,
        },
    )

    return rResponse
