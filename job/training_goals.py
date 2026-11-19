"""Formations et certifications visées, rattachées aux compétences des offres

Un objectif est une certification du catalogue (job/certifications.py) ou une
formation libre (cours en ligne, titre professionnel…). Il porte les compétences
qu'il apporte : on voit combien d'offres en base les demandent, et quelles
compétences très demandées n'ont encore aucun objectif.
"""

import uuid
from datetime import date

from job.certifications import (
    CERTIFICATIONS,
    get_offer_certifications,
    load_owned,
    save_owned,
)
from job.preparation import get_offer_skills
from job.skills_dashboard import count_skill_demand
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

GOALS_KEY = "training_goals"

# État d'un objectif : libellé et tonalité du badge
STATUSES = {
    "planned": ("Visée", "muted"),
    "in_progress": ("En cours", "warning"),
    "done": ("Obtenue", "success"),
    "dropped": ("Abandonnée", "muted"),
}

# Objectifs encore à atteindre : seuls ceux-là peuvent être en retard.
OPEN_STATUSES = ("planned", "in_progress")

MAX_GOALS = 50
MAX_TEXT_LENGTH = 300
MAX_SKILLS = 10

# Compétences très demandées sans objectif, proposées sous la liste
MAX_UNCOVERED = 5


def load_goals(pDatabaseFile):
    """Retourne les objectifs enregistrés, dans l'ordre de saisie."""

    vGoals = load_json_setting(pDatabaseFile, GOALS_KEY, [], list)

    rGoals = [
        vGoal
        for vGoal in vGoals
        if isinstance(vGoal, dict) and vGoal.get("id") and vGoal.get("title")
    ]

    return rGoals


def parse_skills(pText, pKnownSkills):
    """Retourne les compétences saisies, séparées par des virgules, sans doublon.

    Une compétence reconnue prend l'écriture du catalogue (« python » devient
    « Python ») pour être comptée dans les offres.
    """

    rSkills = []

    for vItem in str(pText or "").split(","):
        vSkill = vItem.strip()[:MAX_TEXT_LENGTH]
        vSkill = pKnownSkills.get(vSkill.lower(), vSkill)

        if vSkill and vSkill.lower() not in {vKnown.lower() for vKnown in rSkills}:
            rSkills.append(vSkill)

    rSkills = rSkills[:MAX_SKILLS]

    return rSkills


def clean_goal(pForm, pKnownSkills):
    """Retourne l'objectif saisi, nettoyé ; lève ValueError s'il est invalide."""

    vCertification = str(pForm.get("certification") or "").strip()
    vTitle = str(pForm.get("title") or "").strip()[:MAX_TEXT_LENGTH]
    vStatus = str(pForm.get("status") or "planned")
    vTarget = str(pForm.get("target") or "").strip()
    vLink = str(pForm.get("link") or "").strip()[:MAX_TEXT_LENGTH]

    if vCertification and vCertification not in CERTIFICATIONS:
        raise ValueError("Certification inconnue.")

    if vCertification and not vTitle:
        vTitle = CERTIFICATIONS[vCertification]["label"]

    if not vTitle:
        raise ValueError("Indiquez la formation ou la certification visée.")

    if vStatus not in STATUSES:
        raise ValueError("État inconnu.")

    if vTarget:
        try:
            date.fromisoformat(vTarget)

        except ValueError as vException:
            raise ValueError("Date visée invalide.") from vException

    # Le lien est ouvert d'un clic : seule une adresse web est acceptée.
    if vLink and not vLink.startswith(("https://", "http://")):
        raise ValueError("Le lien doit commencer par https://.")

    rGoal = {
        "certification": vCertification,
        "title": vTitle,
        "organism": str(pForm.get("organism") or "").strip()[:MAX_TEXT_LENGTH],
        "status": vStatus,
        "target": vTarget,
        "link": vLink,
        "skills": parse_skills(pForm.get("skills"), pKnownSkills),
    }

    return rGoal


def save_goal(pDatabaseFile, pForm, pKnownSkills, pToday):
    """Ajoute ou met à jour un objectif ; retourne son identifiant.

    Une certification du catalogue passée à « Obtenue » est aussi notée comme
    obtenue dans la page Certifications, à la date du jour, si elle ne l'était pas.
    """

    vGoal = clean_goal(pForm, pKnownSkills)
    vGoals = load_goals(pDatabaseFile)
    vId = str(pForm.get("id") or "")
    vExisting = next((vItem for vItem in vGoals if vItem["id"] == vId), None)

    if vExisting:
        vExisting.update(vGoal)
        rId = vId
    else:
        if len(vGoals) >= MAX_GOALS:
            raise ValueError(f"{MAX_GOALS} objectifs au plus.")

        rId = uuid.uuid4().hex[:12]
        vGoals.append({"id": rId, **vGoal})

    save_json_setting(pDatabaseFile, GOALS_KEY, vGoals)

    if vGoal["status"] == "done" and vGoal["certification"]:
        if vGoal["certification"] not in load_owned(pDatabaseFile):
            save_owned(pDatabaseFile, vGoal["certification"], pToday)

    logger.info("Objectif de formation enregistré : %s", vGoal["title"])

    return rId


def delete_goal(pDatabaseFile, pId):
    """Retire un objectif ; retourne False s'il n'existait pas."""

    vGoals = load_goals(pDatabaseFile)
    vKept = [vGoal for vGoal in vGoals if vGoal["id"] != pId]

    save_json_setting(pDatabaseFile, GOALS_KEY, vKept)

    rDeleted = len(vKept) < len(vGoals)

    return rDeleted


def build_goals_overview(pGoals, pOffers, pKnownSkills, pToday):
    """Retourne les objectifs avec les offres qu'ils servent, et les compétences
    très demandées qui n'ont encore aucun objectif.

    pOffers sont les offres récentes : leurs compétences et les certifications
    citées dans leur texte sont comptées.
    """

    vSkillLists = [get_offer_skills(vOffer) for vOffer in pOffers]
    vDemand = count_skill_demand(vSkillLists, pKnownSkills)
    vCertificationSets = [get_offer_certifications(vOffer) for vOffer in pOffers]
    vWantedSkills = [{vSkill.lower() for vSkill in vList} for vList in vSkillLists]
    vRows = []

    for vGoal in pGoals:
        vSkills = {vSkill.lower() for vSkill in vGoal.get("skills") or []}
        vTarget = vGoal.get("target") or ""
        vRows.append(
            {
                **vGoal,
                "status_label": STATUSES.get(vGoal.get("status"), STATUSES["planned"]),
                # Une offre compte une fois, même si elle cite plusieurs compétences.
                "skill_offers": sum(1 for vSet in vWantedSkills if vSet & vSkills),
                "skill_counts": [
                    (vSkill, vDemand.get(pKnownSkills.get(vSkill.lower(), vSkill), 0))
                    for vSkill in vGoal.get("skills") or []
                ],
                "certification_offers": (
                    sum(vGoal["certification"] in vSet for vSet in vCertificationSets)
                    if vGoal.get("certification")
                    else None
                ),
                "late": bool(
                    vTarget
                    and vGoal.get("status") in OPEN_STATUSES
                    and date.fromisoformat(vTarget) < pToday
                ),
            }
        )

    vCovered = {
        vSkill.lower()
        for vGoal in pGoals
        if vGoal.get("status") != "dropped"
        for vSkill in vGoal.get("skills") or []
    }

    rOverview = {
        "rows": vRows,
        "counts": {
            vStatus: sum(1 for vGoal in pGoals if vGoal.get("status") == vStatus)
            for vStatus in STATUSES
        },
        "uncovered": [
            (vSkill, vCount)
            for vSkill, vCount in sorted(
                vDemand.items(), key=lambda pItem: (-pItem[1], pItem[0])
            )
            if vSkill.lower() not in vCovered
        ][:MAX_UNCOVERED],
        "offers": len(vSkillLists),
    }

    return rOverview
