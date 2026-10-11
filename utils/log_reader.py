"""Lecture des fichiers de logs pour les afficher dans les interfaces"""

import logging
import re

from utils.logger import LOG_DIRECTORY, LOG_FILE_PREFIX, get_log_day, get_logger

logger = get_logger(__name__)

# Forme d'une ligne écrite avec LOG_FORMAT : date | niveau | module | message
LOG_LINE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \| (\w+) \| ([^|]+?) \| (.*)$"
)

LEVEL_LABELS = {
    "DEBUG": "Débogage",
    "INFO": "Information",
    "WARNING": "Avertissement",
    "ERROR": "Erreur",
    "CRITICAL": "Critique",
}

# Tonalité de couleur de chaque niveau, partagée par le bureau et le web
LEVEL_TONES = {
    "WARNING": "warning",
    "ERROR": "danger",
    "CRITICAL": "danger",
}

# Filtres proposés : niveau minimal affiché
LEVEL_FILTERS = {
    None: "Tous les niveaux",
    "WARNING": "Avertissements et erreurs",
    "ERROR": "Erreurs uniquement",
}

LEGACY_LOG_FILE_NAME = "scraper.log"

# Au-delà, l'utilisateur affine avec les filtres plutôt que de tout parcourir.
MAX_LOG_ENTRIES = 200


def parse_log_file(pFile):
    """Retourne les entrées d'un fichier, dans l'ordre d'écriture.

    Une ligne qui ne commence pas par une date, comme celles d'une trace
    d'erreur, complète le message de l'entrée précédente.
    """

    rEntries = []

    with pFile.open(encoding="utf-8", errors="replace") as vStream:
        for vLine in vStream:
            vLine = vLine.rstrip("\n")
            vMatch = LOG_LINE_PATTERN.match(vLine)

            if vMatch:
                vTime, vLevel, vModule, vMessage = vMatch.groups()
                rEntries.append(
                    {
                        "time": vTime,
                        "level": vLevel,
                        "level_label": LEVEL_LABELS.get(vLevel, vLevel),
                        "module": vModule.strip(),
                        "message": vMessage,
                    }
                )
            elif rEntries and vLine:
                rEntries[-1]["message"] += "\n" + vLine

    return rEntries


def matches_filters(pEntry, pMinimumLevel, pSearch):
    """Indique si une entrée respecte le niveau minimal et le texte recherché."""

    vLevel = logging.getLevelName(pEntry["level"])

    rMatches = (
        pMinimumLevel is None or not isinstance(vLevel, int) or vLevel >= pMinimumLevel
    ) and (
        not pSearch
        or pSearch.lower() in f"{pEntry['module']} {pEntry['message']}".lower()
    )

    return rMatches


def list_log_files(pDirectory=LOG_DIRECTORY):
    """Retourne les fichiers de logs du plus récent au plus ancien."""

    rFiles = sorted(
        (
            vFile
            for vFile in pDirectory.glob(f"{LOG_FILE_PREFIX}*.log")
            if get_log_day(vFile) is not None
        ),
        key=get_log_day,
        reverse=True,
    )

    return rFiles


def read_log_entries(
    pDirectory=LOG_DIRECTORY, pLevel=None, pSearch=None, pLimit=MAX_LOG_ENTRIES
):
    """Retourne les entrées les plus récentes en premier, filtrées et limitées."""

    # Un niveau absent ou inconnu revient à tout afficher.
    vMinimumLevel = (
        logging.getLevelName(pLevel) if pLevel in LEVEL_FILTERS and pLevel else None
    )
    rEntries = []

    for vFile in list_log_files(pDirectory):
        if len(rEntries) >= pLimit:
            break

        for vEntry in reversed(parse_log_file(vFile)):
            if matches_filters(vEntry, vMinimumLevel, pSearch):
                rEntries.append(vEntry)

                if len(rEntries) >= pLimit:
                    break

    return rEntries


def export_logs(pDirectory=LOG_DIRECTORY):
    """Retourne tous les journaux conservés, du plus ancien au plus récent."""

    rText = "".join(
        vFile.read_text(encoding="utf-8", errors="replace")
        for vFile in reversed(list_log_files(pDirectory))
    )

    return rText


def clear_logs(pDirectory=LOG_DIRECTORY):
    """Supprime les anciens journaux et vide celui du jour ; retourne leur nombre.

    Le fichier du jour est vidé plutôt que supprimé : l'application y écrit
    encore et ne le recréerait pas tant que la journée n'a pas changé.
    """

    vFiles = list_log_files(pDirectory)

    # Ancien fichier unique, antérieur au découpage par jour : il n'est plus écrit.
    vLegacyFile = pDirectory / LEGACY_LOG_FILE_NAME

    if vLegacyFile.exists():
        vFiles.append(vLegacyFile)

    for vIndex, vFile in enumerate(vFiles):
        try:
            if vIndex == 0:
                vFile.write_text("", encoding="utf-8")
            else:
                vFile.unlink()

        except OSError as vException:
            logger.warning("Journal non effacé : %s (%s)", vFile.name, vException)

    logger.info("Journaux remis à zéro : %s fichier(s) traité(s)", len(vFiles))

    rCount = len(vFiles)

    return rCount
