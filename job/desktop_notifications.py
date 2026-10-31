"""Notifications du bureau : quoi signaler, quand, et jamais plus de trois par jour

Six situations méritent une notification : les relances du jour, une offre
récente très proche du profil, une nouvelle offre d'un employeur suivi, une
quête du jour presque terminée, le soir une série sur le point de s'arrêter et,
le lundi, le bilan de la semaine écoulée. Chacune n'est signalée qu'une fois ;
les heures calmes et le plafond quotidien des Paramètres évitent de lasser.
"""

from datetime import timedelta

from job.application_tracking import get_due_follow_ups
from job.companies import find_preferred_offers
from job.progress import build_progress
from job.settings import load_settings
from job.statistics import find_hot_offers
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Notifications déjà montrées, par jour
NOTIFICATIONS_KEY = "desktop_notifications"
OFFER_SCORE = 80
QUEST_SHARE = 0.6
STREAK_EVENING_HOUR = 19
MIN_STREAK = 2
KEPT_DAYS = 7


def is_quiet(pHour, pStart, pEnd):
    """Indique si l'heure tombe dans les heures calmes, qui peuvent passer minuit."""

    if pStart == pEnd:
        return False

    rQuiet = (
        pStart <= pHour < pEnd if pStart < pEnd else pHour >= pStart or pHour < pEnd
    )

    return rQuiet


def collect_candidates(pDatabaseFile, pNow):
    """Retourne les notifications possibles, la plus utile d'abord.

    Chacune a une clé, qui empêche de la répéter, un titre, un texte et la page
    à ouvrir d'un clic.
    """

    vToday = pNow.date().isoformat()
    rCandidates = []
    vFollowUps = get_due_follow_ups(pDatabaseFile, pNow)

    if vFollowUps:
        vFirst = vFollowUps[0]
        rCandidates.append(
            {
                "key": f"follow-ups-{vToday}",
                "title": f"{len(vFollowUps)} relance(s) à faire",
                "text": f"{vFirst.get('title') or 'Candidature'}"
                + (f" chez {vFirst['company']}" if vFirst.get("company") else "")
                + (" et d'autres" if len(vFollowUps) > 1 else ""),
                "page": "applications",
            }
        )

    for vOffer in find_hot_offers(pDatabaseFile, pNow):
        if (vOffer.get("match_score") or 0) >= OFFER_SCORE:
            rCandidates.append(
                {
                    "key": f"offer-{vOffer['source']}-{vOffer['source_id']}",
                    "title": f"Offre à {vOffer['match_score']} % de votre profil",
                    "text": f"{vOffer.get('title') or 'Offre'}"
                    + (f" chez {vOffer['company']}" if vOffer.get("company") else ""),
                    "page": "offers",
                }
            )

    # Employeurs suivis : leurs offres vues depuis la veille
    for vOffer in find_preferred_offers(pDatabaseFile, pNow - timedelta(days=1)):
        rCandidates.append(
            {
                "key": f"offer-{vOffer['source']}-{vOffer['source_id']}",
                "title": f"Nouvelle offre chez {vOffer.get('company')}",
                "text": vOffer.get("title") or "Offre",
                "page": "offers",
            }
        )

    vProgress = build_progress(pDatabaseFile, pNow)

    # Le bilan de la semaine écoulée s'annonce le lundi
    if pNow.weekday() == 0 and (vSeason := vProgress.get("season")):
        rCandidates.append(
            {
                "key": f"season-{vSeason['key']}",
                "title": f"Bilan de la {vSeason['title']}",
                "text": vSeason["summary"],
                "page": "progress",
            }
        )

    for vQuest in vProgress["quests"]:
        if (
            not vQuest["weekly"]
            and not vQuest["done"]
            and vQuest["progress"] >= QUEST_SHARE * vQuest["target"]
        ):
            rCandidates.append(
                {
                    "key": f"quest-{vQuest['id']}-{vToday}",
                    "title": "Quête presque terminée",
                    "text": f"Plus que {vQuest['target'] - vQuest['progress']} pour "
                    f"« {vQuest['label']} »",
                    "page": "progress",
                }
            )

    if (
        pNow.hour >= STREAK_EVENING_HOUR
        and vProgress["streak"] >= MIN_STREAK
        and not vProgress["active_today"]
    ):
        rCandidates.append(
            {
                "key": f"streak-{vToday}",
                "title": f"Série de {vProgress['streak']} jours en danger",
                "text": "Une révision ce soir suffit à la garder.",
                "page": "quiz",
            }
        )

    return rCandidates


def pick_notification(pDatabaseFile, pNow):
    """Retourne la prochaine notification à montrer, et la note comme montrée.

    Rien n'est retourné pendant les heures calmes, une fois le plafond du jour
    atteint ou quand tout a déjà été signalé.
    """

    vSettings = load_settings(pDatabaseFile)
    vLimit = vSettings["notification_daily_limit"]

    if not vLimit or is_quiet(
        pNow.hour,
        vSettings["notification_quiet_start"],
        vSettings["notification_quiet_end"],
    ):
        return None

    vLog = load_json_setting(pDatabaseFile, NOTIFICATIONS_KEY, {}, dict)
    vToday = pNow.date().isoformat()
    vShown = {vKey for vKeys in vLog.values() for vKey in vKeys}

    if len(vLog.get(vToday, [])) >= vLimit:
        return None

    rNotification = next(
        (
            vCandidate
            for vCandidate in collect_candidates(pDatabaseFile, pNow)
            if vCandidate["key"] not in vShown
        ),
        None,
    )

    if rNotification is not None:
        vLog[vToday] = [*vLog.get(vToday, []), rNotification["key"]]
        vLog = {vDay: vLog[vDay] for vDay in sorted(vLog)[-KEPT_DAYS:]}
        save_json_setting(pDatabaseFile, NOTIFICATIONS_KEY, vLog)
        logger.info("Notification du bureau : %s", rNotification["title"])

    return rNotification
