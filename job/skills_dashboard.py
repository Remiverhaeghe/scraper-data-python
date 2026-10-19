"""Tableau de bord des compétences : demande des offres et préparation en révision

Croise les compétences citées par les offres en base avec le profil et les
scores de révision, pour voir où porter l'effort avant les entretiens.
"""

from job.enrichment import SKILLS
from job.profile import load_profile
from job.quiz import build_quiz_overview
from job.quiz_domains import DOMAIN_ICONS, classify_theme
from job.quiz_generation import load_catalog
from storage.job_offers import get_skill_lists

# Nombre de compétences affichées, les plus demandées d'abord
MAX_SKILLS = 20

# Seuils de maîtrise d'une compétence, d'après le score de ses thèmes
MASTERED_SCORE = 80
STARTED_SCORE = 40

# État d'une compétence : libellé, icône et tonalité de couleur
SKILL_STATUSES = {
    "missing": ("Aucune question", "circle-alert", "danger"),
    "todo": ("À réviser", "history", "warning"),
    "progress": ("En cours", "graduation-cap", "primary"),
    "done": ("Maîtrisé", "circle-check", "success"),
}


def get_known_skills(pQuiz):
    """Retourne les compétences reconnues, nom en minuscules vers nom affiché."""

    rSkills = {vSkill.lower(): vSkill for vSkill in SKILLS}

    for vTheme in pQuiz.values():
        for vSkill in vTheme["skills"]:
            if vSkill.strip():
                rSkills.setdefault(vSkill.strip().lower(), vSkill.strip())

    return rSkills


def count_skill_demand(pSkillLists, pKnownSkills):
    """Compte les offres qui citent chaque compétence reconnue, sans doublon de casse.

    Les étiquettes des sources qui ne sont pas des compétences (« ai »,
    « fintech ») sont ignorées.
    """

    rCounts = {}

    for vList in pSkillLists:
        for vSkill in {pKnownSkills.get(vItem.strip().lower()) for vItem in vList}:
            if vSkill:
                rCounts[vSkill] = rCounts.get(vSkill, 0) + 1

    return rCounts


def get_skill_status(pThemes, pScore):
    """Retourne l'état d'une compétence selon ses thèmes de révision et leur score."""

    if not pThemes:
        rStatus = "missing"
    elif pScore >= MASTERED_SCORE:
        rStatus = "done"
    elif pScore >= STARTED_SCORE:
        rStatus = "progress"
    else:
        rStatus = "todo"

    return rStatus


def find_catalog_theme(pCatalog, pSkill):
    """Retourne le thème du catalogue qui couvre une compétence, ou None."""

    rTheme = next(
        (
            vTheme
            for vTheme in pCatalog
            if pSkill.lower() in {vItem.lower() for vItem in vTheme["skills"]}
        ),
        None,
    )

    return rTheme


def get_skill_icon(pSkill, pThemes, pCatalogTheme):
    """Retourne l'icône d'une compétence : celle de son sous-domaine de révision.

    Le thème de révision décide d'abord, puis le thème du catalogue, puis le
    classement par mots-clés.
    """

    if pThemes:
        vDomain, vSubdomain = pThemes[0]["domain"], pThemes[0]["subdomain"]
    elif pCatalogTheme:
        vDomain, vSubdomain = pCatalogTheme["domain"], pCatalogTheme["subdomain"]
    else:
        vDomain, vSubdomain = classify_theme(pSkill, [pSkill])

    rIcon = DOMAIN_ICONS.get(vSubdomain) or DOMAIN_ICONS.get(vDomain) or "tag"

    return rIcon


def build_skill_rows(pCounts, pOfferCount, pThemes, pProfileSkills, pCatalog=()):
    """Retourne une ligne par compétence demandée, la plus demandée d'abord.

    Le thème du catalogue sert à préparer la demande de questions à ChatGPT.
    """

    vProfile = {vSkill.strip().lower() for vSkill in pProfileSkills}
    rRows = []

    for vSkill, vCount in sorted(
        pCounts.items(), key=lambda pItem: (-pItem[1], pItem[0].lower())
    )[:MAX_SKILLS]:
        vThemes = [
            vTheme
            for vTheme in pThemes
            if vSkill.lower() in {vItem.lower() for vItem in vTheme["skills"]}
        ]
        vTotal = sum(vTheme["total"] for vTheme in vThemes)
        vCatalogTheme = find_catalog_theme(pCatalog, vSkill)
        vScore = (
            round(100 * sum(vTheme["correct"] for vTheme in vThemes) / vTotal)
            if vTotal
            else 0
        )

        rRows.append(
            {
                "skill": vSkill,
                "offers": vCount,
                "share": round(100 * vCount / pOfferCount) if pOfferCount else 0,
                "in_profile": vSkill.lower() in vProfile,
                "themes": [(vTheme["key"], vTheme["label"]) for vTheme in vThemes],
                "questions": vTotal,
                "score": vScore,
                "status": get_skill_status(vThemes, vScore),
                "catalog_label": (vCatalogTheme or {}).get("label", vSkill),
                "icon": get_skill_icon(vSkill, vThemes, vCatalogTheme),
            }
        )

    return rRows


def summarize_skills(pRows):
    """Retourne les chiffres clés : couverture, préparation pondérée, priorité."""

    vDemand = sum(vRow["offers"] for vRow in pRows)
    vCovered = [vRow for vRow in pRows if vRow["themes"]]

    # La compétence la plus demandée parmi celles qui ne sont pas maîtrisées
    vPriority = next((vRow for vRow in pRows if vRow["status"] != "done"), None)

    rSummary = {
        "skills": len(pRows),
        "covered": len(vCovered),
        "in_profile": sum(1 for vRow in pRows if vRow["in_profile"]),
        # Préparation pondérée par la demande : une compétence très demandée
        # compte davantage qu'une compétence rare.
        "readiness": (
            round(sum(vRow["offers"] * vRow["score"] for vRow in pRows) / vDemand)
            if vDemand
            else 0
        ),
        "priority": vPriority["skill"] if vPriority else None,
    }

    return rSummary


def build_skills_dashboard(pDatabaseFile, pQuiz):
    """Retourne les compétences les plus demandées croisées avec la préparation."""

    vSkillLists = get_skill_lists(pDatabaseFile)
    vRows = build_skill_rows(
        count_skill_demand(vSkillLists, get_known_skills(pQuiz)),
        len(vSkillLists),
        [
            {**vTheme, "skills": pQuiz[vTheme["key"]]["skills"]}
            for vTheme in build_quiz_overview(pDatabaseFile, pQuiz)
        ],
        load_profile(pDatabaseFile).get("skills") or [],
        load_catalog(),
    )

    rDashboard = {
        "offer_count": len(vSkillLists),
        "rows": vRows,
        "summary": summarize_skills(vRows),
    }

    return rDashboard
