"""Pages des puzzles de code : série en cours, réponse corrigée, récapitulatif"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from job.code_puzzles import answer_puzzle, build_puzzle_view, start_series
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()


def render_puzzles(
    pRequest, pDatabaseFile, pFeedback=None, pMessage="", pStatusCode=200
):
    """Affiche la progression, le puzzle en cours ou le bilan de la dernière série."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "puzzles.html",
        {
            "active_page": "challenges",
            "view": build_puzzle_view(pDatabaseFile),
            "feedback": pFeedback,
            "retry_message": pMessage,
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/puzzles", response_class=HTMLResponse)
def show_puzzles(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche les puzzles de code."""

    rResponse = render_puzzles(request, pDatabaseFile)

    return rResponse


@router.post("/puzzles/start", dependencies=[Depends(require_csrf)])
def start_puzzles(pDatabaseFile: str = Depends(get_database_file)):
    """Tire une nouvelle série de puzzles."""

    start_series(pDatabaseFile)

    rResponse = RedirectResponse(
        router.url_path_for("show_puzzles") + "#puzzle", status_code=303
    )

    return rResponse


@router.post(
    "/puzzles/answer", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def answer_puzzles(
    request: Request,
    pPosition: int = Form(alias="position"),
    pChoice: int | None = Form(None, alias="choice"),
    pText: str = Form("", alias="text"),
    pIndexes: list[int] = Form([], alias="indexes"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Corrige la réponse au puzzle en cours ; une saisie illisible est reposée."""

    vPuzzle = build_puzzle_view(pDatabaseFile)["puzzle"]
    vType = vPuzzle["type"] if vPuzzle else ""
    vResponse = {"ordre": pIndexes, "saisie": pText, "ligne": pChoice}.get(vType)

    try:
        vFeedback = answer_puzzle(pDatabaseFile, pPosition, vResponse, datetime.now())

    except ValueError as vError:
        return render_puzzles(
            request, pDatabaseFile, pMessage=str(vError), pStatusCode=400
        )

    rResponse = render_puzzles(request, pDatabaseFile, {**vFeedback, "puzzle": vPuzzle})

    return rResponse
