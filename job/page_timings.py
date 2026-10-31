"""Pages lentes du bureau et du site : durées notées et pages à surveiller"""

from datetime import datetime, timedelta

from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

SLOW_PAGES_KEY = "slow_pages"

# Au-delà, la durée est journalisée et gardée
SLOW_PAGE_SECONDS = 1.0

# Une page est signalée quand elle dépasse ALERT_SECONDS au moins ALERT_COUNT
# fois sur les KEPT_DAYS derniers jours : un ralentissement isolé ne compte pas.
ALERT_SECONDS = 2.0
ALERT_COUNT = 3
KEPT_DAYS = 7
KEPT_PER_PAGE = 20


def record_page_time(pDatabaseFile, pPage, pSeconds, pNow):
    """Journalise et garde la durée d'une page lente ; une page rapide est ignorée."""

    if pSeconds <= SLOW_PAGE_SECONDS:
        return

    logger.warning("Page lente : %s en %.1f s", pPage, pSeconds)

    # La mesure ne doit jamais faire échouer la page qu'elle observe.
    try:
        vTimings = load_json_setting(pDatabaseFile, SLOW_PAGES_KEY, {}, dict)
        vTimings[pPage] = [
            *vTimings.get(pPage, []),
            [pNow.isoformat(timespec="seconds"), round(pSeconds, 1)],
        ][-KEPT_PER_PAGE:]
        save_json_setting(pDatabaseFile, SLOW_PAGES_KEY, keep_recent(vTimings, pNow))

    except Exception:
        logger.exception("Impossible de garder la durée de la page %s", pPage)


def keep_recent(pTimings, pNow):
    """Retourne les durées des KEPT_DAYS derniers jours, sans les pages vidées."""

    vSince = pNow - timedelta(days=KEPT_DAYS)
    rTimings = {}

    for vPage, vEntries in pTimings.items():
        vRecent = [
            vEntry
            for vEntry in vEntries
            if isinstance(vEntry, list)
            and len(vEntry) == 2
            and datetime.fromisoformat(vEntry[0]) >= vSince
        ]

        if vRecent:
            rTimings[vPage] = vRecent

    return rTimings


def find_slow_pages(pTimings, pNow):
    """Retourne les pages lentes à répétition, la plus lente d'abord."""

    rPages = []

    for vPage, vEntries in keep_recent(pTimings, pNow).items():
        vSlow = [vSeconds for _, vSeconds in vEntries if vSeconds > ALERT_SECONDS]

        if len(vSlow) >= ALERT_COUNT:
            rPages.append({"page": vPage, "count": len(vSlow), "max": max(vSlow)})

    rPages.sort(key=lambda vPage: vPage["max"], reverse=True)

    return rPages


def load_slow_pages(pDatabaseFile, pNow):
    """Retourne les pages lentes à répétition gardées dans la base."""

    rPages = find_slow_pages(
        load_json_setting(pDatabaseFile, SLOW_PAGES_KEY, {}, dict), pNow
    )

    return rPages


def describe_slow_pages(pPages):
    """Résume les pages lentes en une ligne : page, nombre de fois et pire durée."""

    rText = " ; ".join(
        f"{vPage['page']} ({vPage['count']} fois, jusqu'à {vPage['max']:.1f} s)"
        for vPage in pPages
    )

    return rText
