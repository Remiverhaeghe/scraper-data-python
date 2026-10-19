"""Pages de suivi : qualité des données, journaux et historique des exécutions"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from job.offer_purge import find_offers_to_purge, parse_purge_words, purge_offers
from job.presentation import (
    CHART_PALETTE,
    EXECUTION_STATUS_LABELS,
    EXECUTION_TONES,
    UNKNOWN_SEARCH,
    describe_search,
    describe_sources,
    summarize_history,
)
from job.quality import (
    PROBLEMS_HELP,
    build_quality_export,
    describe_problems,
    get_quality_report,
)
from job.statistics import (
    EXECUTION_AXES,
    EXECUTION_CHART_SIZE,
    get_contract_shares,
    get_execution_counts,
    get_source_shares,
)
from storage.history_repository import get_history, get_history_summary
from utils.log_reader import (
    LEVEL_FILTERS,
    LEVEL_TONES,
    MAX_LOG_ENTRIES,
    clear_logs,
    export_logs,
    read_log_entries,
)
from utils.logger import get_logger, get_retention_days
from web.dependencies import get_database_file, require_csrf
from web.rendering import (
    TONE_ICONS,
    build_bar_chart,
    build_pie,
    get_message_tone,
    templates,
)

logger = get_logger(__name__)

router = APIRouter()


MAX_DISPLAYED_EXECUTIONS = 200


def render_quality(pRequest, pDatabaseFile, pPurge=None, pStatusCode=200):
    """Affiche le remplissage des champs, puis la purge des offres hors sujet."""

    vReport = get_quality_report(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        pRequest,
        "quality.html",
        {
            "active_page": "quality",
            "purge": pPurge or {"words": "", "offers": None, "message": None},
            "message_tone": get_message_tone(pStatusCode),
            "report": vReport,
            "problems_text": describe_problems(vReport["problems"]),
            "problems_help": PROBLEMS_HELP,
            "chart": build_bar_chart(
                vReport["columns"],
                [
                    (
                        "Remplissage",
                        [
                            f"var(--{vRate['tone']})"
                            for vRate in vReport["total"]["rates"]
                        ],
                        [vRate["rate"] for vRate in vReport["total"]["rates"]],
                    )
                ],
                pAxes=("Champ", "% des offres renseignées"),
                pEmptyText="Aucune offre en base pour le moment",
                pFillWidth=True,
            ),
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/quality", response_class=HTMLResponse)
def show_quality(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la page de qualité des données."""

    rResponse = render_quality(request, pDatabaseFile)

    return rResponse


@router.post(
    "/quality/purge/preview",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def preview_purge(
    request: Request,
    pWords: str = Form("", alias="words"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Liste les offres hors sujet qui seraient supprimées."""

    try:
        vOffers = find_offers_to_purge(pDatabaseFile, parse_purge_words(pWords))

    except ValueError as vException:
        rResponse = render_quality(
            request,
            pDatabaseFile,
            {"words": pWords, "offers": None, "message": str(vException)},
            400,
        )

    else:
        rResponse = render_quality(
            request,
            pDatabaseFile,
            {
                "words": pWords,
                "offers": vOffers,
                "message": (
                    f"{len(vOffers)} offre(s) seraient supprimées."
                    if vOffers
                    else "Aucune offre à supprimer pour ces mots."
                ),
            },
        )

    return rResponse


@router.post(
    "/quality/purge",
    response_class=HTMLResponse,
    dependencies=[Depends(require_csrf)],
)
def run_purge(
    request: Request,
    pWords: str = Form("", alias="words"),
    pConfirm: str = Form("", alias="confirm"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Supprime les offres hors sujet, après confirmation et sauvegarde."""

    vPurge = {"words": pWords, "offers": None}

    try:
        vWords = parse_purge_words(pWords)

        if pConfirm != "1":
            raise ValueError("Cochez la case de confirmation pour supprimer.")

        vCount, vBackupFile = purge_offers(pDatabaseFile, vWords, datetime.now())

    except ValueError as vException:
        rResponse = render_quality(
            request, pDatabaseFile, {**vPurge, "message": str(vException)}, 400
        )

    except Exception:
        logger.exception("Échec de la purge des offres depuis le web")

        rResponse = render_quality(
            request,
            pDatabaseFile,
            {**vPurge, "message": "La suppression a échoué. Voir les journaux."},
            500,
        )

    else:
        rResponse = render_quality(
            request,
            pDatabaseFile,
            {
                **vPurge,
                "message": f"{vCount} offre(s) supprimée(s)"
                + (f", sauvegarde : {vBackupFile.name}" if vBackupFile else "")
                + ". Ajoutez ces mots aux mots à exclure de vos recherches pour "
                "qu'elles ne reviennent pas.",
            },
        )

    return rResponse


@router.get("/quality/export")
def export_quality(pDatabaseFile: str = Depends(get_database_file)):
    """Télécharge le CSV des offres incomplètes ou mal découpées."""

    rResponse = Response(
        build_quality_export(pDatabaseFile),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="offres-a-verifier-{datetime.now():%Y%m%d}.csv"'
            )
        },
    )

    return rResponse


@router.get("/logs", response_class=HTMLResponse)
def show_logs(
    request: Request,
    pLevel: str = Query("", alias="level"),
    pSearch: str = Query("", alias="search"),
):
    """Affiche les derniers logs, filtrables par niveau et par texte."""

    vLevel = pLevel if pLevel in LEVEL_FILTERS else None
    vSearch = pSearch.strip() or None

    rResponse = templates.TemplateResponse(
        request,
        "logs.html",
        {
            "active_page": "logs",
            "entries": read_log_entries(pLevel=vLevel, pSearch=vSearch),
            "level": vLevel,
            "search": vSearch,
            "level_filters": LEVEL_FILTERS,
            "level_tones": LEVEL_TONES,
            "max_entries": MAX_LOG_ENTRIES,
            "retention_days": get_retention_days(),
        },
    )

    return rResponse


@router.get("/logs/download")
def download_logs():
    """Télécharge tous les journaux conservés dans un seul fichier texte."""

    rResponse = PlainTextResponse(
        export_logs(),
        headers={
            "Content-Disposition": (
                f'attachment; filename="journaux-{datetime.now():%Y%m%d}.log"'
            )
        },
    )

    return rResponse


@router.post("/logs/clear", dependencies=[Depends(require_csrf)])
def clear_logs_page():
    """Efface tous les journaux, puis revient à leur page."""

    clear_logs()

    rResponse = RedirectResponse(router.url_path_for("show_logs"), status_code=303)

    return rResponse


# Historique des exécutions et paramètres.
@router.get("/history", response_class=HTMLResponse)
def show_history(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche la synthèse, les graphiques et la liste des dernières exécutions."""

    vExecutionCounts = get_execution_counts(pDatabaseFile)

    vExecutions = [
        {
            "started_at": vEntry.started_at,
            "search": (
                describe_search(vEntry.parameters) or UNKNOWN_SEARCH
                if vEntry.scraper_type == "job"
                else f"Livres · {vEntry.url}"
            ),
            "sources": describe_sources(vEntry.parameters),
            "item_count": vEntry.item_count,
            "duration": f"{vEntry.duration_seconds:.1f} s",
            "status": EXECUTION_STATUS_LABELS.get(vEntry.status, vEntry.status),
            "tone": EXECUTION_TONES.get(vEntry.status, "danger"),
            "error_message": vEntry.error_message,
        }
        for vEntry in get_history(pDatabaseFile, pLimit=MAX_DISPLAYED_EXECUTIONS)
    ]

    rResponse = templates.TemplateResponse(
        request,
        "history.html",
        {
            "active_page": "history",
            "summary": summarize_history(get_history_summary(pDatabaseFile)),
            "source_pie": build_pie(get_source_shares(pDatabaseFile)),
            "contract_pie": build_pie(get_contract_shares(pDatabaseFile)),
            "execution_chart": build_bar_chart(
                [vLabel for vLabel, _ in vExecutionCounts],
                [
                    (
                        "Offres",
                        CHART_PALETTE[0],
                        [vCount for _, vCount in vExecutionCounts],
                    )
                ],
                pAxes=EXECUTION_AXES,
                pEmptyText="Aucune exécution pour le moment",
            ),
            "execution_chart_size": EXECUTION_CHART_SIZE,
            "executions": vExecutions,
            "unknown_search": UNKNOWN_SEARCH,
            "tone_icons": TONE_ICONS,
        },
    )

    return rResponse
