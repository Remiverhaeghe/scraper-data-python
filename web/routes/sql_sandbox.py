"""Bac à sable SQL sur le web : niveaux, dialecte, exécution d'une requête"""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.progress import XP_RULES
from job.sql_levels import (
    build_schema,
    build_sql_overview,
    load_levels,
    pick,
    run_level,
    save_attempt,
    save_dialect,
)
from job.sql_sandbox import DIALECTS, MAX_QUERY_LENGTH, MAX_ROWS, format_value
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def check_level(pLevelId):
    """Retourne un niveau ; refuse un identifiant inconnu."""

    rLevel = load_levels().get(pLevelId)

    if rLevel is None:
        raise HTTPException(status_code=404, detail="Niveau inconnu.")

    return rLevel


def build_table(pResult):
    """Retourne un résultat prêt à afficher : en-têtes et cellules en texte."""

    rTable = {
        "columns": pResult["columns"],
        "rows": [[format_value(vValue) for vValue in vRow] for vRow in pResult["rows"]],
        "truncated": pResult["truncated"],
        "changed": pResult["changed"],
    }

    return rTable


def render_sql(pRequest, pOverview, pValues):
    """Affiche la page avec les niveaux par série et le niveau demandé."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "sql.html",
        {
            "active_page": "sql",
            "overview": pOverview,
            "dialects": DIALECTS,
            "schema": build_schema(),
            "level_xp": XP_RULES["sql_level"][1],
            "max_query_length": MAX_QUERY_LENGTH,
            "max_rows": MAX_ROWS,
            **pValues,
        },
    )

    return rResponse


def describe_level(pLevel, pDialect, pQuery):
    """Retourne les valeurs d'affichage d'un niveau dans un dialecte."""

    rValues = {
        "level": pLevel,
        "hint": pick(pLevel, "hint", pDialect),
        "solution": pick(pLevel, "solution", pDialect),
        "query": pQuery,
    }

    return rValues


@router.get("/sql", response_class=HTMLResponse)
def show_sql(
    request: Request,
    pLevelId: str = Query("", alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les niveaux, et le niveau choisi avec la dernière requête essayée."""

    vOverview = build_sql_overview(pDatabaseFile)
    vValues = {}

    if pLevelId:
        vLevel = check_level(pLevelId)
        vQuery = next(
            vRow["query"]
            for vSeries in vOverview["series"]
            for vRow in vSeries["rows"]
            if vRow["id"] == pLevelId
        )
        vValues = describe_level(vLevel, vOverview["dialect"], vQuery)

    rResponse = render_sql(request, vOverview, vValues)

    return rResponse


@router.post(
    "/sql/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def run_sql(
    request: Request,
    pLevelId: str = Form(alias="level"),
    pQuery: str = Form("", alias="query", max_length=MAX_QUERY_LENGTH),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Exécute la requête sur une base neuve et la compare au résultat attendu."""

    vLevel = check_level(pLevelId)
    vDialect = build_sql_overview(pDatabaseFile)["dialect"]
    vRun = run_level(vLevel, pQuery, vDialect)
    vFirst = False

    if not vRun["result"]["error"]:
        vFirst = save_attempt(pDatabaseFile, pLevelId, pQuery, vRun["passed"])

    rResponse = render_sql(
        request,
        build_sql_overview(pDatabaseFile),
        {
            **describe_level(vLevel, vDialect, pQuery),
            "run": vRun,
            "first": vFirst,
            "result": build_table(vRun["result"]),
            "expected": build_table(vRun["expected"]),
        },
    )

    return rResponse


@router.post("/sql/dialect", dependencies=[Depends(require_csrf)])
def change_sql_dialect(
    pDialect: str = Form(alias="dialect"),
    pLevelId: str = Form("", alias="level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le dialecte choisi et revient au niveau ouvert."""

    if pDialect not in DIALECTS:
        raise HTTPException(status_code=400, detail="Dialecte inconnu.")

    save_dialect(pDatabaseFile, pDialect)
    vUrl = router.url_path_for("show_sql")

    if pLevelId:
        check_level(pLevelId)
        vUrl += "?" + urlencode({"level": pLevelId})

    rResponse = RedirectResponse(vUrl, status_code=303)

    return rResponse
