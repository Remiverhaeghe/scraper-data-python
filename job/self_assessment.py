"""Grille d'auto-évaluation des compétences : niveau de 0 à 10 par compétence

Une compétence notée KNOWN_LEVEL ou plus compte dans la correspondance avec les
offres ; notée de 1 à WEAK_LEVEL, elle désigne les thèmes de révision à renforcer.
"""

from job.fingerprint import normalize
from job.profile import load_profile, save_profile
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_LEVEL = 10
KNOWN_LEVEL = 5
WEAK_LEVEL = 4

# Grille de départ d'un poste de développeur, complétée par les compétences du profil
GRID_SKILLS = (
    "Java",
    "Jakarta EE (JEE)",
    "JavaServer Faces",
    "JavaScript",
    "HTML5",
    "CSS",
    "Android",
    "PHP",
    "MySQL",
    "SQL Server",
    "Tomcat",
    "Apache HTTP Server",
    "Nginx",
    "Linux",
    "Windows",
    "Virtualisation",
)


def build_grid(pProfile):
    """Retourne les lignes de la grille : (compétence, niveau), sans doublon."""

    vLevels = pProfile.get("skill_levels") or {}
    vSkills = list(GRID_SKILLS)
    vSeen = {normalize(vSkill) for vSkill in vSkills}

    for vSkill in [*pProfile.get("skills", []), *vLevels]:
        if normalize(vSkill) not in vSeen:
            vSkills.append(vSkill)
            vSeen.add(normalize(vSkill))

    rGrid = [(vSkill, int(vLevels.get(vSkill, 0))) for vSkill in vSkills]

    return rGrid


def save_skill_levels(pDatabaseFile, pLevels):
    """Enregistre les niveaux saisis ; un niveau à 0 est retiré. Retourne la grille.

    Lève ValueError pour un niveau hors de 0 à MAX_LEVEL.
    """

    vLevels = {}

    for vSkill, vLevel in pLevels.items():
        if not 0 <= vLevel <= MAX_LEVEL:
            raise ValueError(f"Niveau de 0 à {MAX_LEVEL} attendu pour {vSkill}.")

        if vLevel and vSkill.strip():
            vLevels[vSkill.strip()] = vLevel

    vProfile = {**load_profile(pDatabaseFile), "skill_levels": vLevels}
    save_profile(pDatabaseFile, vProfile)

    logger.info("Auto-évaluation enregistrée : %s compétence(s) notée(s)", len(vLevels))

    rGrid = build_grid(vProfile)

    return rGrid


def get_assessed_skills(pProfile):
    """Retourne les compétences notées KNOWN_LEVEL ou plus."""

    rSkills = [
        vSkill
        for vSkill, vLevel in (pProfile.get("skill_levels") or {}).items()
        if vLevel >= KNOWN_LEVEL
    ]

    return rSkills


def find_weak_themes(pProfile, pQuiz):
    """Retourne les thèmes de révision liés à une compétence notée de 1 à WEAK_LEVEL.

    Chaque thème porte la compétence faible qui l'a désigné et son niveau, le
    plus faible en tête.
    """

    vWeak = {
        normalize(vSkill): (vSkill, vLevel)
        for vSkill, vLevel in (pProfile.get("skill_levels") or {}).items()
        if 0 < vLevel <= WEAK_LEVEL
    }
    rThemes = []

    for vKey, vTheme in pQuiz.items():
        vMatch = next(
            (
                vWeak[vName]
                for vName in map(normalize, [vTheme["label"], *vTheme["skills"]])
                if vName in vWeak
            ),
            None,
        )

        if vMatch and vTheme["questions"]:
            rThemes.append(
                {
                    "key": vKey,
                    "label": vTheme["label"],
                    "skill": vMatch[0],
                    "level": vMatch[1],
                }
            )

    rThemes.sort(key=lambda pTheme: (pTheme["level"], pTheme["label"]))

    return rThemes
