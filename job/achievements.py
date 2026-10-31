"""Trophées et carte joueur, déduits de l'activité déjà en base

Chaque trophée a une condition sur les totaux de l'activité (réponses,
candidatures, entretiens, séries, niveaux). Seule la date d'obtention est
gardée : elle s'affiche, et un trophée sans date est nouveau. Quelques trophées
restent cachés jusqu'à leur obtention, pour l'effet de surprise.
"""

from datetime import timedelta

from job.code_puzzles import load_puzzle_progress
from job.quiz_exam import load_exam_results
from storage.aptitude_sessions import get_aptitude_sessions
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

UNLOCKED_KEY = "achievements_unlocked"

# Semaines montrées dans la carte d'activité
HEATMAP_WEEKS = 12

# (identifiant, titre, description, icône, statistique, seuil, caché)
ACHIEVEMENTS = (
    (
        "first-answer",
        "Premier pas",
        "Répondre à une question de révision",
        "graduation-cap",
        "answers",
        1,
        False,
    ),
    (
        "answers-100",
        "Révision assidue",
        "Répondre à 100 questions",
        "graduation-cap",
        "answers",
        100,
        False,
    ),
    (
        "answers-1000",
        "Encyclopédie",
        "Répondre à 1 000 questions",
        "graduation-cap",
        "answers",
        1000,
        False,
    ),
    (
        "right-500",
        "Tête bien faite",
        "Donner 500 réponses justes",
        "circle-check",
        "right",
        500,
        False,
    ),
    (
        "first-application",
        "Candidat",
        "Envoyer une première candidature",
        "send",
        "applied",
        1,
        False,
    ),
    (
        "applications-10",
        "Candidat motivé",
        "Envoyer 10 candidatures",
        "send",
        "applied",
        10,
        False,
    ),
    (
        "applications-50",
        "Infatigable",
        "Envoyer 50 candidatures",
        "send",
        "applied",
        50,
        False,
    ),
    (
        "interested-20",
        "Œil de lynx",
        "Repérer 20 offres intéressantes",
        "search",
        "interested",
        20,
        False,
    ),
    (
        "follow-ups-10",
        "Relanceur",
        "Faire 10 relances",
        "bell-ring",
        "follow_up",
        10,
        False,
    ),
    (
        "first-interview",
        "Convoqué",
        "Obtenir un premier entretien",
        "calendar",
        "interview",
        1,
        False,
    ),
    (
        "interviews-5",
        "Habitué des entretiens",
        "Obtenir 5 entretiens",
        "calendar",
        "interview",
        5,
        False,
    ),
    (
        "accepted",
        "Mission accomplie",
        "Accepter un poste",
        "trophy",
        "accepted",
        1,
        False,
    ),
    (
        "challenge-first",
        "Défi relevé",
        "Réussir un premier défi",
        "trophy",
        "challenge_right",
        1,
        False,
    ),
    (
        "challenges-10",
        "Champion des défis",
        "Réussir 10 défis",
        "trophy",
        "challenge_right",
        10,
        False,
    ),
    (
        "git-5",
        "Maître des branches",
        "Terminer 5 niveaux Git",
        "git-branch",
        "git_level",
        5,
        False,
    ),
    (
        "exam-first",
        "Examen blanc",
        "Terminer un examen blanc",
        "timer",
        "exam",
        1,
        False,
    ),
    (
        "exam-90",
        "Major de promo",
        "Obtenir 90 % ou plus à un examen blanc",
        "award",
        "best_exam",
        90,
        False,
    ),
    (
        "streak-3",
        "Lancé",
        "Tenir une série de 3 jours",
        "flame",
        "best_streak",
        3,
        False,
    ),
    (
        "streak-7",
        "Une semaine pleine",
        "Tenir une série de 7 jours",
        "flame",
        "best_streak",
        7,
        False,
    ),
    (
        "streak-30",
        "Inarrêtable",
        "Tenir une série de 30 jours",
        "flame",
        "best_streak",
        30,
        False,
    ),
    (
        "aptitude-first",
        "Candidat préparé",
        "Terminer un test de recrutement",
        "timer",
        "aptitude",
        1,
        False,
    ),
    (
        "aptitude-perfect",
        "Sans faute",
        "Réussir un test de recrutement à 10 sur 10",
        "circle-check",
        "aptitude_perfect",
        1,
        False,
    ),
    (
        "troubleshooting-first",
        "Premier dépannage",
        "Résoudre une panne",
        "wrench",
        "troubleshooting",
        1,
        False,
    ),
    (
        "ladder-all",
        "Automaticien",
        "Réussir les 10 niveaux du simulateur d'automate",
        "cpu",
        "ladder_level",
        10,
        False,
    ),
    (
        "sql-first",
        "Première requête",
        "Réussir un niveau du bac à sable SQL",
        "database",
        "sql_level",
        1,
        False,
    ),
    (
        "sql-all",
        "As du SQL",
        "Réussir les 26 niveaux du bac à sable SQL",
        "database",
        "sql_level",
        26,
        False,
    ),
    (
        "circuit-first",
        "Premier montage",
        "Réussir un montage électrique",
        "zap",
        "circuit_level",
        1,
        False,
    ),
    (
        "circuit-all",
        "Électricien",
        "Réussir les 9 montages électriques",
        "zap",
        "circuit_level",
        9,
        False,
    ),
    (
        "devops-first",
        "Premier build",
        "Réussir un niveau Maven ou Docker",
        "server",
        "devops_level",
        1,
        False,
    ),
    (
        "devops-all",
        "Intégrateur",
        "Réussir les 12 niveaux Maven et Docker",
        "server",
        "devops_level",
        12,
        False,
    ),
    (
        "puzzle-first",
        "Casse-tête",
        "Terminer une série de puzzles de code",
        "code",
        "puzzle_series",
        1,
        False,
    ),
    (
        "puzzle-streak",
        "Sans faute",
        "Enchaîner 10 puzzles de code justes",
        "code",
        "puzzle_best_streak",
        10,
        False,
    ),
    (
        "puzzle-expert",
        "Relecteur confirmé",
        "Atteindre le niveau confirmé des puzzles de code",
        "code",
        "puzzle_level",
        3,
        False,
    ),
    ("level-3", "Technicien", "Atteindre le niveau 3", "star", "level", 3, False),
    (
        "level-5",
        "Technicien expert",
        "Atteindre le niveau 5",
        "star",
        "level",
        5,
        False,
    ),
    ("level-10", "Légende", "Atteindre le niveau 10", "star", "level", 10, False),
    (
        "quests-10",
        "Aventurier",
        "Réussir 10 quêtes",
        "target",
        "daily_quest",
        10,
        False,
    ),
    (
        "weekly-quest",
        "Semaine accomplie",
        "Réussir une quête de la semaine",
        "calendar",
        "weekly_quest",
        1,
        False,
    ),
    (
        "weekend",
        "Week-end studieux",
        "Être actif un samedi et le dimanche suivant",
        "sparkles",
        "weekend",
        1,
        True,
    ),
    (
        "comeback",
        "Retour en force",
        "Revenir après une semaine d'absence",
        "zap",
        "comeback",
        1,
        True,
    ),
    (
        "big-day",
        "Journée record",
        "Gagner 200 XP en une seule journée",
        "zap",
        "best_day_xp",
        200,
        True,
    ),
)

# Actions qui ne comptent pas comme une activité (points des quêtes)
BONUS_ACTIONS = ("daily_quest", "weekly_quest")


def count_actions(pActivity):
    """Retourne le total de chaque action sur toute l'activité."""

    rTotals = {}

    for vDay in pActivity.values():
        for vAction, vCount in vDay["actions"].items():
            rTotals[vAction] = rTotals.get(vAction, 0) + vCount

    return rTotals


def get_active_days(pActivity):
    """Retourne les jours où une action utile a été faite, triés."""

    rDays = sorted(
        vDay
        for vDay, vValues in pActivity.items()
        if any(vAction not in BONUS_ACTIONS for vAction in vValues["actions"])
    )

    return rDays


def has_weekend(pDays):
    """Indique si un samedi et le dimanche suivant ont tous deux été actifs."""

    vDays = set(pDays)

    rWeekend = any(
        vDay.weekday() == 5 and vDay + timedelta(days=1) in vDays for vDay in vDays
    )

    return rWeekend


def has_comeback(pDays):
    """Indique un retour après au moins sept jours sans activité."""

    rComeback = any(
        (vNext - vPrevious).days > 7 for vPrevious, vNext in zip(pDays, pDays[1:])
    )

    return rComeback


def build_statistics(pDatabaseFile, pActivity, pProgress):
    """Retourne les statistiques comparées aux seuils des trophées."""

    vTotals = count_actions(pActivity)
    vDays = get_active_days(pActivity)
    vPuzzles = load_puzzle_progress(pDatabaseFile)

    rStatistics = {
        **vTotals,
        "answers": vTotals.get("answer_right", 0) + vTotals.get("answer_wrong", 0),
        "right": vTotals.get("answer_right", 0),
        "best_exam": max(
            (
                int(vResult.get("score") or 0)
                for vResult in load_exam_results(pDatabaseFile)
            ),
            default=0,
        ),
        "aptitude_perfect": sum(
            vSession["correct"] == vSession["total"]
            for vSession in get_aptitude_sessions(pDatabaseFile)
        ),
        "best_streak": pProgress["best_streak"],
        "level": pProgress["level"],
        "weekend": int(has_weekend(vDays)),
        "comeback": int(has_comeback(vDays)),
        "best_day_xp": max((vDay["xp"] for vDay in pActivity.values()), default=0),
        "active_days": len(vDays),
        "puzzle_best_streak": vPuzzles["best_streak"],
        "puzzle_level": vPuzzles["level"],
    }

    return rStatistics


def evaluate_achievements(pDatabaseFile, pActivity, pProgress, pToday):
    """Retourne les trophées avec leur état ; un trophée nouvellement obtenu est daté.

    Un trophée caché et non obtenu ne montre ni son titre ni sa condition.
    """

    vStatistics = build_statistics(pDatabaseFile, pActivity, pProgress)
    vUnlocked = load_json_setting(pDatabaseFile, UNLOCKED_KEY, {}, dict)
    vNew = []
    rAchievements = []

    for (
        vId,
        vTitle,
        vDescription,
        vIcon,
        vStatistic,
        vThreshold,
        vHidden,
    ) in ACHIEVEMENTS:
        vValue = vStatistics.get(vStatistic, 0)

        if vValue >= vThreshold and vId not in vUnlocked:
            vUnlocked[vId] = pToday.isoformat()
            vNew.append(vId)
            logger.info("Trophée obtenu : %s", vTitle)

        vDone = vId in vUnlocked
        vSecret = vHidden and not vDone

        rAchievements.append(
            {
                "id": vId,
                "title": "Trophée caché" if vSecret else vTitle,
                "description": "À découvrir" if vSecret else vDescription,
                "icon": "star" if vSecret else vIcon,
                "unlocked": vDone,
                "unlocked_on": vUnlocked.get(vId),
                "progress": min(vValue, vThreshold),
                "target": vThreshold,
                "hidden": vSecret,
            }
        )

    if vNew:
        save_json_setting(pDatabaseFile, UNLOCKED_KEY, vUnlocked)

    return rAchievements


def build_player_card(pDatabaseFile, pActivity, pProgress, pToday):
    """Retourne la carte joueur : records et carte d'activité des dernières semaines."""

    vStatistics = build_statistics(pDatabaseFile, pActivity, pProgress)
    vStart = pToday - timedelta(days=pToday.weekday() + 7 * (HEATMAP_WEEKS - 1))

    rCard = {
        "records": [
            {"label": "Réponses de révision", "value": vStatistics["answers"]},
            {"label": "Candidatures envoyées", "value": vStatistics.get("applied", 0)},
            {"label": "Entretiens obtenus", "value": vStatistics.get("interview", 0)},
            {"label": "Jours actifs", "value": vStatistics["active_days"]},
            {"label": "Meilleure journée", "value": f"{vStatistics['best_day_xp']} XP"},
            {
                "label": "Meilleur examen blanc",
                "value": f"{vStatistics['best_exam']} %",
            },
        ],
        # Une colonne par semaine, du lundi au dimanche : comme sur GitHub
        "heatmap": [
            {
                "day": vDay.isoformat(),
                "xp": pActivity.get(vDay, {}).get("xp", 0) if vDay <= pToday else None,
            }
            for vDay in (
                vStart + timedelta(days=vOffset) for vOffset in range(7 * HEATMAP_WEEKS)
            )
        ],
    }

    return rCard


def get_heat_level(pXp):
    """Retourne l'intensité d'une case de la carte d'activité, de 0 à 4."""

    if not pXp:
        rLevel = 0
    elif pXp < 30:
        rLevel = 1
    elif pXp < 80:
        rLevel = 2
    elif pXp < 150:
        rLevel = 3
    else:
        rLevel = 4

    return rLevel


def sort_achievements(pAchievements):
    """Retourne les trophées obtenus d'abord, du plus récent au plus ancien."""

    rSorted = sorted(
        pAchievements, key=lambda pItem: pItem["unlocked_on"] or "", reverse=True
    )
    rSorted.sort(key=lambda pItem: not pItem["unlocked"])

    return rSorted
