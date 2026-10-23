"""Sauvegarde de la base de données et rotation des sauvegardes"""

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    AUTO_BACKUP_INTERVAL_HOURS,
    AUTO_BACKUP_KEEP_COUNT,
    BACKUP_KEEP_COUNT,
    BACKUP_NAS_DIRECTORY,
    NAS_KEEP_COUNT,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des sauvegardes, à côté de la base
BACKUP_DIRECTORY_NAME = "backups"

# Suffixe des sauvegardes automatiques : elles tournent entre elles, sans évincer
# celles faites avant une opération risquée.
AUTO_BACKUP_REASON = "auto"


def backup_database(pDatabaseFile, pNow, pReason=None):
    """Copie la base dans le dossier des sauvegardes ; retourne le fichier créé.

    pReason complète le nom du fichier, par exemple « avant-v9 ».
    """

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME
    vDirectory.mkdir(parents=True, exist_ok=True)

    vSuffix = f"-{pReason}" if pReason else ""

    rBackupFile = vDirectory / f"{vDatabaseFile.stem}-{pNow:%Y%m%d-%H%M%S}{vSuffix}.db"

    # L'API de sauvegarde de SQLite produit une copie cohérente, même si une autre
    # application écrit dans la base au même moment, ce que ne garantit pas une
    # simple copie de fichier.
    vSource = sqlite3.connect(vDatabaseFile)
    vTarget = sqlite3.connect(rBackupFile)

    try:
        vSource.backup(vTarget)

    finally:
        vTarget.close()
        vSource.close()

    logger.info("Sauvegarde de la base créée : %s", rBackupFile.name)

    vAutomatic = pReason == AUTO_BACKUP_REASON

    purge_backups(
        vDatabaseFile,
        AUTO_BACKUP_KEEP_COUNT if vAutomatic else BACKUP_KEEP_COUNT,
        vAutomatic,
    )

    return rBackupFile


def list_backups(pDatabaseFile, pAutomatic=None):
    """Retourne les sauvegardes, les plus récentes en tête.

    pAutomatic garde seulement les automatiques (True) ou les autres (False).
    """

    vDatabaseFile = Path(pDatabaseFile)
    vDirectory = vDatabaseFile.parent / BACKUP_DIRECTORY_NAME

    # La date est dans le nom : l'ordre alphabétique est l'ordre chronologique.
    rBackups = [
        vBackupFile
        for vBackupFile in sorted(
            vDirectory.glob(f"{vDatabaseFile.stem}-*.db"), reverse=True
        )
        if pAutomatic is None
        or vBackupFile.stem.endswith(f"-{AUTO_BACKUP_REASON}") == pAutomatic
    ]

    return rBackups


def purge_backups(pDatabaseFile, pKeepCount=BACKUP_KEEP_COUNT, pAutomatic=False):
    """Supprime les sauvegardes les plus anciennes ; retourne le nombre supprimé."""

    rDeletedCount = 0

    for vBackupFile in list_backups(pDatabaseFile, pAutomatic)[pKeepCount:]:
        try:
            vBackupFile.unlink()

        except OSError:
            # Un fichier ouvert ailleurs est laissé en place, au prochain passage.
            logger.warning("Sauvegarde non supprimée : %s", vBackupFile.name)

        else:
            rDeletedCount += 1

    if rDeletedCount:
        logger.info("Anciennes sauvegardes supprimées : %s", rDeletedCount)

    return rDeletedCount


def describe_backup(pDatabaseFile, pBackupFile):
    """Retourne la date, le motif et la taille d'une sauvegarde, ou None si son nom diffère."""

    # Nom : <base>-AAAAMMJJ-HHMMSS[-motif].db
    vParts = pBackupFile.stem[len(Path(pDatabaseFile).stem) + 1 :].split("-", 2)

    try:
        vCreatedAt = datetime.strptime(f"{vParts[0]}-{vParts[1]}", "%Y%m%d-%H%M%S")
        vSize = pBackupFile.stat().st_size

    except (IndexError, ValueError, OSError):
        return None

    rBackup = {
        "name": pBackupFile.name,
        "created_at": vCreatedAt,
        "reason": vParts[2] if len(vParts) > 2 else "",
        "size": vSize,
    }

    return rBackup


def describe_backups(pDatabaseFile):
    """Retourne la description de chaque sauvegarde, la plus récente en tête."""

    rBackups = [
        vBackup
        for vBackup in (
            describe_backup(pDatabaseFile, vBackupFile)
            for vBackupFile in list_backups(pDatabaseFile)
        )
        if vBackup is not None
    ]

    rBackups.sort(key=lambda pBackup: pBackup["created_at"], reverse=True)

    return rBackups


def get_last_auto_backup_time(pDatabaseFile):
    """Retourne la date de la dernière sauvegarde automatique, lue dans son nom."""

    rTime = next(
        (
            vBackup["created_at"]
            for vBackup in map(
                lambda pFile: describe_backup(pDatabaseFile, pFile),
                list_backups(pDatabaseFile, pAutomatic=True),
            )
            if vBackup is not None
        ),
        None,
    )

    return rTime


def run_due_backup(pDatabaseFile, pNow):
    """Sauvegarde la base si la dernière sauvegarde automatique est trop ancienne.

    Retourne le fichier créé, ou None. Un échec est journalisé sans interrompre
    l'appelant : l'application et le planificateur continuent.
    """

    rBackupFile = None

    try:
        vLastTime = get_last_auto_backup_time(pDatabaseFile)

        if vLastTime is None or pNow - vLastTime >= timedelta(
            hours=AUTO_BACKUP_INTERVAL_HOURS
        ):
            rBackupFile = backup_database(pDatabaseFile, pNow, AUTO_BACKUP_REASON)

    except (OSError, sqlite3.Error):
        logger.exception("Échec de la sauvegarde automatique de la base")

    copy_to_nas(pDatabaseFile)

    return rBackupFile


def list_nas_copies(pDatabaseFile, pNasDirectory):
    """Retourne les copies présentes sur le NAS, les plus récentes en tête."""

    vStem = Path(pDatabaseFile).stem

    rCopies = sorted(
        Path(pNasDirectory).glob(f"{vStem}-*-{AUTO_BACKUP_REASON}.db"), reverse=True
    )

    return rCopies


def copy_to_nas(pDatabaseFile, pNasDirectory=None, pKeepCount=NAS_KEEP_COUNT):
    """Copie la dernière sauvegarde automatique sur le NAS si elle n'y est pas.

    Un NAS éteint ou injoignable est signalé dans le journal ; la copie est
    retentée au passage suivant, sans rien perdre. Retourne le fichier copié,
    ou None.
    """

    vNasDirectory = pNasDirectory or BACKUP_NAS_DIRECTORY
    vLatest = next(iter(list_backups(pDatabaseFile, pAutomatic=True)), None)
    rCopy = None

    if vNasDirectory is None or vLatest is None:
        return rCopy

    try:
        vTarget = Path(vNasDirectory) / vLatest.name

        if not vTarget.exists():
            Path(vNasDirectory).mkdir(parents=True, exist_ok=True)
            # Copie sous un nom provisoire puis renommage : une coupure réseau ne
            # laisse jamais une copie tronquée sous le nom définitif.
            vPartial = vTarget.with_suffix(".partiel")
            shutil.copy2(vLatest, vPartial)
            vPartial.replace(vTarget)
            rCopy = vTarget

            logger.info("Sauvegarde copiée sur le NAS : %s", vTarget.name)

            for vOld in list_nas_copies(pDatabaseFile, vNasDirectory)[pKeepCount:]:
                vOld.unlink(missing_ok=True)

    except OSError as vException:
        logger.warning(
            "Copie sur le NAS impossible (%s) : nouvel essai au prochain passage",
            vException,
        )

    return rCopy


def get_last_nas_copy_time(pDatabaseFile, pNasDirectory=None):
    """Retourne la date de la dernière copie sur le NAS ; None sans copie.

    Lève OSError si le NAS est injoignable.
    """

    vNasDirectory = pNasDirectory or BACKUP_NAS_DIRECTORY

    if not Path(vNasDirectory).is_dir():
        raise OSError(f"Dossier du NAS injoignable : {vNasDirectory}")

    vCopies = list_nas_copies(pDatabaseFile, vNasDirectory)
    vStemLength = len(Path(pDatabaseFile).stem) + 1

    # Date lue dans le nom, « scraper-20261022-183000-auto » : 15 caractères
    rTime = (
        datetime.strptime(
            vCopies[0].stem[vStemLength : vStemLength + 15], "%Y%m%d-%H%M%S"
        )
        if vCopies
        else None
    )

    return rTime
