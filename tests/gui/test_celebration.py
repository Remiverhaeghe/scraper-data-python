"""Tests de la fête des gains"""

from gui.celebration import find_new_successes


def build_progress(pDoneQuests, pUnlocked):
    """Construit une progression avec deux quêtes et deux trophées."""

    rProgress = {
        "quests": [
            {"id": vId, "label": vId, "done": vId in pDoneQuests} for vId in ("a", "b")
        ],
        "achievements": [
            {"id": vId, "title": vId, "unlocked": vId in pUnlocked}
            for vId in ("x", "y")
        ],
    }

    return rProgress


def test_only_new_successes_are_returned():
    """Vérifie que seuls les quêtes et trophées obtenus depuis la relecture sortent."""

    vQuests, vAchievements = find_new_successes(
        build_progress({"a"}, {"x"}), build_progress({"a", "b"}, {"x", "y"})
    )

    assert [vQuest["id"] for vQuest in vQuests] == ["b"]
    assert [vItem["id"] for vItem in vAchievements] == ["y"]
    assert find_new_successes(
        build_progress({"a"}, set()), build_progress({"a"}, set())
    ) == ([], [])
