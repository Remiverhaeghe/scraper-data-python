"""Pages de la révision : questions, examen, import et export des questions"""

import random
import re
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from markupsafe import Markup
from starlette.background import BackgroundTask

from job.assistant import CHATGPT_URL
from job.presentation import CHART_PALETTE
from job.quiz import (
    DEFAULT_MODE,
    QUIZ_MODES,
    THEME_STATUSES,
    answer_question,
    build_quiz_overview,
    build_quiz_statistics,
    describe_no_question,
    find_question,
    flag_question,
    get_next_review,
    get_review_schedule,
    load_active_quiz,
    pick_question,
)
from job.interview_revision import start_offer_exam
from job.quiz_domains import (
    DOMAIN_ICONS,
    build_category_progress,
    filter_guides,
    count_categories,
    group_themes,
)
from job.quiz_exam import (
    EXAM_QUESTION_COUNT,
    answer_exam,
    describe_exam_results,
    describe_exam_summary,
    format_countdown,
    get_exam_question,
    get_remaining_seconds,
    load_exam,
    load_exam_results,
    start_exam,
    stop_exam,
    summarize_exam,
)
from job.quiz_generation import (
    DEFAULT_GENERATION_COUNT,
    GENERATION_COUNTS,
    GENERATION_LEVELS,
    load_catalog,
    MIXED_LEVEL,
    TARGET_QUESTIONS,
    build_correction_prompt,
    build_generation_prompt,
    build_priority_themes,
    list_generation_themes,
)
from job.quiz_import import (
    IMPORT_EXTENSIONS,
    clear_imported_questions,
    describe_import_details,
    describe_quiz_import,
    export_quiz_pack,
    get_import_tone,
    import_questions,
    import_questions_file,
)
from job.quiz_packs import import_validated_packs, list_validated_packs
from job.quiz_types import build_response, prepare_question
from storage.job_offers import get_offer
from storage.quiz_answers import get_last_answers
from storage.quiz_questions import get_quiz_asset, get_quiz_guide, get_quiz_guides
from utils.markdown import render_markdown
from web.dependencies import get_database_file, require_csrf
from web.rendering import build_bar_chart, get_message_tone, templates

router = APIRouter()


# Schémas des questions importées : nom produit à l'import, et SVG sans script
QUIZ_ASSET_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*\.svg")


QUIZ_ASSET_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


# Archive de questions de révision envoyée depuis le web
MAX_QUIZ_UPLOAD_BYTES = 20 * 1024 * 1024


def render_quiz(
    pRequest,
    pDatabaseFile,
    pTheme=None,
    pMode=DEFAULT_MODE,
    pResult=None,
    pImport=None,
    pStatusCode=200,
    pDomain=None,
    pSubdomain=None,
    pRetry=None,
):
    """Affiche les thèmes de révision, avec une question ou une correction.

    pImport porte la saisie, la demande ChatGPT et le message de l'ajout de
    questions ; pRetry, la question à reposer et la raison du refus de sa
    réponse.
    """

    vQuiz = load_active_quiz(pDatabaseFile)
    vMode = pMode if pMode in QUIZ_MODES else DEFAULT_MODE
    vTheme = pTheme if pTheme in vQuiz else None
    vQuestion = None

    vSchedule = get_review_schedule(pDatabaseFile)

    if pRetry:
        vQuestion = {**prepare_question(pRetry[0], random), "theme_key": vTheme}
    elif vTheme and pResult is None:
        vQuestion = pick_question(
            vQuiz,
            vTheme,
            vMode,
            get_last_answers(pDatabaseFile),
            pSchedule=vSchedule,
        )

    vThemes = build_quiz_overview(pDatabaseFile, vQuiz)
    vStatistics = build_quiz_statistics(pDatabaseFile, vThemes, datetime.now())

    rResponse = templates.TemplateResponse(
        pRequest,
        "quiz.html",
        {
            "active_page": "quiz",
            "themes": vThemes,
            "themes_by_key": {vItem["key"]: vItem for vItem in vThemes},
            "theme": vTheme,
            "mode": vMode,
            "modes": QUIZ_MODES,
            "question": vQuestion,
            "retry_message": pRetry[1] if pRetry else None,
            "result": pResult,
            "no_question": (
                describe_no_question(vMode, get_next_review(vQuiz, vTheme, vSchedule))
                if vTheme and vQuestion is None
                else None
            ),
            "import_form": pImport or {},
            "message_tone": (pImport or {}).get("tone")
            or get_message_tone(pStatusCode),
            "generation_themes": list_generation_themes(vThemes),
            "priorities": build_priority_themes(pDatabaseFile, vQuiz),
            "target_questions": TARGET_QUESTIONS,
            "mixed_level": MIXED_LEVEL,
            "packs_count": len(list_validated_packs()),
            "default_count": DEFAULT_GENERATION_COUNT,
            "domains": [vDomain for vDomain, _ in group_themes(vThemes)],
            "exam": load_exam(pDatabaseFile),
            "exam_count": EXAM_QUESTION_COUNT,
            "domain": pDomain,
            "subdomains": (
                [
                    vSubdomain
                    for _, vSections in group_themes(vThemes, pDomain)
                    for vSubdomain, _ in vSections
                ]
                if pDomain
                else []
            ),
            "subdomain": pSubdomain,
            "groups": group_themes(vThemes, pDomain, pSubdomain),
            "categories": count_categories(vThemes),
            "empty_themes": [
                vTheme
                for vTheme in load_catalog()
                if pDomain in (None, vTheme["domain"])
                and pSubdomain in (None, vTheme["subdomain"])
            ],
            "all_groups": group_themes(vThemes),
            "category_progress": build_category_progress(vThemes),
            "theme_count": len(vThemes),
            "theme_statuses": THEME_STATUSES,
            "domain_icons": DOMAIN_ICONS,
            "guides": filter_guides(
                get_quiz_guides(pDatabaseFile), vThemes, pDomain, pSubdomain
            ),
            "levels": GENERATION_LEVELS,
            "generation_counts": GENERATION_COUNTS,
            "import_extensions": ",".join(IMPORT_EXTENSIONS),
            "chatgpt_url": CHATGPT_URL,
            "statistics": vStatistics,
            "statistics_chart": build_bar_chart(
                [f"{vDay:%d/%m}" for vDay, _, _ in vStatistics["days"]],
                [
                    (
                        "Réponses",
                        CHART_PALETTE[0],
                        [vCount for _, vCount, _ in vStatistics["days"]],
                    ),
                    (
                        "Bonnes réponses",
                        CHART_PALETTE[1],
                        [vCorrect for _, _, vCorrect in vStatistics["days"]],
                    ),
                ],
                pAxes=("Jour", "Réponses par jour"),
                pEmptyText="Aucune réponse ces 14 derniers jours",
            ),
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/quiz", response_class=HTMLResponse)
def show_quiz(
    request: Request,
    pTheme: str = Query("", alias="theme"),
    pMode: str = Query(DEFAULT_MODE, alias="mode"),
    pDomain: str = Query("", alias="domain"),
    pSubdomain: str = Query("", alias="subdomain"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les thèmes de révision et, si un thème est choisi, une question."""

    rResponse = render_quiz(
        request,
        pDatabaseFile,
        pTheme,
        pMode,
        pDomain=pDomain or None,
        pSubdomain=pSubdomain or None,
    )

    return rResponse


def read_point(pX, pY):
    """Retourne le point cliqué sur l'image d'une question « zone », ou None."""

    rPoint = (pX, pY) if pX is not None and pY is not None else None

    return rPoint


@router.post(
    "/quiz/answer", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def answer_quiz(
    request: Request,
    pQuestionId: str = Form(alias="question_id"),
    pChoice: int | None = Form(None, alias="choice"),
    pText: str = Form("", alias="text"),
    pIndexes: list[int] = Form([], alias="indexes"),
    pPointX: int | None = Form(None, alias="point.x"),
    pPointY: int | None = Form(None, alias="point.y"),
    pMode: str = Form(DEFAULT_MODE, alias="mode"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Corrige une réponse et affiche son explication ; une saisie illisible est reposée."""

    vQuiz = load_active_quiz(pDatabaseFile)
    vQuestion, vThemeKey = find_question(vQuiz, pQuestionId)

    if vQuestion is None:
        raise HTTPException(status_code=400, detail="Question ou réponse inconnue.")

    try:
        vResult = answer_question(
            pDatabaseFile,
            vQuiz,
            pQuestionId,
            build_response(
                vQuestion, pChoice, pText, pIndexes, read_point(pPointX, pPointY)
            ),
            datetime.now(),
        )

    except ValueError as vException:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            vThemeKey,
            pMode,
            pStatusCode=400,
            pRetry=(vQuestion, str(vException)),
        )

    else:
        rResponse = render_quiz(
            request, pDatabaseFile, vThemeKey, pMode, pResult=vResult
        )

    return rResponse


@router.post(
    "/quiz/prompt", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def prepare_quiz_prompt(
    request: Request,
    pTheme: str = Form("", alias="theme"),
    pLevel: str = Form(MIXED_LEVEL, alias="level"),
    pCount: int = Form(DEFAULT_GENERATION_COUNT, alias="count"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Prépare la demande de questions à copier dans ChatGPT."""

    vForm = {"theme": pTheme, "level": pLevel, "count": pCount}

    if not pTheme.strip() or pCount not in GENERATION_COUNTS:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={**vForm, "message": "Choisissez un thème et un nombre proposé."},
            pStatusCode=400,
        )

    else:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={
                **vForm,
                "prompt": build_generation_prompt(
                    load_active_quiz(pDatabaseFile), pTheme, pLevel, pCount
                ),
            },
        )

    return rResponse


@router.post(
    "/quiz/import", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def import_quiz_questions(
    request: Request,
    pTheme: str = Form("", alias="theme"),
    pText: str = Form("", alias="text"),
    pFile: UploadFile | None = File(None, alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Importe des questions collées ou envoyées en fichier (.json ou .zip)."""

    try:
        if pFile is not None and pFile.filename:
            # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
            vContent = pFile.file.read(MAX_QUIZ_UPLOAD_BYTES + 1)

            if len(vContent) > MAX_QUIZ_UPLOAD_BYTES:
                raise ValueError("Fichier trop volumineux.")

            vReport = import_questions_file(
                pDatabaseFile, pTheme, pFile.filename, vContent, datetime.now()
            )
        else:
            vReport = import_questions(pDatabaseFile, pTheme, pText, datetime.now())

    except ValueError as vException:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"theme": pTheme, "text": pText, "message": str(vException)},
            pStatusCode=400,
        )

    else:
        rResponse = render_import_report(request, pDatabaseFile, vReport, pTheme)

    return rResponse


def render_import_report(pRequest, pDatabaseFile, pReport, pTheme=""):
    """Affiche la révision avec le bilan d'un import : message, détail, correction."""

    rResponse = render_quiz(
        pRequest,
        pDatabaseFile,
        pImport={
            "theme": pTheme,
            "message": describe_quiz_import(pReport),
            "details": describe_import_details(pReport),
            "tone": get_import_tone(pReport),
            "correction": (
                build_correction_prompt(pReport["review"]) if pReport["review"] else ""
            ),
        },
    )

    return rResponse


@router.post(
    "/quiz/import-packs",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def import_quiz_packs(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Importe d'un coup les archives validées du dossier des lots."""

    try:
        vReport = import_validated_packs(pDatabaseFile, datetime.now())

    except ValueError as vException:
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"message": str(vException)},
            pStatusCode=400,
        )

    else:
        rResponse = render_import_report(request, pDatabaseFile, vReport)

    return rResponse


@router.get("/quiz/export")
def download_quiz_pack(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Télécharge les questions importées dans un pack .zip réimportable."""

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as vFile:
        vPath = Path(vFile.name)

    try:
        export_quiz_pack(pDatabaseFile, vPath)

    except ValueError as vException:
        vPath.unlink(missing_ok=True)

        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"message": str(vException)},
            pStatusCode=400,
        )

    else:
        # Le fichier temporaire est supprimé une fois envoyé.
        rResponse = FileResponse(
            vPath,
            media_type="application/zip",
            filename=f"questions-revision-{datetime.now():%Y%m%d}.zip",
            background=BackgroundTask(vPath.unlink, missing_ok=True),
        )

    return rResponse


@router.get("/quiz/asset/{pName}")
def show_quiz_asset(pName: str, pDatabaseFile: str = Depends(get_database_file)):
    """Sert le schéma SVG d'une question importée."""

    vContent = (
        get_quiz_asset(pDatabaseFile, pName)
        if QUIZ_ASSET_PATTERN.fullmatch(pName)
        else None
    )

    if vContent is None:
        raise HTTPException(status_code=404)

    # Vérifié sans script à l'import ; ouvert seul dans un onglet, le SVG reste
    # en plus isolé et privé de tout script par sa politique de sécurité.
    rResponse = Response(
        vContent,
        media_type="image/svg+xml",
        headers={"Content-Security-Policy": QUIZ_ASSET_POLICY},
    )

    return rResponse


@router.get("/quiz/guide/{pName}", response_class=HTMLResponse)
def show_quiz_guide(
    request: Request, pName: str, pDatabaseFile: str = Depends(get_database_file)
):
    """Affiche un guide pratique importé avec les questions."""

    vGuide = get_quiz_guide(pDatabaseFile, pName)

    if vGuide is None:
        raise HTTPException(status_code=404)

    rResponse = templates.TemplateResponse(
        request,
        "guide.html",
        {
            "active_page": "quiz",
            "guide": vGuide,
            # Texte échappé puis mis en forme par render_markdown : HTML sûr.
            "content": Markup(render_markdown(vGuide["content"])),  # nosec B704
        },
    )

    return rResponse


@router.post("/quiz/exam/start", dependencies=[Depends(require_csrf)])
def begin_quiz_exam(
    request: Request,
    pDomain: str = Form("", alias="domain"),
    pSubdomain: str = Form("", alias="subdomain"),
    pSource: str = Form("", alias="source"),
    pSourceId: str = Form("", alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Commence un examen sur une catégorie ou une offre, ou reprend celui en cours."""

    vExam = load_exam(pDatabaseFile)
    vOffer = get_offer(pDatabaseFile, pSource, pSourceId) if pSource else None

    if pSource and vOffer is None:
        raise HTTPException(status_code=404, detail="Offre introuvable.")

    if not vExam or vExam["finished_at"]:
        try:
            vQuiz = load_active_quiz(pDatabaseFile)

            if vOffer:
                start_offer_exam(pDatabaseFile, vQuiz, vOffer, datetime.now())
            else:
                start_exam(
                    pDatabaseFile,
                    vQuiz,
                    pDomain or None,
                    datetime.now(),
                    pSubdomain=pSubdomain or None,
                )

        except ValueError as vException:
            return render_quiz(
                request,
                pDatabaseFile,
                pImport={"message": str(vException)},
                pStatusCode=400,
            )

    rResponse = RedirectResponse(router.url_path_for("show_quiz_exam"), status_code=303)

    return rResponse


def render_exam(pRequest, pDatabaseFile, pResult=None, pMessage=None):
    """Affiche la question en cours de l'examen, sa correction ou le résultat."""

    vQuiz = load_active_quiz(pDatabaseFile)
    vExam = load_exam(pDatabaseFile)
    vRemaining = get_remaining_seconds(vExam, datetime.now())

    vSummary = None

    if vExam["finished_at"] and not pResult:
        vSummary = describe_exam_summary(summarize_exam(vQuiz, vExam))

        if vExam.get("offer"):
            vSummary += " " + describe_exam_results(
                load_exam_results(pDatabaseFile, vExam["offer"])
            )

    rResponse = templates.TemplateResponse(
        pRequest,
        "quiz_exam.html",
        {
            "active_page": "quiz",
            "exam": vExam,
            "remaining": vRemaining,
            "countdown": format_countdown(vRemaining),
            "result": pResult,
            "question": None if pResult else get_exam_question(vQuiz, vExam),
            "retry_message": pMessage,
            "summary": vSummary,
        },
    )

    return rResponse


@router.get("/quiz/exam", response_class=HTMLResponse)
def show_quiz_exam(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche l'examen en cours, ou revient à la révision s'il n'y en a pas."""

    if load_exam(pDatabaseFile) is None:
        rResponse = RedirectResponse(router.url_path_for("show_quiz"), status_code=303)
    else:
        rResponse = render_exam(request, pDatabaseFile)

    return rResponse


@router.post(
    "/quiz/exam/answer",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def answer_quiz_exam(
    request: Request,
    pChoice: int | None = Form(None, alias="choice"),
    pText: str = Form("", alias="text"),
    pIndexes: list[int] = Form([], alias="indexes"),
    pPointX: int | None = Form(None, alias="point.x"),
    pPointY: int | None = Form(None, alias="point.y"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Corrige la réponse à la question en cours ; une saisie illisible est reposée."""

    vQuiz = load_active_quiz(pDatabaseFile)
    vExam = load_exam(pDatabaseFile)

    if not vExam or vExam["finished_at"]:
        raise HTTPException(status_code=400, detail="Aucun examen en cours.")

    vQuestion = find_question(vQuiz, vExam["ids"][vExam["index"]])[0]

    try:
        vResult, _ = answer_exam(
            pDatabaseFile,
            vQuiz,
            build_response(
                vQuestion or {},
                pChoice,
                pText,
                pIndexes,
                read_point(pPointX, pPointY),
            ),
            datetime.now(),
        )

    except ValueError as vException:
        rResponse = render_exam(request, pDatabaseFile, pMessage=str(vException))

    else:
        # Question supprimée pendant l'examen : passée, la suivante s'affiche.
        rResponse = (
            render_exam(request, pDatabaseFile, vResult)
            if vResult
            else RedirectResponse(
                router.url_path_for("show_quiz_exam"), status_code=303
            )
        )

    return rResponse


@router.post("/quiz/exam/stop", dependencies=[Depends(require_csrf)])
def stop_quiz_exam(pDatabaseFile: str = Depends(get_database_file)):
    """Abandonne ou referme l'examen, puis revient à la révision."""

    stop_exam(pDatabaseFile)

    rResponse = RedirectResponse(router.url_path_for("show_quiz"), status_code=303)

    return rResponse


@router.post(
    "/quiz/clear", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def clear_quiz_questions(
    request: Request,
    pConfirm: str = Form("", alias="confirm"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Efface les questions importées après sauvegarde, sur confirmation explicite."""

    if pConfirm != "1":
        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={"message": "Cochez la case de confirmation pour supprimer."},
            pStatusCode=400,
        )

    else:
        vCount, vBackupFile = clear_imported_questions(pDatabaseFile, datetime.now())

        rResponse = render_quiz(
            request,
            pDatabaseFile,
            pImport={
                "message": f"{vCount} question(s) importée(s) effacée(s). "
                f"Sauvegarde : {vBackupFile.name}"
            },
        )

    return rResponse


@router.post("/quiz/flag", dependencies=[Depends(require_csrf)])
def flag_quiz_question(
    pQuestionId: str = Form(alias="question_id"),
    pTheme: str = Form("", alias="theme"),
    pMode: str = Form(DEFAULT_MODE, alias="mode"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Retire une question douteuse des tirages, puis propose la suivante."""

    flag_question(pDatabaseFile, pQuestionId)

    rResponse = RedirectResponse(
        f"{router.url_path_for('show_quiz')}?theme={quote(pTheme)}&mode={quote(pMode)}",
        status_code=303,
    )

    return rResponse
