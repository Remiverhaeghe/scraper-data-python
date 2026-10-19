"""Page du profil du candidat et import d'un CV"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
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
from job.interview_drill import get_due_cards, grade_card
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
    pDatabaseFile: str = Depends(get_database_file),
):
    """Enregistre le profil saisi, ou réaffiche le formulaire avec l'erreur."""

    vTexts = {
        "name": pName,
        "headline": pHeadline,
        "skills": pSkills,
        "experiences": pExperiences,
        "cv_variants": pCvVariants,
    }

    try:
        vProfile = build_profile(pName, pHeadline, pSkills, pExperiences, pCvVariants)

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
