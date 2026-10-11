"""Configuration du système de logs : un fichier par jour, conservé un temps limité"""

import logging
import os
from datetime import date, timedelta
from pathlib import Path

# Dossier des logs, à la racine du projet quel que soit le dossier de lancement
LOG_DIRECTORY = Path(__file__).resolve().parent.parent / "logs"

LOG_FILE_PREFIX = "scraper-"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

# Au-delà, les fichiers de logs sont supprimés ; modifiable par LOG_RETENTION_DAYS
DEFAULT_LOG_RETENTION_DAYS = 14


def get_retention_days():
    """Retourne la durée de conservation des logs, en jours."""

    try:
        rDays = max(int(os.getenv("LOG_RETENTION_DAYS", "")), 1)

    except ValueError:
        rDays = DEFAULT_LOG_RETENTION_DAYS

    return rDays


def get_log_file(pDirectory, pDay):
    """Retourne le fichier de logs d'une journée."""

    rFile = pDirectory / f"{LOG_FILE_PREFIX}{pDay.isoformat()}.log"

    return rFile


def get_log_day(pFile):
    """Retourne la journée d'un fichier de logs, ou None pour un autre fichier."""

    try:
        rDay = date.fromisoformat(pFile.stem.removeprefix(LOG_FILE_PREFIX))

    except ValueError:
        rDay = None

    return rDay


def purge_old_logs(pDirectory, pToday, pRetentionDays):
    """Supprime les fichiers de logs plus anciens que la durée de conservation."""

    vLimit = pToday - timedelta(days=pRetentionDays)
    rDeleted = []

    for vFile in pDirectory.glob(f"{LOG_FILE_PREFIX}*.log"):
        vDay = get_log_day(vFile)

        if vDay is not None and vDay < vLimit:
            try:
                vFile.unlink()
                rDeleted.append(vFile.name)

            # Un autre processus peut avoir supprimé le fichier entre-temps.
            except OSError:
                pass

    return rDeleted


class DailyFileHandler(logging.FileHandler):
    """Écrit dans le fichier du jour et passe au suivant à minuit.

    Contrairement à une rotation par renommage, aucun fichier n'est renommé :
    le bureau, le web et le planificateur peuvent écrire en même temps.
    """

    def __init__(self, pDirectory, pRetentionDays):
        """Ouvre le fichier du jour après avoir supprimé les plus anciens."""
        pDirectory.mkdir(parents=True, exist_ok=True)

        self.directory = pDirectory
        self.retention_days = pRetentionDays
        self.day = date.today()

        purge_old_logs(pDirectory, self.day, pRetentionDays)

        super().__init__(get_log_file(pDirectory, self.day), encoding="utf-8")

    def emit(self, pRecord):
        """Change de fichier lorsque la journée a changé, puis écrit le message."""
        vToday = date.today()

        if vToday != self.day:
            self.day = vToday
            self.close()
            self.baseFilename = str(get_log_file(self.directory, vToday))
            purge_old_logs(self.directory, vToday, self.retention_days)

        super().emit(pRecord)


def configure_logging():
    """Installe une seule fois les sorties fichier et console, partagées par tous."""

    vRootLogger = logging.getLogger()

    if not any(
        isinstance(vHandler, DailyFileHandler) for vHandler in vRootLogger.handlers
    ):
        vFormatter = logging.Formatter(LOG_FORMAT)

        vFileHandler = DailyFileHandler(LOG_DIRECTORY, get_retention_days())
        vFileHandler.setFormatter(vFormatter)

        vConsoleHandler = logging.StreamHandler()
        vConsoleHandler.setFormatter(vFormatter)

        vRootLogger.addHandler(vFileHandler)
        vRootLogger.addHandler(vConsoleHandler)
        vRootLogger.setLevel(logging.INFO)


def get_logger(pName):
    """Retourne le logger d'un module ; ses messages vont aux sorties communes."""

    configure_logging()

    rLogger = logging.getLogger(pName)

    return rLogger
