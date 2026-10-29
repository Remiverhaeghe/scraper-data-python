"""Page du profil du candidat et import d'un CV"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from job.assistant import CHATGPT_URL
from job.cv_import import (
    CV_EXTENSIONS,
    MAX_CV_BYTES,
    build_cv_prompt,
    extract_profile,
    merge_profile_texts,
    read_cv_text,
)
from job.education import EDUCATION_LEVELS, get_profile_level, read_level
from job.interview_drill import get_due_cards, grade_card
from job.self_assessment import (
    KNOWN_LEVEL,
    MAX_LEVEL,
    WEAK_LEVEL,
    build_grid,
    save_skill_levels,
)
from job.interview_simulation import (
    ALL_THEMES,
    get_current_question,
    list_themes,
    load_simulation,
    record_answer,
    start_simulation,
    stop_simulation,
    summarize_simulation,
)
from job.interview_simulation import get_history as get_simulation_history
from job.interview_journal import collect_asked_questions
from job.profile import build_profile, load_profile, profile_to_texts, save_profile
from job.star_answers import (
    BEHAVIORAL_QUESTIONS,
    STAR_FIELDS,
    load_star_answers,
    save_star_answer,
)
from web.dependencies import get_database_file, require_csrf
from web.rendering import get_message_tone, templates

router = APIRouter()


def render_profile(
    pRequest,
    pDatabaseFile,
    pTexts,
    pMessage=None,
    pStatusCode=200,
    pCvPrompt=None,
    pStarMessage=None,
):
    """Affiche le formulaire du profil avec les textes donnés et les réponses STAR."""

    vAnswers = load_star_answers(pDatabaseFile)

    rResponse = templates.TemplateResponse(
        pRequest,
        "profile.html",
        {
            "active_page": "profile",
            "profile": pTexts,
            "education_levels": EDUCATION_LEVELS,
            "profile_level": get_profile_level(
                {
                    "diplomas": str(pTexts.get("diplomas") or "").splitlines(),
                    "education_level": pTexts.get("education_level"),
                }
            ),
            "message": pMessage,
            "message_tone": get_message_tone(pStatusCode),
            "cv_prompt": pCvPrompt,
            "cv_extensions": ",".join(CV_EXTENSIONS),
            "chatgpt_url": CHATGPT_URL,
            "star_questions": BEHAVIORAL_QUESTIONS,
            "star_fields": STAR_FIELDS,
            "star_answers": vAnswers,
            "star_message": pStarMessage,
            "asked_questions": collect_asked_questions(pDatabaseFile)[:5],
            "drill_cards": get_due_cards(pDatabaseFile, datetime.now()),
            **build_simulation_context(pDatabaseFile),
            "skill_grid": build_grid(load_profile(pDatabaseFile)),
            "max_level": MAX_LEVEL,
            "known_level": KNOWN_LEVEL,
            "weak_level": WEAK_LEVEL,
            "experiences": [
                vExperience["title"]
                for vExperience in load_profile(pDatabaseFile)["experiences"]
            ],
        },
        status_code=pStatusCode,
    )

    return rResponse


@router.get("/profile", response_class=HTMLResponse)
def show_profile(request: Request, pDatabaseFile: str = Depends(get_database_file)):
    """Affiche le profil du candidat."""

    rResponse = render_profile(
        request, pDatabaseFile, profile_to_texts(load_profile(pDatabaseFile))
    )

    return rResponse


@router.post(
    "/profile", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def update_profile(
    request: Request,
    pName: str = Form("", alias="name"),
    pHeadline: str = Form("", alias="headline"),
    pSkills: str = Form("", alias="skills"),
    pExperiences: str = Form("", alias="experiences"),
    pCvVariants: str = Form("", alias="cv_variants"),
    pDiploma: str = Form("", alias="diploma"),
    pEducationLevel: str = Form("", alias="education_level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le profil saisi, ou réaffiche le formulaire avec l'erreur."""

    vTexts = {
        "name": pName,
        "headline": pHeadline,
        "skills": pSkills,
        "experiences": pExperiences,
        "cv_variants": pCvVariants,
        "diplomas": pDiploma,
        "education_level": read_level(pEducationLevel),
    }

    try:
        vProfile = build_profile(
            pName,
            pHeadline,
            pSkills,
            pExperiences,
            pCvVariants,
            pDiploma,
            pEducationLevel,
        )

    except ValueError as vException:
        rResponse = render_profile(request, pDatabaseFile, vTexts, str(vException), 400)

    else:
        save_profile(pDatabaseFile, vProfile)

        rResponse = render_profile(
            request,
            pDatabaseFile,
            profile_to_texts(vProfile),
            f"Profil enregistré : {len(vProfile['skills'])} compétence(s), "
            f"{len(vProfile['experiences'])} expérience(s), "
            f"{len(vProfile['cv_variants'])} CV.",
        )

    return rResponse


@router.post(
    "/profile/cv", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
def import_cv(
    request: Request,
    pFile: UploadFile = File(alias="file"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Pré-remplit le profil depuis un CV envoyé ; rien n'est enregistré."""

    vTexts = profile_to_texts(load_profile(pDatabaseFile))

    try:
        # Un octet de plus que la limite suffit à savoir qu'elle est dépassée.
        vText = read_cv_text(pFile.filename, pFile.file.read(MAX_CV_BYTES + 1))

    except ValueError as vException:
        rResponse = render_profile(request, pDatabaseFile, vTexts, str(vException), 400)

    else:
        vExtracted = extract_profile(vText)

        rResponse = render_profile(
            request,
            pDatabaseFile,
            merge_profile_texts(vTexts, vExtracted),
            f"CV importé : {len(vExtracted['skills'])} compétence(s) repérée(s). "
            "Pour les expériences, copiez la demande pour ChatGPT ci-dessous et "
            "collez sa réponse dans le formulaire. Vérifiez puis enregistrez.",
            pCvPrompt=build_cv_prompt(vText),
        )

    return rResponse


@router.post(
    "/profile/star", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
async def update_star_answer(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre la réponse STAR d'une question ; vide, elle est retirée."""

    vForm = await request.form()
    vTexts = profile_to_texts(load_profile(pDatabaseFile))

    try:
        save_star_answer(
            pDatabaseFile,
            vForm.get("question"),
            vForm.get("experience"),
            {vName: vForm.get(vName) for vName in STAR_FIELDS},
        )

    except ValueError as vException:
        rResponse = render_profile(
            request,
            pDatabaseFile,
            vTexts,
            pStatusCode=400,
            pStarMessage=str(vException),
        )

    else:
        rResponse = render_profile(
            request, pDatabaseFile, vTexts, pStarMessage="Réponse enregistrée."
        )

    return rResponse


@router.post("/profile/levels", dependencies=[Depends(require_csrf)])
def save_profile_levels(
    pSkills: list[str] = Form([], alias="skill"),
    pLevels: list[int] = Form([], alias="level"),
    pNewSkill: str = Form("", alias="new_skill"),
    pNewLevel: int = Form(0, alias="new_level"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre la grille d'auto-évaluation, compétence ajoutée comprise."""

    if len(pSkills) != len(pLevels):
        raise HTTPException(status_code=400, detail="Grille incomplète.")

    vLevels = dict(zip(pSkills, pLevels))

    if pNewSkill.strip():
        vLevels[pNewSkill.strip()] = pNewLevel

    try:
        save_skill_levels(pDatabaseFile, vLevels)

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(
        router.url_path_for("show_profile") + "#self-assessment", status_code=303
    )

    return rResponse


def build_simulation_context(pDatabaseFile):
    """Retourne la série de simulation en cours, son bilan et l'historique."""

    vSimulation = load_simulation(pDatabaseFile)
    vQuestion = get_current_question(vSimulation)

    rContext = {
        "simulation_themes": list_themes(),
        "simulation": vSimulation,
        "simulation_question": vQuestion,
        "simulation_summary": (
            summarize_simulation(vSimulation)
            if vSimulation is not None and vQuestion is None
            else None
        ),
        "simulation_history": get_simulation_history(pDatabaseFile)[:3],
    }

    return rContext


def redirect_to_simulation():
    """Revient à la carte de simulation de la page Profil."""

    rResponse = RedirectResponse(
        router.url_path_for("show_profile") + "#simulation", status_code=303
    )

    return rResponse


@router.post("/profile/simulation/start", dependencies=[Depends(require_csrf)])
def start_interview_simulation(
    pTheme: str = Form(ALL_THEMES, alias="theme"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Commence une série de questions sur le thème choisi."""

    if pTheme not in list_themes():
        raise HTTPException(status_code=400, detail="Thème inconnu.")

    start_simulation(pDatabaseFile, pTheme, datetime.now())

    rResponse = redirect_to_simulation()

    return rResponse


@router.post("/profile/simulation/answer", dependencies=[Depends(require_csrf)])
def answer_interview_simulation(
    pPoints: list[int] = Form([], alias="points"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Note la question en cours d'après les points clés cochés."""

    try:
        record_answer(pDatabaseFile, pPoints, datetime.now())

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = redirect_to_simulation()

    return rResponse


@router.post("/profile/simulation/stop", dependencies=[Depends(require_csrf)])
def stop_interview_simulation(pDatabaseFile: str = Depends(get_database_file)):
    """Ferme la série en cours ou son bilan."""

    stop_simulation(pDatabaseFile)

    rResponse = redirect_to_simulation()

    return rResponse


@router.post("/profile/drill", dependencies=[Depends(require_csrf)])
def grade_interview_question(
    pCardId: str = Form(..., alias="card"),
    pKnown: str = Form("", alias="known"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Note une question d'entretien, puis revient au profil sur la suivante."""

    grade_card(pDatabaseFile, pCardId, pKnown == "1", datetime.now())

    rResponse = RedirectResponse(
        router.url_path_for("show_profile") + "#drill", status_code=303
    )

    return rResponse
