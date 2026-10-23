"""État de santé de l'application : sauvegardes, planification, sources et place"""

from datetime import datetime, timedelta
from pathlib import Path

from config import BACKUP_NAS_DIRECTORY, WEB_SCHEME, WEB_TLS_CERTFILE
from job.followed_availability import LAST_CHECK_KEY
from job.geocoding import load_home
from job.location import FRANCE
from job.mobile_sync import get_last_phone_sync, get_mobile_token
from job.schedule import load_schedule
from job.sources.registry import SOURCES
from storage.backup import (
    describe_backups,
    get_last_auto_backup_time,
    get_last_nas_copy_time,
    list_damaged_backups,
)
from storage.geo_cache import count_offer_positions
from storage.history_repository import get_history
from storage.settings_repository import get_setting_values
from utils.logger import get_logger
from utils.permissions import find_permission_problems
from utils.tls import read_expiry

logger = get_logger(__name__)

# Au-delà, la sauvegarde automatique n'a manifestement plus lieu
BACKUP_WARNING_DELAY = timedelta(days=2)

# Fin proche du certificat HTTPS : orange à un mois, rouge à une semaine
CERTIFICATE_WARNING_DAYS = 30
CERTIFICATE_DANGER_DAYS = 7

# Au-delà, le téléphone ne s'est plus synchronisé depuis longtemps
PHONE_SYNC_WARNING_DELAY = timedelta(days=2)

# Recherches de suite sans aucune offre au-delà desquelles une source qui en
# renvoyait est signalée : son API a peut-être changé ou sa clé expiré.
SILENT_SOURCE_RUNS = 3


def format_age(pDate, pNow):
    """Décrit l'ancienneté d'une date : aujourd'hui, hier ou il y a n jours."""

    vDays = (pNow.date() - pDate.date()).days

    rText = (
        "aujourd'hui"
        if vDays <= 0
        else ("hier" if vDays == 1 else f"il y a {vDays} jours")
    )

    return rText


def format_size(pBytes):
    """Décrit une taille de fichier en Mo, avec une décimale."""

    rText = f"{pBytes / 1_048_576:.1f} Mo".replace(".", ",")

    return rText


def check_backup(pDatabaseFile, pNow):
    """Vérifie que la sauvegarde automatique a lieu."""

    vLast = get_last_auto_backup_time(pDatabaseFile)

    if vLast is None:
        rCheck = ("Aucune sauvegarde automatique", "warning")
    else:
        rCheck = (
            f"{vLast:%d/%m/%Y %H:%M} ({format_age(vLast, pNow)})",
            "success" if pNow - vLast < BACKUP_WARNING_DELAY else "warning",
        )

    return rCheck


def check_backup_integrity(pDatabaseFile):
    """Signale les sauvegardes écartées par le contrôle d'intégrité."""

    vDamaged = list_damaged_backups(pDatabaseFile)

    rCheck = (
        (
            f"{len(vDamaged)} sauvegarde(s) endommagée(s) mise(s) à l'écart, "
            f"dont {vDamaged[0].name} : voir les journaux",
            "danger",
        )
        if vDamaged
        else ("Contrôle d'intégrité réussi à chaque sauvegarde", "success")
    )

    return rCheck


def check_nas_copy(pDatabaseFile, pNow):
    """Vérifie que les sauvegardes sont copiées sur le NAS, s'il est configuré."""

    if not BACKUP_NAS_DIRECTORY:
        return ("Non configurée : BACKUP_NAS_DIRECTORY dans .env", "muted")

    try:
        vLast = get_last_nas_copy_time(pDatabaseFile)

    except OSError:
        return (
            "NAS injoignable : la copie est retentée au prochain passage",
            "warning",
        )

    rCheck = (
        ("Aucune copie pour le moment", "warning")
        if vLast is None
        else (
            f"{vLast:%d/%m/%Y %H:%M} ({format_age(vLast, pNow)})",
            "success" if pNow - vLast < BACKUP_WARNING_DELAY else "warning",
        )
    )

    return rCheck


def check_schedule(pDatabaseFile, pNow):
    """Vérifie que la recherche planifiée tourne à son rythme."""

    vSchedule = load_schedule(pDatabaseFile)
    vLast = vSchedule["last_run"]

    if not vSchedule["enabled"]:
        rCheck = ("Désactivée", "muted")
    elif vLast is None:
        rCheck = ("Activée, jamais lancée : le planificateur tourne-t-il ?", "warning")
    else:
        # Deux échéances manquées : le planificateur est sans doute arrêté.
        vLate = pNow - vLast > timedelta(hours=2 * vSchedule["interval_hours"])
        rCheck = (
            f"Dernière le {vLast:%d/%m/%Y %H:%M}"
            + (" : en retard, le planificateur tourne-t-il ?" if vLate else ""),
            "warning" if vLate else "success",
        )

    return rCheck


def check_last_run(pDatabaseFile):
    """Vérifie le résultat de la dernière recherche."""

    vHistory = get_history(pDatabaseFile, 1)

    if not vHistory:
        rCheck = ("Aucune recherche pour le moment", "muted")
    else:
        vEntry = vHistory[0]
        vDate = datetime.fromisoformat(str(vEntry["started_at"])[:19])

        rCheck = (
            (f"{vDate:%d/%m/%Y %H:%M} : {vEntry['item_count']} offre(s)", "success")
            if vEntry["status"] == "success"
            else (
                f"{vDate:%d/%m/%Y %H:%M} : {vEntry['error_message'] or 'en échec'}",
                "danger",
            )
        )

    return rCheck


def check_sources():
    """Liste les sources indisponibles faute de configuration."""

    vUnavailable = [
        vDefinition.label
        for vDefinition in SOURCES.values()
        if vDefinition.get_unavailability_reason()
    ]

    rCheck = (
        (f"{len(vUnavailable)} indisponible(s) : {', '.join(vUnavailable)}", "warning")
        if vUnavailable
        else (f"{len(SOURCES)} source(s) disponibles", "success")
    )

    return rCheck


def find_silent_sources(pHistory, pRuns=SILENT_SOURCE_RUNS):
    """Retourne les sources sans offre lors des pRuns dernières recherches qui les
    ont interrogées, alors qu'elles en renvoyaient auparavant.

    pHistory va de la plus récente à la plus ancienne entrée.
    """

    vCounts = {}

    for vEntry in pHistory:
        for vName, vCount in (
            (vEntry.parameters or {}).get("source_counts") or {}
        ).items():
            vCounts.setdefault(vName, []).append(vCount)

    rSilent = [
        vName
        for vName, vValues in vCounts.items()
        if len(vValues) > pRuns and not any(vValues[:pRuns]) and any(vValues[pRuns:])
    ]

    return rSilent


def check_silent_sources(pDatabaseFile):
    """Signale les sources qui ne renvoient plus d'offres."""

    vSilent = [
        SOURCES[vName].label if vName in SOURCES else vName
        for vName in find_silent_sources(get_history(pDatabaseFile))
    ]

    rCheck = (
        (
            f"Plus aucune offre depuis {SILENT_SOURCE_RUNS} recherches : "
            f"{', '.join(vSilent)}. Clé expirée ou API modifiée ? Voir les journaux.",
            "warning",
        )
        if vSilent
        else ("Toutes les sources interrogées renvoient des offres", "success")
    )

    return rCheck


def check_followed_offers(pDatabaseFile):
    """Indique la dernière vérification des liens des offres suivies."""

    vDay = get_setting_values(pDatabaseFile).get(LAST_CHECK_KEY)

    rCheck = (
        (f"Le {datetime.fromisoformat(vDay):%d/%m/%Y}", "success")
        if vDay
        else ("Jamais : faite chaque jour par le planificateur", "muted")
    )

    return rCheck


def check_storage(pDatabaseFile):
    """Mesure la place de la base et de ses sauvegardes."""

    vBackups = describe_backups(pDatabaseFile)
    vDatabaseSize = Path(pDatabaseFile).stat().st_size

    rCheck = (
        f"Base {format_size(vDatabaseSize)}, {len(vBackups)} sauvegarde(s) "
        f"{format_size(sum(vBackup['size'] for vBackup in vBackups))}",
        "muted",
    )

    return rCheck


def check_certificate(pNow, pCertificateFile=None):
    """Vérifie la date de fin du certificat HTTPS du tableau de bord."""

    vCertificateFile = pCertificateFile or WEB_TLS_CERTFILE

    if WEB_SCHEME != "https" and pCertificateFile is None:
        return ("HTTP, sans certificat", "muted")

    try:
        vExpiry = read_expiry(vCertificateFile)

    except (OSError, ValueError):
        return ("Certificat illisible : voir WEB_TLS_CERTFILE", "danger")

    vDays = (vExpiry - pNow).days

    if vDays < CERTIFICATE_DANGER_DAYS:
        vTone = "danger"
    elif vDays < CERTIFICATE_WARNING_DAYS:
        vTone = "warning"
    else:
        vTone = "success"

    rCheck = (f"Valable jusqu'au {vExpiry:%d/%m/%Y} ({max(vDays, 0)} jours)", vTone)

    return rCheck


def check_geocoding(pDatabaseFile):
    """Vérifie que les offres en France sont placées pour le filtre de distance."""

    if load_home(pDatabaseFile) is None:
        return ("Domicile non renseigné dans Paramètres", "muted")

    vTotal, vPlaced = count_offer_positions(pDatabaseFile, FRANCE)

    rCheck = (
        f"{vPlaced} offre(s) placée(s) sur {vTotal} en France",
        "success" if vPlaced >= vTotal / 2 else "warning",
    )

    return rCheck


def check_phone(pDatabaseFile, pNow):
    """Vérifie que l'application mobile se synchronise encore."""

    if not get_mobile_token(pDatabaseFile):
        return ("Application mobile non reliée", "muted")

    vLast = get_last_phone_sync(pDatabaseFile)

    rCheck = (
        ("Jamais synchronisée", "warning")
        if vLast is None
        else (
            f"{vLast:%d/%m/%Y %H:%M} ({format_age(vLast, pNow)})",
            "success" if pNow - vLast < PHONE_SYNC_WARNING_DELAY else "warning",
        )
    )

    return rCheck


def check_permissions():
    """Vérifie les moindres privilèges : compte d'exécution, .env et data/."""

    vProblems = find_permission_problems()

    if vProblems is None:
        return ("Non vérifiés sous Windows", "muted")

    rCheck = (
        ("Compte dédié, .env et data/ protégés", "success")
        if not vProblems
        else ("À corriger : " + " ; ".join(vProblems), "warning")
    )

    return rCheck


def build_health(pDatabaseFile, pNow):
    """Retourne les indicateurs de santé, chacun avec son libellé, sa valeur et sa couleur."""

    vChecks = (
        ("Sauvegarde automatique", lambda: check_backup(pDatabaseFile, pNow)),
        ("Sauvegarde vérifiée", lambda: check_backup_integrity(pDatabaseFile)),
        ("Copie sur le NAS", lambda: check_nas_copy(pDatabaseFile, pNow)),
        ("Recherche planifiée", lambda: check_schedule(pDatabaseFile, pNow)),
        ("Dernière recherche", lambda: check_last_run(pDatabaseFile)),
        ("Sources", check_sources),
        ("Sources muettes", lambda: check_silent_sources(pDatabaseFile)),
        ("Offres suivies vérifiées", lambda: check_followed_offers(pDatabaseFile)),
        ("Place occupée", lambda: check_storage(pDatabaseFile)),
        ("Certificat HTTPS", lambda: check_certificate(pNow)),
        ("Placement des offres", lambda: check_geocoding(pDatabaseFile)),
        ("Application mobile", lambda: check_phone(pDatabaseFile, pNow)),
        ("Droits d'exécution", check_permissions),
    )

    rHealth = []

    for vLabel, vCheck in vChecks:
        # Un indicateur illisible n'empêche pas d'afficher les autres.
        try:
            vValue, vTone = vCheck()

        except Exception:
            logger.exception("Indicateur de santé illisible : %s", vLabel)

            vValue, vTone = "Illisible : voir les journaux", "danger"

        rHealth.append({"label": vLabel, "value": vValue, "tone": vTone})

    return rHealth
