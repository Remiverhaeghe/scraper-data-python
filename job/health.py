"""État de santé de l'application : sauvegardes, planification, sources et place"""

from datetime import datetime, timedelta
from pathlib import Path

from config import BACKUP_NAS_DIRECTORY, WEB_SCHEME, WEB_TLS_CERTFILE
from job.application_replies import LAST_CHECK_KEY as LAST_REPLY_CHECK_KEY
from job.application_replies import REPLY_CHECK_HOURS, load_pending_replies
from job.followed_availability import LAST_CHECK_KEY
from job.geocoding import load_home
from job.location import FRANCE
from job.restore_check import load_restore_check
from job.mobile_sync import get_last_phone_sync, get_mobile_token
from job.schedule import get_scheduler_heartbeat, load_schedule
from job.sources.registry import SOURCES
from job.statistics import load_source_review
from storage.backup import (
    describe_backups,
    get_last_auto_backup_time,
    get_last_nas_copy_time,
    list_damaged_backups,
)
from storage.geo_cache import count_offer_positions
from storage.history_repository import get_history
from storage.job_offers import count_empty_fields, get_offers
from storage.settings_repository import get_setting_values, load_json_setting
from utils.logger import get_logger
from utils.mailer import get_missing_email_settings
from utils.permissions import find_permission_problems
from utils.tls import read_expiry

logger = get_logger(__name__)

# Au-delà, la sauvegarde automatique n'a manifestement plus lieu
BACKUP_WARNING_DELAY = timedelta(days=2)

# Fin proche du certificat HTTPS : orange à un mois, rouge à une semaine
CERTIFICATE_WARNING_DAYS = 30
CERTIFICATE_DANGER_DAYS = 7

# Offres récentes dont la description manquante est comptée
DESCRIPTION_DAYS = 7

# Le planificateur passe chaque minute : au-delà, il est arrêté ou bloqué.
SCHEDULER_SILENT_DELAY = timedelta(minutes=10)

# Au-delà, le téléphone ne s'est plus synchronisé depuis longtemps
PHONE_SYNC_WARNING_DELAY = timedelta(days=2)

# Recherches de suite sans aucune offre au-delà desquelles une source qui en
# renvoyait est signalée : son API a peut-être changé ou sa clé expiré.
SILENT_SOURCE_RUNS = 3

# Une source dont plus de la moitié des offres récentes ont un champ vide a
# sans doute changé le format de son API (lieu déplacé, champ renommé).
FORMAT_CHECK_DAYS = 14
FORMAT_MIN_OFFERS = 10
FORMAT_EMPTY_SHARE = 0.5
FORMAT_FIELDS = {"title": "titre", "location": "lieu", "company": "entreprise"}


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


def check_restore_test(pDatabaseFile):
    """Rappelle le résultat du dernier essai de restauration, fait chaque mois."""

    vResult = load_restore_check(pDatabaseFile)

    if not vResult:
        return ("Pas encore essayée : le planificateur le fait chaque mois", "muted")

    vDate = datetime.fromisoformat(vResult["date"])

    rCheck = (
        f"{vDate:%d/%m/%Y} : {vResult['message']}",
        "success" if vResult["success"] else "danger",
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


def check_scheduler(pDatabaseFile, pNow):
    """Vérifie que le planificateur tourne : il fait les tâches de fond."""

    vLast = get_scheduler_heartbeat(pDatabaseFile)

    if vLast is None:
        rCheck = (
            "Jamais vu tourner : sauvegardes, descriptions et récapitulatifs "
            "attendent. Lancez python -m scheduler, ou python -m "
            "tools.windows_startup pour le démarrer avec la session.",
            "warning",
        )
    elif pNow - vLast > SCHEDULER_SILENT_DELAY:
        rCheck = (
            f"Arrêté depuis le {vLast:%d/%m/%Y %H:%M} : les tâches de fond attendent",
            "danger",
        )
    else:
        rCheck = (f"En marche, dernier passage à {vLast:%H:%M}", "success")

    return rCheck


def check_last_run(pDatabaseFile):
    """Vérifie le résultat de la dernière recherche."""

    vHistory = get_history(pDatabaseFile, 1)

    if not vHistory:
        rCheck = ("Aucune recherche pour le moment", "muted")
    else:
        vEntry = vHistory[0]
        vDate = datetime.fromisoformat(str(vEntry.started_at)[:19])

        if vEntry.status == "success":
            rCheck = (
                f"{vDate:%d/%m/%Y %H:%M} : {vEntry.item_count} offre(s)",
                "success",
            )
        # Partielle : des offres reçues, mais au moins une source en erreur
        elif vEntry.status == "partial":
            rCheck = (
                f"{vDate:%d/%m/%Y %H:%M} : {vEntry.item_count} offre(s), "
                f"source(s) en erreur : {vEntry.error_message}",
                "warning",
            )
        else:
            rCheck = (
                f"{vDate:%d/%m/%Y %H:%M} : {vEntry.error_message or 'en échec'}",
                "danger",
            )

    return rCheck


def check_gmail(pDatabaseFile, pNow):
    """Vérifie la lecture des réponses de recruteurs dans Gmail."""

    vMissing = get_missing_email_settings()

    if vMissing:
        return (f"Non configuré : {', '.join(vMissing)} dans .env", "muted")

    vLast = load_json_setting(pDatabaseFile, LAST_REPLY_CHECK_KEY, None, str)

    if not vLast:
        return ("Configuré, pas encore lu par le planificateur", "warning")

    vDate = datetime.fromisoformat(vLast)
    vPending = len(load_pending_replies(pDatabaseFile))

    rCheck = (
        f"Lu {format_age(vDate, pNow)} à {vDate:%H:%M} · "
        f"{vPending} réponse(s) à traiter dans Candidatures",
        (
            "success"
            if pNow - vDate < timedelta(hours=REPLY_CHECK_HOURS * 2)
            else "warning"
        ),
    )

    return rCheck


def check_descriptions(pDatabaseFile, pNow):
    """Compte les offres récentes sans description, lue seulement à l'ouverture."""

    vOffers = get_offers(
        pDatabaseFile,
        pSeenSince=pNow - timedelta(days=DESCRIPTION_DAYS),
        pHideIgnored=True,
    )
    vMissing = int(vOffers["description"].isna().sum()) if not vOffers.empty else 0

    rCheck = (
        (
            f"{vMissing} offre(s) des {DESCRIPTION_DAYS} derniers jours sans "
            "description : SmartRecruiters et Workday les complètent en tâche de "
            "fond, score moins précis en attendant",
            "warning" if vMissing > len(vOffers) / 2 else "muted",
        )
        if vMissing
        else ("Toutes les offres récentes ont une description", "success")
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


def find_format_changes(pCounts):
    """Retourne « Source : lieu vide pour 85 % » pour chaque champ trop souvent vide."""

    rChanges = [
        f"{SOURCES[vRow['source']].label if vRow['source'] in SOURCES else vRow['source']}"
        f" : {vLabel} vide pour {round(100 * vRow[vField] / vRow['total'])} %"
        for vRow in pCounts
        if vRow["total"] >= FORMAT_MIN_OFFERS
        for vField, vLabel in FORMAT_FIELDS.items()
        if vRow[vField] > FORMAT_EMPTY_SHARE * vRow["total"]
    ]

    return rChanges


def check_source_formats(pDatabaseFile, pNow):
    """Signale les sources dont les offres récentes arrivent avec des champs vides."""

    vChanges = find_format_changes(
        count_empty_fields(pDatabaseFile, pNow - timedelta(days=FORMAT_CHECK_DAYS))
    )

    rCheck = (
        (
            "; ".join(vChanges)
            + ". Format de l'API modifié ? Comparez une offre récente à la source.",
            "warning",
        )
        if vChanges
        else ("Titre, lieu et entreprise lus pour toutes les sources", "success")
    )

    return rCheck


def check_useful_sources(pDatabaseFile):
    """Rappelle les sources à décocher, d'après la revue quotidienne du planificateur."""

    vReview = load_source_review(pDatabaseFile)

    if not vReview:
        rCheck = ("Pas encore revue : faite chaque jour par le planificateur", "muted")
    elif vReview["advice"]:
        rCheck = (vReview["advice"], "warning")
    else:
        rCheck = (
            "Chaque source a donné au moins une offre utile ce mois-ci",
            "success",
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
        ("Restauration éprouvée", lambda: check_restore_test(pDatabaseFile)),
        ("Copie sur le NAS", lambda: check_nas_copy(pDatabaseFile, pNow)),
        ("Planificateur", lambda: check_scheduler(pDatabaseFile, pNow)),
        ("Recherche planifiée", lambda: check_schedule(pDatabaseFile, pNow)),
        ("Dernière recherche", lambda: check_last_run(pDatabaseFile)),
        ("Sources", check_sources),
        ("Sources muettes", lambda: check_silent_sources(pDatabaseFile)),
        ("Formats des sources", lambda: check_source_formats(pDatabaseFile, pNow)),
        ("Sources utiles", lambda: check_useful_sources(pDatabaseFile)),
        ("Descriptions", lambda: check_descriptions(pDatabaseFile, pNow)),
        ("Réponses Gmail", lambda: check_gmail(pDatabaseFile, pNow)),
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
