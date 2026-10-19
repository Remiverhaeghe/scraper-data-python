"""Réponses STAR aux questions comportementales, reliées aux expériences du profil"""

import re

from job.fingerprint import normalize
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

STAR_KEY = "star_answers"

# Questions comportementales les plus posées en entretien
BEHAVIORAL_QUESTIONS = {
    "reussite": "Parlez-moi d'une réussite dont vous êtes fier.",
    "echec": "Racontez un échec et ce que vous en avez retenu.",
    "desaccord": "Comment avez-vous géré un désaccord dans une équipe ?",
    "pression": "Décrivez une situation de forte pression ou de délai serré.",
    "initiative": "Donnez un exemple d'initiative que vous avez prise.",
    "apprentissage": "Racontez comment vous avez appris vite un nouvel outil.",
    "priorites": "Comment avez-vous arbitré entre plusieurs priorités ?",
}

STAR_FIELDS = {
    "situation": "Situation",
    "task": "Tâche",
    "action": "Action",
    "result": "Résultat",
}

# Une réponse STAR se raconte en deux minutes : au-delà, elle sera survolée.
MAX_FIELD_LENGTH = 1000


def load_star_answers(pDatabaseFile):
    """Retourne les réponses enregistrées, par clé de question."""

    rAnswers = {
        vKey: vAnswer
        for vKey, vAnswer in load_json_setting(
            pDatabaseFile, STAR_KEY, {}, dict
        ).items()
        if vKey in BEHAVIORAL_QUESTIONS and isinstance(vAnswer, dict)
    }

    return rAnswers


def save_star_answer(pDatabaseFile, pKey, pExperience, pFields):
    """Enregistre la réponse à une question ; tous les champs vides la retirent."""

    if pKey not in BEHAVIORAL_QUESTIONS:
        raise ValueError("Question comportementale inconnue.")

    vFields = {vName: (pFields.get(vName) or "").strip() for vName in STAR_FIELDS}

    if any(len(vText) > MAX_FIELD_LENGTH for vText in vFields.values()):
        raise ValueError(
            f"Réponse trop longue : {MAX_FIELD_LENGTH} caractères au plus par partie."
        )

    vAnswers = load_star_answers(pDatabaseFile)

    if any(vFields.values()):
        vAnswers[pKey] = {"experience": (pExperience or "").strip(), **vFields}
    else:
        vAnswers.pop(pKey, None)

    save_json_setting(pDatabaseFile, STAR_KEY, vAnswers)

    logger.info(
        "Réponse STAR %s : %s",
        "enregistrée" if pKey in vAnswers else "retirée",
        pKey,
    )


def suggest_star_answer(pProfile, pExperienceTitle):
    """Prépare une réponse à compléter à partir d'une expérience du profil."""

    vExperience = next(
        (
            vItem
            for vItem in pProfile["experiences"]
            if vItem["title"] == pExperienceTitle
        ),
        None,
    )

    rAnswer = {"experience": pExperienceTitle or "", **dict.fromkeys(STAR_FIELDS, "")}

    if vExperience is not None:
        rAnswer["situation"] = vExperience["title"]
        rAnswer["result"] = vExperience.get("achievement") or ""

    return rAnswer


def format_star_answer(pAnswer):
    """Met une réponse en forme, une ligne par partie renseignée."""

    rText = "\n".join(
        f"{vLabel} : {pAnswer[vName]}"
        for vName, vLabel in STAR_FIELDS.items()
        if pAnswer.get(vName)
    )

    return rText


def select_star_answers(pAnswers, pProfile, pOfferSkills):
    """Retourne les réponses préparées, celles liées aux compétences de l'offre en tête."""

    vSkills = {vSkill.casefold() for vSkill in pOfferSkills}
    vExperienceSkills = {
        vExperience["title"]: {vSkill.casefold() for vSkill in vExperience["skills"]}
        for vExperience in pProfile["experiences"]
    }

    rAnswers = []

    for vKey, vQuestion in BEHAVIORAL_QUESTIONS.items():
        vAnswer = pAnswers.get(vKey)

        if vAnswer:
            vCovered = vExperienceSkills.get(vAnswer.get("experience"), set()) & vSkills

            rAnswers.append(
                {
                    "question": vQuestion,
                    "experience": vAnswer.get("experience") or "",
                    "text": format_star_answer(vAnswer),
                    "skills": sorted(vCovered),
                }
            )

    # Tri stable : l'ordre des questions est gardé à pertinence égale.
    rAnswers.sort(key=lambda pAnswer: not pAnswer["skills"])

    return rAnswers


# Mots de l'offre, sans accents, qui annoncent une question comportementale
OFFER_SIGNALS = {
    "desaccord": (
        r"\b(equipe|collabor\w*|transverse|transversal\w*|interlocuteurs?)\b",
        "travail en équipe",
    ),
    "pression": (
        r"\b(delais?|urgences?|rythme|pression|astreintes?|production|run)\b",
        "délais et production",
    ),
    "initiative": (
        r"\b(autonom\w*|initiatives?|proacti\w*|force de proposition)\b",
        "autonomie et initiative",
    ),
    "apprentissage": (
        r"\b(veille|curiosite|curieux|apprendre|montee en competences?)\b",
        "veille et apprentissage",
    ),
    "priorites": (
        r"\b(priorit\w*|multi projets?|plusieurs projets|polyvalen\w*)\b",
        "priorités multiples",
    ),
    "reussite": (
        r"\b(clients?|utilisateurs?|resultats?|objectifs?)\b",
        "résultats et clients",
    ),
}


def suggest_star_questions(pOfferText, pAnswers):
    """Retourne les questions comportementales que le texte de l'offre rend probables.

    Chacune indique le thème repéré et si sa réponse STAR est déjà préparée.
    """

    vText = normalize(pOfferText)

    rSuggestions = [
        {
            "question": BEHAVIORAL_QUESTIONS[vKey],
            "reason": vReason,
            "prepared": vKey in pAnswers,
        }
        for vKey, (vPattern, vReason) in OFFER_SIGNALS.items()
        if re.search(vPattern, vText)
    ]

    return rSuggestions
