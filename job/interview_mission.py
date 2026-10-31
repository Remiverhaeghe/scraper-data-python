"""Préparation d'un entretien en mission : étapes à cocher, avancement et boss

La mission d'une offre reprend la préparation existante : fiche entreprise,
pitch, questions pièges, manques, simulation. Les étapes qui se vérifient seules
le font d'après les examens blancs enregistrés : les manques avec l'examen des
compétences manquantes, le boss avec l'examen blanc de l'offre. La première
mission terminée d'une offre rapporte des points, une seule fois.
"""

from datetime import datetime

from job.interview_revision import describe_offer_exam
from job.quiz_exam import load_exam_results
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Étapes cochées et date de réussite, par offre ; lues aussi par job/progress.py
MISSIONS_KEY = "interview_missions"
# Étape : (identifiant, titre, ce qu'il faut faire, vérifiée seule)
MISSION_STEPS = (
    (
        "company",
        "Fiche entreprise",
        "Lire l'activité, la taille et les sites de l'entreprise",
        False,
    ),
    (
        "pitch",
        "Pitch",
        "Dire son pitch de 30 secondes et de 2 minutes à voix haute",
        False,
    ),
    (
        "tricky",
        "Questions pièges",
        "Préparer une réponse à chaque question piège",
        False,
    ),
    (
        "gaps",
        "Manques à combler",
        "Passer l'examen blanc des compétences manquantes",
        True,
    ),
    (
        "simulation",
        "Simulation d'entretien",
        "Répondre à une simulation d'entretien technique, à voix haute",
        False,
    ),
    (
        "boss",
        "Boss : examen blanc de l'offre",
        "Obtenir 70 % ou plus à l'examen blanc de l'offre",
        True,
    ),
)
MANUAL_STEPS = tuple(vId for vId, _, _, vAuto in MISSION_STEPS if not vAuto)
BOSS_SCORE = 70


def get_mission_key(pOffer):
    """Retourne la clé d'une offre, celle des fiches de préparation du téléphone."""

    rKey = f"{pOffer.get('source')}/{pOffer.get('source_id')}"

    return rKey


def load_missions(pDatabaseFile):
    """Retourne les missions enregistrées, par offre."""

    rMissions = load_json_setting(pDatabaseFile, MISSIONS_KEY, {}, dict)

    return rMissions


def describe_gaps(pDatabaseFile, pOffer, pMissing):
    """Retourne (faite, détail) de l'étape des manques."""

    if not pMissing:
        return (True, "Aucune compétence de l'offre ne manque au profil.")

    vTitle = f"Compétences manquantes · {describe_offer_exam(pOffer)}"
    vScores = [
        vResult.get("score", 0)
        for vResult in load_exam_results(pDatabaseFile)
        if vResult.get("title") == vTitle
    ]

    rGaps = (
        bool(vScores),
        (
            f"Examen des manques passé : {max(vScores)} %."
            if vScores
            else f"À revoir : {', '.join(pMissing)}."
        ),
    )

    return rGaps


def describe_boss(pDatabaseFile, pOffer):
    """Retourne (vaincu, meilleure note, détail) du boss : l'examen blanc de l'offre."""

    vScores = [
        vResult.get("score", 0)
        for vResult in load_exam_results(
            pDatabaseFile, (pOffer.get("source"), str(pOffer.get("source_id")))
        )
    ]
    vBest = max(vScores, default=None)

    rBoss = (
        vBest is not None and vBest >= BOSS_SCORE,
        vBest,
        (
            f"Meilleure note : {vBest} % pour {BOSS_SCORE} % demandés."
            if vBest is not None
            else f"Pas encore affronté : {BOSS_SCORE} % demandés."
        ),
    )

    return rBoss


def build_mission(pDatabaseFile, pOffer, pMissing, pNow=None):
    """Retourne la mission d'une offre : étapes, avancement, et récompense.

    pMissing liste les compétences de l'offre absentes du profil. La première
    fois que toutes les étapes sont faites, la mission est datée : c'est ce qui
    rapporte les points.
    """

    vMissions = load_missions(pDatabaseFile)
    vKey = get_mission_key(pOffer)
    vEntry = vMissions.get(vKey) if isinstance(vMissions.get(vKey), dict) else {}
    vChecked = vEntry.get("steps") if isinstance(vEntry.get("steps"), dict) else {}
    vGapsDone, vGapsDetail = describe_gaps(pDatabaseFile, pOffer, pMissing)
    vBossDone, vBest, vBossDetail = describe_boss(pDatabaseFile, pOffer)
    vAutomatic = {"gaps": (vGapsDone, vGapsDetail), "boss": (vBossDone, vBossDetail)}
    vSteps = []

    for vId, vLabel, vTask, vAuto in MISSION_STEPS:
        vDone, vDetail = vAutomatic[vId] if vAuto else (vId in vChecked, "")
        vSteps.append(
            {
                "id": vId,
                "label": vLabel,
                "task": vTask,
                "automatic": vAuto,
                "done": vDone,
                "detail": vDetail,
            }
        )

    vDoneCount = sum(vStep["done"] for vStep in vSteps)
    vJustCompleted = vDoneCount == len(vSteps) and not vEntry.get("completed_at")

    if vJustCompleted:
        vEntry = {
            **vEntry,
            "completed_at": (pNow or datetime.now()).isoformat(timespec="seconds"),
        }
        vMissions[vKey] = vEntry
        save_json_setting(pDatabaseFile, MISSIONS_KEY, vMissions)
        logger.info("Mission d'entretien terminée : %s", vKey)

    rMission = {
        "key": vKey,
        "steps": vSteps,
        "done": vDoneCount,
        "total": len(vSteps),
        "percent": round(100 * vDoneCount / len(vSteps)),
        "boss_best": vBest,
        "completed_at": vEntry.get("completed_at"),
        "just_completed": vJustCompleted,
    }

    return rMission


def set_step(pDatabaseFile, pOffer, pStep, pDone, pNow=None):
    """Coche ou décoche une étape à faire soi-même ; lève ValueError sinon."""

    if pStep not in MANUAL_STEPS:
        raise ValueError("Cette étape se vérifie toute seule.")

    vMissions = load_missions(pDatabaseFile)
    vKey = get_mission_key(pOffer)
    vEntry = vMissions.get(vKey) if isinstance(vMissions.get(vKey), dict) else {}
    vSteps = vEntry.get("steps") if isinstance(vEntry.get("steps"), dict) else {}

    if pDone:
        vSteps[pStep] = (pNow or datetime.now()).isoformat(timespec="seconds")
    else:
        vSteps.pop(pStep, None)

    vMissions[vKey] = {**vEntry, "steps": vSteps}
    save_json_setting(pDatabaseFile, MISSIONS_KEY, vMissions)
