"""Fête des gains : points, quêtes, trophées et niveau, entre deux relectures"""

from gui.progress_widgets import TOAST_GAP_MS, CelebrationOverlay, show_xp_gain
from gui.sounds import play_success
from utils.logger import get_logger

logger = get_logger(__name__)


def find_new_successes(pPrevious, pProgress):
    """Retourne les quêtes réussies et les trophées obtenus depuis la relecture."""
    vDoneBefore = {vQuest["id"] for vQuest in pPrevious["quests"] if vQuest["done"]}
    vUnlockedBefore = {
        vItem["id"] for vItem in pPrevious["achievements"] if vItem["unlocked"]
    }

    rSuccesses = (
        [
            vQuest
            for vQuest in pProgress["quests"]
            if vQuest["done"] and vQuest["id"] not in vDoneBefore
        ],
        [
            vItem
            for vItem in pProgress["achievements"]
            if vItem["unlocked"] and vItem["id"] not in vUnlockedBefore
        ],
    )

    return rSuccesses


def celebrate(pWindow, pAnchor, pPrevious, pProgress, pMode):
    """Montre les points gagnés, les quêtes réussies et un nouveau niveau."""
    vGain = pProgress["xp"] - pPrevious["xp"]
    vQuests, vAchievements = find_new_successes(pPrevious, pProgress)
    vLevelUp = pProgress["level"] > pPrevious["level"]
    vDelay = 0

    if vGain > 0:
        show_xp_gain(pWindow, pAnchor, f"+{vGain} XP")
        vDelay += TOAST_GAP_MS

    for vQuest in vQuests:
        logger.info("Quête réussie affichée : %s", vQuest["label"])
        show_xp_gain(pWindow, pAnchor, f"Quête réussie : {vQuest['label']}", vDelay)
        vDelay += TOAST_GAP_MS

    for vItem in vAchievements:
        show_xp_gain(pWindow, pAnchor, f"Trophée obtenu : {vItem['title']}", vDelay)
        vDelay += TOAST_GAP_MS

    if vLevelUp:
        logger.info("Niveau %s atteint : %s", pProgress["level"], pProgress["title"])

        if pMode == "full":
            CelebrationOverlay(
                pWindow,
                f"Niveau {pProgress['level']}",
                pProgress["title"],
                f"Prochain titre : {pProgress['next_title']}",
            )
        else:
            show_xp_gain(
                pWindow,
                pAnchor,
                f"Niveau {pProgress['level']} : {pProgress['title']}",
                vDelay,
            )

    # Un son court pour une quête, un trophée ou un niveau ; pas pour de simples points
    if (vLevelUp or vQuests or vAchievements) and pProgress.get("cosmetics", {}).get(
        "sounds"
    ):
        play_success()
