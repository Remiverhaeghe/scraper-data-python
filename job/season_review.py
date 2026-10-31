"""Bilan de la « saison » : la semaine écoulée, du lundi au dimanche

Chaque lundi, la semaine qui vient de finir est résumée : XP gagnée, jours
actifs, quêtes, candidatures, révisions et entretiens, comparés à la semaine
d'avant. Une médaille récompense la part des quêtes proposées réussies. Le bilan est
calculé à partir de l'activité déjà lue par la progression : rien n'est stocké.
"""

from datetime import timedelta

# Séries du bilan : clé, libellé, actions additionnées (vide : points ou jours)
STATISTICS = (
    ("xp", "XP gagnée", ()),
    ("active_days", "Jours actifs", ()),
    ("quests", "Quêtes réussies", ("daily_quest", "weekly_quest")),
    ("applications", "Candidatures", ("applied",)),
    ("answers", "Questions révisées", ("answer_right", "answer_wrong")),
    ("interviews", "Entretiens obtenus", ("interview",)),
)
QUEST_ACTIONS = ("daily_quest", "weekly_quest")

# Médaille selon la part des quêtes proposées dans la semaine réussies
MEDALS = (
    (0.75, "or", "Médaille d'or"),
    (0.4, "argent", "Médaille d'argent"),
    (0.15, "bronze", "Médaille de bronze"),
)
MEDAL_COLORS = {"or": "#EAB308", "argent": "#94A3B8", "bronze": "#B45309"}

# Semaines passées comparées pour reconnaître un record
RECORD_WEEKS = 8


def summarize_week(pActivity, pMonday):
    """Retourne les chiffres d'une semaine commençant le lundi donné."""

    vDays = [pActivity.get(pMonday + timedelta(days=vOffset)) for vOffset in range(7)]
    vDays = [vDay for vDay in vDays if vDay]

    rSummary = {
        "xp": sum(vDay["xp"] for vDay in vDays),
        # Une quête validée seule ne fait pas un jour actif
        "active_days": sum(
            any(vAction not in QUEST_ACTIONS for vAction in vDay["actions"])
            for vDay in vDays
        ),
        **{
            vKey: sum(
                vDay["actions"].get(vAction, 0)
                for vDay in vDays
                for vAction in vActions
            )
            for vKey, _, vActions in STATISTICS
            if vActions
        },
    }

    return rSummary


def get_medal(pQuests, pQuestCount):
    """Retourne la médaille méritée par les quêtes réussies sur celles proposées, ou None."""

    vShare = pQuests / max(pQuestCount, 1)

    rMedal = next(
        (
            {
                "id": vId,
                "label": f"{vLabel} : {pQuests} quêtes sur {pQuestCount}",
                "color": MEDAL_COLORS[vId],
            }
            for vMinimum, vId, vLabel in MEDALS
            if vShare >= vMinimum
        ),
        None,
    )

    return rMedal


def describe_trend(pCurrent, pPrevious):
    """Retourne l'évolution lisible d'une série : « +3 », « -1 » ou « = »."""

    vDelta = pCurrent - pPrevious

    rTrend = f"{vDelta:+d}" if vDelta else "="

    return rTrend


def build_season_review(pActivity, pToday, pQuestCount):
    """Retourne le bilan de la semaine écoulée, ou None si elle a été sans activité.

    pQuestCount est le nombre de quêtes proposées en une semaine.
    """

    vMonday = pToday - timedelta(days=pToday.weekday())
    vStart = vMonday - timedelta(days=7)
    vCurrent = summarize_week(pActivity, vStart)

    if not vCurrent["xp"]:
        return None

    vPrevious = summarize_week(pActivity, vStart - timedelta(days=7))
    vPastXp = [
        summarize_week(pActivity, vStart - timedelta(days=7 * vWeeks))["xp"]
        for vWeeks in range(1, RECORD_WEEKS + 1)
    ]
    vBestDay = max(
        (vStart + timedelta(days=vOffset) for vOffset in range(7)),
        key=lambda pDay: pActivity.get(pDay, {}).get("xp", 0),
    )
    vYear, vWeek, _ = vStart.isocalendar()
    vDelta = vCurrent["xp"] - vPrevious["xp"]

    rReview = {
        "key": f"{vYear}-W{vWeek:02d}",
        "title": f"Saison {vWeek}",
        "start": vStart.isoformat(),
        "end": (vStart + timedelta(days=6)).isoformat(),
        "statistics": [
            {
                "key": vKey,
                "label": vLabel,
                "value": vCurrent[vKey],
                "previous": vPrevious[vKey],
                "trend": describe_trend(vCurrent[vKey], vPrevious[vKey]),
            }
            for vKey, vLabel, _ in STATISTICS
        ],
        "best_day": {
            "day": vBestDay.isoformat(),
            "xp": pActivity[vBestDay]["xp"],
        },
        "medal": get_medal(vCurrent["quests"], pQuestCount),
        # Record : mieux que chacune des semaines passées comparées, s'il y en a eu
        "record": any(vPastXp) and vCurrent["xp"] > max(vPastXp),
        "summary": (
            f"{vCurrent['xp']} XP, {vDelta:+d} par rapport à la semaine précédente"
            if vDelta
            else f"{vCurrent['xp']} XP, autant que la semaine précédente"
        ),
    }

    return rReview
