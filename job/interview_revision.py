"""Révision ciblée sur une offre : thèmes à revoir avant l'entretien et examen blanc

Les thèmes retenus sont ceux dont l'offre demande les compétences, repérées
comme pour le classement des thèmes conseillés de la page Révision.
"""

import random

from job.preparation import get_offer_skills, get_offer_text, match_offer
from job.profile import load_profile
from job.quiz import (
    MIN_MATCHED_SKILLS,
    build_quiz_overview,
    find_skills_in_text,
    index_skills,
)
from job.quiz_exam import EXAM_QUESTION_COUNT, start_exam
from utils.logger import get_logger

logger = get_logger(__name__)


def find_offer_themes(pQuiz, pOffer):
    """Retourne, par thème concerné par l'offre, les compétences qu'elle demande.

    Une compétence reconnue à l'enrichissement suffit ; dans le texte seul, il en
    faut deux, pour qu'un mot générique ne rattache pas l'offre à un thème.
    """

    vDetected = {vSkill.lower() for vSkill in get_offer_skills(pOffer)}
    vIndex = index_skills(
        {
            vSkill.strip()
            for vTheme in pQuiz.values()
            for vSkill in vTheme["skills"]
            if vSkill.strip()
        }
    )
    vFound = {
        vSkill.lower() for vSkill in find_skills_in_text(get_offer_text(pOffer), vIndex)
    }

    rThemes = {}

    for vKey, vTheme in pQuiz.items():
        vSkills = [vSkill for vSkill in vTheme["skills"] if vSkill.strip()]
        vDirect = [vSkill for vSkill in vSkills if vSkill.lower() in vDetected]
        vInText = [vSkill for vSkill in vSkills if vSkill.lower() in vFound]

        if vDirect or (
            vSkills and len(vInText) >= min(MIN_MATCHED_SKILLS, len(vSkills))
        ):
            rThemes[vKey] = list(dict.fromkeys(vDirect + vInText))

    return rThemes


def build_offer_revision(pDatabaseFile, pQuiz, pOffer):
    """Retourne les thèmes à revoir pour une offre, les moins maîtrisés d'abord."""

    vMatches = find_offer_themes(pQuiz, pOffer)
    vThemes = sorted(
        (
            {**vTheme, "matched": vMatches[vTheme["key"]]}
            for vTheme in build_quiz_overview(pDatabaseFile, pQuiz)
            if vTheme["key"] in vMatches
        ),
        key=lambda pTheme: (pTheme["score"], pTheme["label"]),
    )
    vQuestionCount = sum(vTheme["total"] for vTheme in vThemes)

    rRevision = {
        "themes": vThemes,
        "exam_count": min(EXAM_QUESTION_COUNT, vQuestionCount),
    }

    return rRevision


def describe_offer_exam(pOffer):
    """Retourne le titre de l'examen blanc d'une offre."""

    rTitle = f"Entretien : {pOffer.get('title') or 'offre sans titre'}"

    if pOffer.get("company"):
        rTitle += f" chez {pOffer['company']}"

    return rTitle


def start_skills_exam(
    pDatabaseFile,
    pQuiz,
    pSkills,
    pNow,
    pRandom=random,
    pTitle="Compétences prioritaires du marché",
):
    """Commence un examen blanc sur les thèmes de compétences données : celles à
    travailler en priorité d'après Mon marché, ou celles qui manquent pour une offre.

    Lève ValueError si aucun thème de révision ne couvre ces compétences.
    """

    vKeys = find_offer_themes(pQuiz, {"skills": list(pSkills)})

    if not vKeys:
        raise ValueError(
            "Aucun thème de révision ne couvre ces compétences : préparez-en les "
            "questions avec ChatGPT depuis la page Compétences."
        )

    logger.info("Examen blanc « %s » : %s thème(s)", pTitle, len(vKeys))

    rExam = start_exam(
        pDatabaseFile,
        pQuiz,
        None,
        pNow,
        pRandom,
        pThemeKeys=set(vKeys),
        pTitle=pTitle,
    )

    return rExam


def start_missing_skills_exam(pDatabaseFile, pQuiz, pOffer, pNow, pRandom=random):
    """Commence un examen blanc limité aux compétences de l'offre absentes du profil.

    Lève ValueError si le profil les couvre toutes ou si aucun thème ne les couvre.
    """

    vMissing = match_offer(load_profile(pDatabaseFile), pOffer)["missing"]

    if not vMissing:
        raise ValueError(
            "Votre profil couvre déjà toutes les compétences repérées dans l'offre."
        )

    rExam = start_skills_exam(
        pDatabaseFile,
        pQuiz,
        vMissing,
        pNow,
        pRandom,
        pTitle=f"Compétences manquantes · {describe_offer_exam(pOffer)}",
    )

    return rExam


def start_offer_exam(pDatabaseFile, pQuiz, pOffer, pNow, pRandom=random):
    """Commence un examen blanc sur les thèmes demandés par une offre.

    Lève ValueError si aucun thème ne correspond à l'offre.
    """

    vKeys = find_offer_themes(pQuiz, pOffer)

    if not vKeys:
        raise ValueError(
            "Aucun thème de révision ne correspond aux compétences de cette offre."
        )

    logger.info(
        "Examen blanc pour l'offre %s/%s : %s thème(s)",
        pOffer.get("source"),
        pOffer.get("source_id"),
        len(vKeys),
    )

    rExam = start_exam(
        pDatabaseFile,
        pQuiz,
        None,
        pNow,
        pRandom,
        pThemeKeys=set(vKeys),
        pTitle=describe_offer_exam(pOffer),
        pOfferKey=(pOffer.get("source"), str(pOffer.get("source_id"))),
    )

    return rExam
