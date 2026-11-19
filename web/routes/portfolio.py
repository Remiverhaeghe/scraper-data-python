"""Page Projets : fiche portfolio et préparation d'entretien sur un projet réel"""

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response

from job.portfolio_projects import PROJECTS, get_project
from job.portfolio_sheet import (
    build_portfolio_sheet,
    render_sheet_text,
    write_sheet_pdf,
)
from job.project_interview import (
    NUMBERS_NOTICE,
    build_project_questions,
    render_questions_text,
)
from web.rendering import templates

router = APIRouter()


def find_project(pId):
    """Retourne le projet demandé, ou une erreur 404 s'il est inconnu."""

    try:
        rProject = get_project(pId)

    except KeyError as vException:
        raise HTTPException(status_code=404, detail="Projet inconnu.") from vException

    return rProject


def build_download(pContent, pFileName, pMediaType):
    """Retourne un fichier à télécharger sous le nom donné."""

    rResponse = Response(
        pContent,
        media_type=pMediaType,
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(pFileName)
        },
    )

    return rResponse


@router.get("/portfolio", response_class=HTMLResponse)
def show_portfolio(request: Request, pProject: str = Query("", alias="project")):
    """Affiche la fiche d'un projet et les questions d'entretien qui s'y rapportent."""

    vProject = find_project(pProject or PROJECTS[0]["id"])

    rResponse = templates.TemplateResponse(
        request,
        "portfolio.html",
        {
            "active_page": "portfolio",
            "projects": PROJECTS,
            "project": vProject,
            "sheet": build_portfolio_sheet(vProject),
            "questions": build_project_questions(vProject),
            "numbers_notice": NUMBERS_NOTICE,
        },
    )

    return rResponse


@router.get("/portfolio/pdf")
def download_portfolio_pdf(pProject: str = Query(alias="project")):
    """Télécharge la fiche d'un projet en PDF."""

    vSheet = build_portfolio_sheet(find_project(pProject))

    rResponse = build_download(
        write_sheet_pdf(vSheet),
        f"Fiche projet {vSheet['title']}.pdf",
        "application/pdf",
    )

    return rResponse


@router.get("/portfolio/text")
def download_portfolio_text(
    pProject: str = Query(alias="project"),
    pKind: str = Query("sheet", alias="kind", pattern="^(sheet|questions)$"),
):
    """Télécharge la fiche ou les questions d'entretien d'un projet en texte."""

    vProject = find_project(pProject)

    if pKind == "questions":
        vText = render_questions_text(vProject, build_project_questions(vProject))
        vFileName = f"Entretien {vProject['name']}.txt"
    else:
        vText = render_sheet_text(build_portfolio_sheet(vProject))
        vFileName = f"Fiche projet {vProject['name']}.txt"

    rResponse = build_download(
        vText.encode("utf-8"), vFileName, "text/plain; charset=utf-8"
    )

    return rResponse
