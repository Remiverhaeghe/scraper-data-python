"""Progression du candidat : points d'expérience, niveaux, série et quêtes

Les points (XP) se calculent à partir de ce que la base garde déjà : réponses de
révision, défis, niveaux Git, examens blancs, statuts des candidatures, relances
et comptes rendus d'entretien. Aucune page n'a donc à déclarer ses actions, et
l'historique compte dès la première ouverture.

Les actions utiles à la recherche d'emploi rapportent le plus : une candidature
vaut six réponses justes, un entretien obtenu vingt. Une série perdue ne fait
jamais perdre de points.
"""

import random
from datetime import date, datetime, timedelta

from job.achievements import build_player_card, evaluate_achievements
from job.code_puzzles import PUZZLE_PROGRESS_KEY
from job.interview_mission import MISSIONS_KEY
from job.oral_interview import ORAL_KEY
from job.quiz_exam import load_exam_results
from storage.aptitude_sessions import get_aptitude_sessions
from storage.database import connect_database
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Points par action : (libellé affiché, XP)
XP_RULES = {
    "answer_right": ("Réponse juste en révision", 5),
    "answer_wrong": ("Réponse fausse : l'effort compte", 2),
    "challenge_right": ("Défi réussi", 20),
    "challenge_tried": ("Défi tenté", 3),
    "git_level": ("Niveau Git terminé", 25),
    "exam": ("Examen blanc terminé, plus 1 par tranche de 10 % de note", 30),
    "aptitude": ("Test de recrutement terminé, plus 2 par bonne réponse", 10),
    "troubleshooting": ("Panne résolue, plus 2 par tranche de 10 points", 20),
    "ladder_level": ("Niveau d'automate réussi", 25),
    "sql_level": ("Niveau SQL réussi", 15),
    "circuit_level": ("Montage électrique réussi", 20),
    "devops_level": ("Niveau Maven ou Docker réussi", 20),
    "oral_interview": ("Entretien oral simulé terminé", 25),
    "interview_mission": ("Mission d'entretien terminée", 60),
    "puzzle_series": (
        "Série de puzzles de code terminée, plus 2 par bonne réponse",
        10,
    ),
    "interested": ("Offre marquée « Intéressé »", 5),
    "applied": ("Candidature envoyée", 30),
    "follow_up": ("Relance faite", 15),
    "interview": ("Entretien obtenu", 100),
    "interview_note": ("Compte rendu d'entretien", 20),
    "accepted": ("Poste accepté", 300),
    "daily_quest": ("Quête du jour réussie", 20),
    "weekly_quest": ("Quête de la semaine réussie", 60),
}

# Points de chaque bonne réponse d'un test de recrutement, en plus du forfait
APTITUDE_XP_PER_RIGHT = 2

# Points de chaque tranche de 10 points du score d'une panne résolue
TROUBLESHOOTING_XP_PER_TEN = 2

# Points de chaque bonne réponse d'une série de puzzles de code, en plus du forfait
PUZZLE_XP_PER_RIGHT = 2

# Résultats des pannes résolues, enregistrés par job/troubleshooting.py
TROUBLESHOOTING_RESULTS_KEY = "troubleshooting_results"

# Programmes et réussites du simulateur d'automate (job/ladder_game.py)
LADDER_PROGRESS_KEY = "ladder_progress"

# Dialecte choisi, requêtes et réussites du bac à sable SQL (job/sql_levels.py)
SQL_PROGRESS_KEY = "sql_progress"

# Montages réussis et schémas libres de l'éditeur de circuits (job/circuit_levels.py)
CIRCUIT_PROGRESS_KEY = "circuit_progress"

# Fichiers, hôte Docker et réussites des niveaux Maven et Docker (job/devops_levels.py)
DEVOPS_PROGRESS_KEY = "devops_progress"

# Statut de candidature vers son action
STATUS_ACTIONS = {
    "INTERESTED": "interested",
    "APPLIED": "applied",
    "INTERVIEW": "interview",
    "ACCEPTED": "accepted",
}

# Titres des niveaux, au vocabulaire de la maintenance ; au-delà, Légende
LEVEL_TITLES = (
    "Apprenti",
    "Apprenti confirmé",
    "Technicien",
    "Technicien confirmé",
    "Technicien expert",
    "Chef d'équipe",
    "Responsable",
    "Expert",
    "Maître",
    "Légende",
)

# Le niveau n commence à 50 × n × (n - 1) XP : 100 pour le 2, 300 pour le 3…
LEVEL_STEP = 50

# Quêtes du jour : (libellé, objectif) ; leur choix dépend de la situation
DAILY_QUESTS = {
    "revise": ("Réviser 10 questions", 10),
    "apply": ("Envoyer une candidature", 1),
    "follow_up": ("Faire une relance prévue", 1),
    "challenge": ("Réussir un défi", 1),
    "interested": ("Repérer 3 offres intéressantes", 3),
    "exam": ("Terminer un examen blanc", 1),
    "git": ("Terminer un niveau Git", 1),
}
DAILY_QUEST_COUNT = 3

# Une quête de la semaine, choisie selon le numéro de la semaine
WEEKLY_QUESTS = {
    "week_apply": ("Envoyer 3 candidatures", 3),
    "week_active": ("Être actif 5 jours", 5),
    "week_revise": ("Réviser 60 questions", 60),
}

# Quêtes tirées pour chaque jour et chaque semaine, gardées pour ne pas changer en
# cours de journée quand la situation évolue (une relance faite, par exemple)
QUESTS_KEY = "progress_quests"

# Jours gardés dans l'historique des quêtes
QUEST_HISTORY_DAYS = 60

HISTORY_DAYS = 14


def read_day(pValue):
    """Retourne le jour d'une date enregistrée en texte ISO, ou None."""

    try:
        rDay = date.fromisoformat(str(pValue)[:10])

    except ValueError:
        rDay = None

    return rDay


def add_action(pActivity, pDay, pAction, pCount=1, pXp=None):
    """Ajoute des actions d'un jour à l'activité, avec leurs points."""

    if pDay is None or not pCount:
        return

    vDay = pActivity.setdefault(pDay, {"xp": 0, "actions": {}})
    vDay["actions"][pAction] = vDay["actions"].get(pAction, 0) + pCount
    vDay["xp"] += XP_RULES[pAction][1] * pCount if pXp is None else pXp


def load_activity(pDatabaseFile):
    """Retourne, par jour, les actions faites et les points gagnés."""

    rActivity = {}
    vConnection = connect_database(pDatabaseFile)

    try:
        for vDay, vRight, vWrong in vConnection.execute("""
            SELECT substr(answered_at, 1, 10), SUM(correct = 1), SUM(correct = 0)
            FROM quiz_answer GROUP BY 1
            """):
            add_action(rActivity, read_day(vDay), "answer_right", vRight)
            add_action(rActivity, read_day(vDay), "answer_wrong", vWrong)

        for vDay, vRight, vTried in vConnection.execute("""
            SELECT substr(answered_at, 1, 10), SUM(correct = 1), SUM(correct = 0)
            FROM challenge_attempt GROUP BY 1
            """):
            add_action(rActivity, read_day(vDay), "challenge_right", vRight)
            add_action(rActivity, read_day(vDay), "challenge_tried", vTried)

        for vDay, vCount in vConnection.execute("""
            SELECT substr(completed_at, 1, 10), COUNT(*)
            FROM git_level_result WHERE completed_at IS NOT NULL GROUP BY 1
            """):
            add_action(rActivity, read_day(vDay), "git_level", vCount)

        for vDay, vStatus, vCount in vConnection.execute("""
            SELECT substr(changed_at, 1, 10), status, COUNT(*)
            FROM application_history GROUP BY 1, 2
            """):
            if vStatus in STATUS_ACTIONS:
                add_action(rActivity, read_day(vDay), STATUS_ACTIONS[vStatus], vCount)

        for vTable, vColumn, vAction in (
            ("job_follow_up", "followed_up_at", "follow_up"),
            ("interview_note", "interviewed_at", "interview_note"),
        ):
            for vDay, vCount in vConnection.execute(
                f"SELECT substr({vColumn}, 1, 10), COUNT(*) "  # nosec B608
                f"FROM {vTable} GROUP BY 1"
            ):
                add_action(rActivity, read_day(vDay), vAction, vCount)

    finally:
        vConnection.close()

    for vResult in load_exam_results(pDatabaseFile):
        add_action(
            rActivity,
            read_day(vResult.get("finished_at")),
            "exam",
            pXp=XP_RULES["exam"][1] + int(vResult.get("score") or 0) // 10,
        )

    for vSession in get_aptitude_sessions(pDatabaseFile):
        add_action(
            rActivity,
            read_day(vSession["played_at"]),
            "aptitude",
            pXp=XP_RULES["aptitude"][1] + APTITUDE_XP_PER_RIGHT * vSession["correct"],
        )

    for vResult in load_json_setting(
        pDatabaseFile, TROUBLESHOOTING_RESULTS_KEY, [], list
    ):
        add_action(
            rActivity,
            read_day(vResult.get("finished_at")),
            "troubleshooting",
            pXp=XP_RULES["troubleshooting"][1]
            + TROUBLESHOOTING_XP_PER_TEN * (int(vResult.get("score") or 0) // 10),
        )

    for vEntry in load_json_setting(
        pDatabaseFile, LADDER_PROGRESS_KEY, {}, dict
    ).values():
        if isinstance(vEntry, dict) and vEntry.get("passed_at"):
            add_action(rActivity, read_day(vEntry["passed_at"]), "ladder_level")

    for vKey, vAction in (
        (SQL_PROGRESS_KEY, "sql_level"),
        (CIRCUIT_PROGRESS_KEY, "circuit_level"),
        (DEVOPS_PROGRESS_KEY, "devops_level"),
    ):
        vLevels = load_json_setting(pDatabaseFile, vKey, {}, dict).get("levels")

        for vEntry in (vLevels if isinstance(vLevels, dict) else {}).values():
            if isinstance(vEntry, dict) and vEntry.get("passed_at"):
                add_action(rActivity, read_day(vEntry["passed_at"]), vAction)

    vOral = load_json_setting(pDatabaseFile, ORAL_KEY, {}, dict)

    for vSession in vOral.get("history") or []:
        if isinstance(vSession, dict):
            add_action(
                rActivity, read_day(vSession.get("finished_at")), "oral_interview"
            )

    for vMission in load_json_setting(pDatabaseFile, MISSIONS_KEY, {}, dict).values():
        if isinstance(vMission, dict) and vMission.get("completed_at"):
            add_action(
                rActivity, read_day(vMission["completed_at"]), "interview_mission"
            )

    vPuzzles = load_json_setting(pDatabaseFile, PUZZLE_PROGRESS_KEY, {}, dict)

    for vSeries in vPuzzles.get("history") or []:
        if isinstance(vSeries, dict):
            add_action(
                rActivity,
                read_day(vSeries.get("finished_at")),
                "puzzle_series",
                pXp=XP_RULES["puzzle_series"][1]
                + PUZZLE_XP_PER_RIGHT * int(vSeries.get("score") or 0),
            )

    for vDay, vQuests in load_quest_log(pDatabaseFile).get("done", {}).items():
        for vQuest in vQuests:
            add_action(
                rActivity,
                read_day(vDay),
                "weekly_quest" if vQuest in WEEKLY_QUESTS else "daily_quest",
            )

    return rActivity


def get_level_start(pLevel):
    """Retourne les points à partir desquels un niveau est atteint."""

    rStart = LEVEL_STEP * pLevel * (pLevel - 1)

    return rStart


def get_level_title(pLevel):
    """Retourne le titre d'un niveau ; au-delà de la liste, Légende numérotée."""

    rTitle = (
        LEVEL_TITLES[pLevel - 1]
        if pLevel <= len(LEVEL_TITLES)
        else f"{LEVEL_TITLES[-1]} {pLevel - len(LEVEL_TITLES) + 1}"
    )

    return rTitle


def describe_level(pXp):
    """Retourne le niveau atteint, son titre et l'avancée vers le suivant."""

    vLevel = 1

    while pXp >= get_level_start(vLevel + 1):
        vLevel += 1

    vStart = get_level_start(vLevel)
    vNext = get_level_start(vLevel + 1)

    rLevel = {
        "level": vLevel,
        "title": get_level_title(vLevel),
        "next_title": get_level_title(vLevel + 1),
        "xp_in_level": pXp - vStart,
        "xp_for_level": vNext - vStart,
        "percent": round(100 * (pXp - vStart) / (vNext - vStart)),
    }

    return rLevel


def compute_streak(pActiveDays, pToday):
    """Retourne la série en cours et la meilleure, en jours d'activité.

    Une série commencée hier reste en cours aujourd'hui. Un jour manqué par
    semaine est pardonné (joker), s'il est encadré de jours actifs.
    """

    vDays = set(pActiveDays)
    vStart = pToday if pToday in vDays else pToday - timedelta(days=1)
    rCurrent = count_streak(vDays, vStart)
    rBest = max([rCurrent, *(count_streak(vDays, vDay) for vDay in vDays)])

    return rCurrent, rBest


def count_streak(pDays, pStart):
    """Compte les jours actifs consécutifs jusqu'à pStart, un joker par semaine."""

    rCount = 0
    vJokers = set()
    vDay = pStart

    while True:
        if vDay in pDays:
            rCount += 1
        elif (
            rCount
            and vDay.isocalendar()[:2] not in vJokers
            and vDay - timedelta(days=1) in pDays
        ):
            vJokers.add(vDay.isocalendar()[:2])
        else:
            break

        vDay -= timedelta(days=1)

    return rCount


def load_quest_log(pDatabaseFile):
    """Retourne les quêtes tirées et réussies, par jour et par semaine."""

    rLog = load_json_setting(pDatabaseFile, QUESTS_KEY, {}, dict)

    return rLog


def read_situation(pDatabaseFile, pToday):
    """Retourne ce qui oriente les quêtes : relance due, entretien proche, offres."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vFollowUps, vInterviews = vConnection.execute(
            """
            SELECT
                SUM(status = 'APPLIED' AND follow_up_date <= ?),
                SUM(status = 'INTERVIEW' AND interview_at BETWEEN ? AND ?)
            FROM job_application
            """,
            (
                pToday.isoformat(),
                pToday.isoformat(),
                (pToday + timedelta(days=7)).isoformat() + "T23:59",
            ),
        ).fetchone()
        vNewOffers = vConnection.execute(
            "SELECT COUNT(*) FROM job_offer WHERE first_seen_at >= ?",
            ((pToday - timedelta(days=3)).isoformat(),),
        ).fetchone()[0]

    finally:
        vConnection.close()

    rSituation = {
        "follow_up_due": bool(vFollowUps),
        "interview_soon": bool(vInterviews),
        "new_offers": bool(vNewOffers),
    }

    return rSituation


def draw_daily_quests(pSituation, pToday):
    """Tire les quêtes du jour : les urgences d'abord, puis au hasard du jour."""

    vFirst = [
        vQuest
        for vQuest, vNeeded in (
            ("follow_up", pSituation["follow_up_due"]),
            ("exam", pSituation["interview_soon"]),
        )
        if vNeeded
    ]
    vOthers = [
        vQuest
        for vQuest in DAILY_QUESTS
        if vQuest not in vFirst
        and vQuest not in ("follow_up", "exam")
        and (pSituation["new_offers"] or vQuest not in ("apply", "interested"))
    ]
    # Quêtes du jour tirées pareil toute la journée, sans usage cryptographique.
    random.Random(pToday.toordinal()).shuffle(vOthers)  # nosec B311

    # La révision reste toujours proposée : c'est la quête faisable partout.
    vOthers.sort(key=lambda pQuest: pQuest != "revise")

    rQuests = (vFirst + vOthers)[:DAILY_QUEST_COUNT]

    return rQuests


def count_quest_progress(pQuest, pActivity, pToday):
    """Retourne l'avancée d'une quête d'après l'activité du jour ou de la semaine."""

    vWeek = [
        pToday - timedelta(days=vOffset) for vOffset in range(pToday.weekday() + 1)
    ]
    vToday = pActivity.get(pToday, {}).get("actions", {})

    def count_week(pActions):
        """Compte des actions sur la semaine en cours."""

        rCount = sum(
            pActivity.get(vDay, {}).get("actions", {}).get(vAction, 0)
            for vDay in vWeek
            for vAction in pActions
        )

        return rCount

    rProgress = {
        "revise": vToday.get("answer_right", 0) + vToday.get("answer_wrong", 0),
        "apply": vToday.get("applied", 0),
        "follow_up": vToday.get("follow_up", 0),
        "challenge": vToday.get("challenge_right", 0),
        "interested": vToday.get("interested", 0),
        "exam": vToday.get("exam", 0),
        "git": vToday.get("git_level", 0),
        "week_apply": count_week(("applied",)),
        "week_active": sum(
            1
            for vDay in vWeek
            if any(
                vAction not in ("daily_quest", "weekly_quest")
                for vAction in pActivity.get(vDay, {}).get("actions", {})
            )
        ),
        "week_revise": count_week(("answer_right", "answer_wrong")),
    }[pQuest]

    return rProgress


def build_quests(pDatabaseFile, pActivity, pToday):
    """Retourne les quêtes du jour et de la semaine avec leur avancée.

    Les quêtes tirées sont gardées pour la journée ou la semaine ; une quête
    réussie est notée une fois, ses points s'ajoutent au prochain calcul.
    """

    vLog = load_quest_log(pDatabaseFile)
    vDayKey = pToday.isoformat()
    vWeekKey = "{}-S{:02d}".format(*pToday.isocalendar()[:2])
    vDrawn = vLog.setdefault("drawn", {})
    vDone = vLog.setdefault("done", {})
    vChanged = False

    if vDayKey not in vDrawn:
        vDrawn[vDayKey] = draw_daily_quests(
            read_situation(pDatabaseFile, pToday), pToday
        )
        vChanged = True

    if vWeekKey not in vDrawn:
        vWeekQuests = list(WEEKLY_QUESTS)
        vDrawn[vWeekKey] = [vWeekQuests[pToday.isocalendar()[1] % len(vWeekQuests)]]
        vChanged = True

    rQuests = []

    for vQuest in vDrawn[vDayKey] + vDrawn[vWeekKey]:
        vLabel, vTarget = (DAILY_QUESTS | WEEKLY_QUESTS)[vQuest]
        vProgress = min(vTarget, count_quest_progress(vQuest, pActivity, pToday))
        vDoneDay = vWeekKey if vQuest in WEEKLY_QUESTS else vDayKey
        vAlreadyDone = vQuest in vDone.get(vDoneDay, [])

        if vProgress >= vTarget and not vAlreadyDone:
            vDone.setdefault(vDoneDay, []).append(vQuest)
            vChanged = True
            logger.info("Quête réussie : %s", vLabel)

        rQuests.append(
            {
                "id": vQuest,
                "label": vLabel,
                "weekly": vQuest in WEEKLY_QUESTS,
                "progress": vProgress,
                "target": vTarget,
                "done": vProgress >= vTarget,
                "xp": XP_RULES[
                    "weekly_quest" if vQuest in WEEKLY_QUESTS else "daily_quest"
                ][1],
            }
        )

    if vChanged:
        vOldest = (pToday - timedelta(days=QUEST_HISTORY_DAYS)).isoformat()
        vLog["drawn"] = {
            vKey: vValue for vKey, vValue in vDrawn.items() if vKey >= vOldest
        }
        save_json_setting(pDatabaseFile, QUESTS_KEY, vLog)

    return rQuests


def count_total_xp(pActivity):
    """Retourne le total des points gagnés."""

    rTotal = sum(vDay["xp"] for vDay in pActivity.values())

    return rTotal


def build_progress(pDatabaseFile, pNow=None):
    """Retourne la progression : niveau, points, série, quêtes et derniers jours."""

    vToday = (pNow or datetime.now()).date()
    vQuests = build_quests(pDatabaseFile, load_activity(pDatabaseFile), vToday)
    # Relue après les quêtes : une quête réussie à l'instant compte déjà.
    vActivity = load_activity(pDatabaseFile)
    vXp = count_total_xp(vActivity)
    vActiveDays = [
        vDay
        for vDay, vValues in vActivity.items()
        if any(
            vAction not in ("daily_quest", "weekly_quest")
            for vAction in vValues["actions"]
        )
    ]
    vStreak, vBestStreak = compute_streak(vActiveDays, vToday)

    rProgress = {
        "xp": vXp,
        **describe_level(vXp),
        "today_xp": vActivity.get(vToday, {}).get("xp", 0),
        "streak": vStreak,
        "best_streak": vBestStreak,
        "active_today": vToday in vActiveDays,
        "quests": vQuests,
        "history": [
            {
                "day": vDay.isoformat(),
                "xp": vActivity.get(vDay, {}).get("xp", 0),
            }
            for vDay in (
                vToday - timedelta(days=vOffset)
                for vOffset in range(HISTORY_DAYS - 1, -1, -1)
            )
        ],
        "rules": [{"label": vLabel, "xp": vXp} for vLabel, vXp in XP_RULES.values()],
    }
    vAchievements = evaluate_achievements(pDatabaseFile, vActivity, rProgress, vToday)
    rProgress["achievements"] = vAchievements
    rProgress["achievement_count"] = sum(vItem["unlocked"] for vItem in vAchievements)
    rProgress["player"] = build_player_card(pDatabaseFile, vActivity, rProgress, vToday)

    return rProgress


def get_total_xp(pDatabaseFile):
    """Retourne le total des points, sans tirer de quête : lu souvent, il reste léger."""

    rTotal = count_total_xp(load_activity(pDatabaseFile))

    return rTotal
