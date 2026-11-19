"""Formations et certifications visées, gérées depuis la page Certifications"""

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from job.quiz import load_active_quiz
from job.skills_dashboard import get_known_skills
from job.training_goals import delete_goal, save_goal
from web.dependencies import get_database_file, require_csrf

router = APIRouter()

GOALS_ANCHOR = "/certifications#objectifs"


@router.post("/certifications/goals/save", dependencies=[Depends(require_csrf)])
async def save_training_goal(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Ajoute ou met à jour une formation ou une certification visée."""

    vForm = await request.form()

    try:
        save_goal(
            pDatabaseFile,
            {vKey: str(vValue) for vKey, vValue in vForm.items()},
            get_known_skills(load_active_quiz(pDatabaseFile)),
            date.today(),
        )

    except ValueError as vException:
        raise HTTPException(status_code=400, detail=str(vException)) from vException

    rResponse = RedirectResponse(GOALS_ANCHOR, status_code=303)

    return rResponse


@router.post("/certifications/goals/delete", dependencies=[Depends(require_csrf)])
def delete_training_goal(
    pId: str = Form(alias="id"),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Retire une formation ou une certification visée."""

    if not delete_goal(pDatabaseFile, pId):
        raise HTTPException(status_code=404, detail="Objectif inconnu.")

    rResponse = RedirectResponse(GOALS_ANCHOR, status_code=303)

    return rResponse
