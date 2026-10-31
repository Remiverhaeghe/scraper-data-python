"""Planning de la semaine : entretiens, relances, révisions prévues et quêtes

Les relances et les entretiens viennent des candidatures : les déplacer change
leur date, donc aussi l'abonnement d'agenda (job/calendar.py). Les séances de
révision prévues sont gardées dans les réglages et publiées dans le même agenda.
"""

import uuid
from datetime import date, datetime, timedelta

from job.calendar import INTERVIEW_STATUSES, PLANNED_REVISIONS_KEY, describe_offer
from job.progress import build_progress
from storage.job_applications import get_applications_with_offers, move_application_date
from storage.job_offers import FOLLOW_UP_STATUSES
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

DAY_NAMES = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MAX_LABEL_LENGTH = 80
MAX_REVISIONS = 200


def get_monday(pDay):
    """Retourne le lundi de la semaine d'un jour."""

    rMonday = pDay - timedelta(days=pDay.weekday())

    return rMonday


def load_planned_revisions(pDatabaseFile):
    """Retourne les séances de révision prévues, bien formées."""

    rRevisions = [
        vItem
        for vItem in load_json_setting(pDatabaseFile, PLANNED_REVISIONS_KEY, [], list)
        if isinstance(vItem, dict) and vItem.get("id") and vItem.get("day")
    ]

    return rRevisions


def collect_items(pDatabaseFile):
    """Retourne toutes les tâches datées : (jour, tâche)."""

    rItems = []

    for vApplication in get_applications_with_offers(pDatabaseFile, INTERVIEW_STATUSES):
        vOffer = describe_offer(vApplication)
        vKey = f"{vApplication['source']}|{vApplication['source_id']}"

        if (
            vApplication["status"] in FOLLOW_UP_STATUSES
            and vApplication["follow_up_date"]
        ):
            rItems.append(
                (
                    datetime.fromisoformat(vApplication["follow_up_date"]).date(),
                    {
                        "id": f"follow-up|{vKey}",
                        "kind": "follow-up",
                        "label": f"Relancer : {vOffer}",
                        "time": "",
                        "page": "applications",
                    },
                )
            )

        if vApplication["interview_at"]:
            vStart = datetime.fromisoformat(vApplication["interview_at"])
            rItems.append(
                (
                    vStart.date(),
                    {
                        "id": f"interview|{vKey}",
                        "kind": "interview",
                        "label": f"Entretien : {vOffer}",
                        "time": vStart.strftime("%H:%M"),
                        "page": "applications",
                    },
                )
            )

    for vRevision in load_planned_revisions(pDatabaseFile):
        rItems.append(
            (
                date.fromisoformat(vRevision["day"]),
                {
                    "id": f"revision|{vRevision['id']}",
                    "kind": "revision",
                    "label": f"Réviser : {vRevision['label']}",
                    "time": "",
                    "page": "quiz",
                },
            )
        )

    return rItems


def build_week(pDatabaseFile, pDay, pNow=None):
    """Retourne la semaine du jour donné : sept jours de tâches et les quêtes de la semaine."""

    vMonday = get_monday(pDay)
    vToday = (pNow or datetime.now()).date()
    vDays = [
        {
            "date": vMonday + timedelta(days=vOffset),
            "name": DAY_NAMES[vOffset],
            "today": vMonday + timedelta(days=vOffset) == vToday,
            "items": [],
        }
        for vOffset in range(7)
    ]

    for vDay, vItem in collect_items(pDatabaseFile):
        vOffset = (vDay - vMonday).days

        if 0 <= vOffset < 7:
            vDays[vOffset]["items"].append(vItem)

    for vDay in vDays:
        # Entretiens à l'heure d'abord, puis relances et révisions
        vDay["items"].sort(key=lambda pItem: (pItem["time"] or "99", pItem["label"]))

    rWeek = {
        "monday": vMonday,
        "previous": vMonday - timedelta(days=7),
        "next": vMonday + timedelta(days=7),
        "days": vDays,
        "quests": [
            vQuest
            for vQuest in build_progress(pDatabaseFile, pNow)["quests"]
            if vQuest["weekly"]
        ],
    }

    return rWeek


def move_item(pDatabaseFile, pItemId, pDay):
    """Déplace une tâche à un autre jour, en gardant l'heure d'un entretien.

    Lève ValueError pour une tâche inconnue.
    """

    vKind, _, vKey = str(pItemId).partition("|")

    if vKind in ("follow-up", "interview"):
        vSource, _, vSourceId = vKey.partition("|")
        vColumn = "follow_up_date" if vKind == "follow-up" else "interview_at"
        vCurrent = next(
            (
                vApplication[vColumn]
                for vApplication in get_applications_with_offers(
                    pDatabaseFile, INTERVIEW_STATUSES
                )
                if vApplication["source"] == vSource
                and str(vApplication["source_id"]) == vSourceId
                and vApplication[vColumn]
            ),
            None,
        )

        if vCurrent is None:
            raise ValueError("Tâche introuvable.")

        # Une date sans heure le reste ; un entretien garde son heure.
        vValue = (
            datetime.combine(pDay, datetime.fromisoformat(vCurrent).time())
            if "T" in vCurrent or " " in vCurrent
            else pDay
        )
        move_application_date(pDatabaseFile, vSource, vSourceId, vColumn, vValue)
    elif vKind == "revision":
        vRevisions = load_planned_revisions(pDatabaseFile)

        if not any(vItem["id"] == vKey for vItem in vRevisions):
            raise ValueError("Tâche introuvable.")

        save_json_setting(
            pDatabaseFile,
            PLANNED_REVISIONS_KEY,
            [
                {**vItem, "day": pDay.isoformat()} if vItem["id"] == vKey else vItem
                for vItem in vRevisions
            ],
        )
    else:
        raise ValueError("Tâche introuvable.")

    logger.info("Planning : tâche %s déplacée au %s", vKind, pDay.isoformat())


def add_revision(pDatabaseFile, pDay, pLabel):
    """Prévoit une séance de révision ; lève ValueError sans intitulé ou si la liste est pleine."""

    vLabel = " ".join(str(pLabel or "").split())[:MAX_LABEL_LENGTH]

    if not vLabel:
        raise ValueError("Indiquez ce que vous comptez réviser.")

    vRevisions = load_planned_revisions(pDatabaseFile)

    if len(vRevisions) >= MAX_REVISIONS:
        raise ValueError(f"{MAX_REVISIONS} séances prévues au plus.")

    vRevisions.append(
        {"id": uuid.uuid4().hex[:12], "day": pDay.isoformat(), "label": vLabel}
    )
    save_json_setting(pDatabaseFile, PLANNED_REVISIONS_KEY, vRevisions)


def delete_revision(pDatabaseFile, pRevisionId):
    """Retire une séance de révision prévue."""

    save_json_setting(
        pDatabaseFile,
        PLANNED_REVISIONS_KEY,
        [
            vItem
            for vItem in load_planned_revisions(pDatabaseFile)
            if vItem["id"] != pRevisionId
        ],
    )
