"""Sauvegarde complète exportable : base et pièces jointes dans une archive .zip"""

import re
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from storage.attachments import (
    ALLOWED_EXTENSIONS,
    MAX_ATTACHMENT_BYTES,
    get_attachment_directory,
)
from storage.backup import backup_database
from storage.database import MIGRATIONS, connect_database, initialize_database
from storage.maintenance import move_attachments
from utils.logger import get_logger

logger = get_logger(__name__)

ARCHIVE_DATABASE_NAME = "scraper.db"
ARCHIVE_ATTACHMENT_PREFIX = "attachments/"

# Nom donné par add_attachment : seul ce format est extrait d'une archive, aucun
# chemin choisi par l'archive ne peut donc viser un autre fichier.
STORED_NAME_PATTERN = re.compile(
    r"[0-9a-f]{32}("
    + "|".join(re.escape(vExtension) for vExtension in ALLOWED_EXTENSIONS)
    + r")"
)

# Une archive plus lourde est refusée avant extraction (archive piégée).
MAX_DATABASE_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024

# Tables sans lesquelles le fichier n'est pas une base de l'application
REQUIRED_TABLES = ("job_offer", "job_application", "app_setting")


def export_archive(pDatabaseFile, pTarget):
    """Écrit la base et les pièces jointes dans l'archive pTarget ; retourne leur nombre.

    pTarget est un chemin ou un fichier binaire ouvert en écriture.
    """

    vDirectory = get_attachment_directory(pDatabaseFile)

    with tempfile.TemporaryDirectory(prefix="jobboard-export-") as vTemporary:
        vSnapshot = Path(vTemporary) / ARCHIVE_DATABASE_NAME

        # Copie cohérente même si la base est en cours d'écriture
        vSource = sqlite3.connect(pDatabaseFile)
        vCopy = sqlite3.connect(vSnapshot)

        try:
            vSource.backup(vCopy)

        finally:
            vCopy.close()
            vSource.close()

        vConnection = connect_database(pDatabaseFile)

        try:
            vStoredNames = [
                vRow[0]
                for vRow in vConnection.execute(
                    "SELECT stored_name FROM job_attachment ORDER BY id"
                )
            ]

        finally:
            vConnection.close()

        rCount = 0

        with zipfile.ZipFile(pTarget, "w", zipfile.ZIP_DEFLATED) as vArchive:
            vArchive.write(vSnapshot, ARCHIVE_DATABASE_NAME)

            for vStoredName in vStoredNames:
                vFile = vDirectory / vStoredName

                if vFile.is_file():
                    vArchive.write(vFile, ARCHIVE_ATTACHMENT_PREFIX + vStoredName)
                    rCount += 1
                else:
                    logger.warning("Pièce jointe absente du disque : %s", vStoredName)

    logger.info("Sauvegarde complète exportée : base et %s pièce(s) jointe(s)", rCount)

    return rCount


def check_archive(pArchive):
    """Vérifie le contenu d'une archive ; lève ValueError si elle est refusée."""

    vEntries = pArchive.infolist()
    vNames = [vEntry.filename for vEntry in vEntries]

    if vNames.count(ARCHIVE_DATABASE_NAME) != 1:
        raise ValueError("Archive refusée : la base de données est absente.")

    for vEntry in vEntries:
        vName = vEntry.filename
        vStoredName = vName.removeprefix(ARCHIVE_ATTACHMENT_PREFIX)

        if vName == ARCHIVE_DATABASE_NAME:
            vLimit = MAX_DATABASE_BYTES
        elif vName.startswith(ARCHIVE_ATTACHMENT_PREFIX) and (
            STORED_NAME_PATTERN.fullmatch(vStoredName)
        ):
            vLimit = MAX_ATTACHMENT_BYTES
        else:
            raise ValueError(f"Archive refusée : fichier inattendu « {vName} ».")

        if vEntry.file_size > vLimit:
            raise ValueError(f"Archive refusée : « {vName} » est trop volumineux.")

    if sum(vEntry.file_size for vEntry in vEntries) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive refusée : contenu trop volumineux.")


def check_database(pDatabaseFile):
    """Vérifie qu'un fichier est une base saine de l'application ; lève ValueError."""

    try:
        vConnection = sqlite3.connect(
            Path(pDatabaseFile).resolve().as_uri() + "?mode=ro", uri=True
        )

        try:
            vIntegrity = vConnection.execute("PRAGMA integrity_check").fetchone()[0]
            vVersion = vConnection.execute("PRAGMA user_version").fetchone()[0]
            vTables = {
                vRow[0]
                for vRow in vConnection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        finally:
            vConnection.close()

    except sqlite3.DatabaseError as vException:
        raise ValueError("Archive refusée : la base est illisible.") from vException

    if vIntegrity != "ok":
        raise ValueError("Archive refusée : la base est endommagée.")

    # Une base plus récente que l'application perdrait des colonnes inconnues.
    if not 1 <= vVersion <= len(MIGRATIONS):
        raise ValueError(
            f"Archive refusée : version de base {vVersion} non prise en charge."
        )

    if not set(REQUIRED_TABLES) <= vTables:
        raise ValueError("Archive refusée : ce n'est pas une base de l'application.")


def restore_archive(pDatabaseFile, pArchiveFile, pNow):
    """Remplace la base et les pièces jointes par celles de l'archive.

    La base actuelle est sauvegardée et les pièces jointes actuelles rangées avec
    les sauvegardes avant tout remplacement. Retourne le fichier de sauvegarde ;
    lève ValueError si l'archive est refusée, sans rien modifier.
    """

    try:
        vArchive = zipfile.ZipFile(pArchiveFile)

    except (zipfile.BadZipFile, OSError) as vException:
        raise ValueError("Archive refusée : ce n'est pas un fichier .zip.") from (
            vException
        )

    with vArchive, tempfile.TemporaryDirectory(prefix="jobboard-import-") as vTemporary:
        check_archive(vArchive)

        # Tout est extrait et vérifié avant de toucher aux données actuelles : une
        # archive corrompue est refusée sans rien modifier.
        vExtracted = Path(vTemporary)
        vDatabase = vExtracted / ARCHIVE_DATABASE_NAME
        vAttachments = []

        try:
            for vName in vArchive.namelist():
                vStoredName = vName.removeprefix(ARCHIVE_ATTACHMENT_PREFIX)
                (vExtracted / vStoredName).write_bytes(vArchive.read(vName))

                if vName != ARCHIVE_DATABASE_NAME:
                    vAttachments.append(vStoredName)

        except zipfile.BadZipFile as vException:
            raise ValueError("Archive refusée : fichier corrompu.") from vException

        check_database(vDatabase)

        rBackupFile = backup_database(pDatabaseFile, pNow, "avant-restauration")

        # Recopie dans la base existante plutôt que remplacement du fichier : une
        # autre application qui l'a ouverte, le web par exemple, n'est pas gênée.
        vSource = sqlite3.connect(vDatabase)
        vTarget = sqlite3.connect(pDatabaseFile)

        try:
            vSource.backup(vTarget)

        finally:
            vTarget.close()
            vSource.close()

        move_attachments(pDatabaseFile, pNow)

        vDirectory = get_attachment_directory(pDatabaseFile)
        vDirectory.mkdir(parents=True, exist_ok=True)

        # Le dossier temporaire peut être sur un autre disque : copie, pas renommage.
        for vStoredName in vAttachments:
            shutil.move(vExtracted / vStoredName, vDirectory / vStoredName)

    # Une archive d'une version antérieure reçoit les migrations manquantes.
    initialize_database(pDatabaseFile)

    logger.warning(
        "Sauvegarde complète restaurée : base et %s pièce(s) jointe(s) ; "
        "ancienne base : %s",
        len(vAttachments),
        rBackupFile.name,
    )

    return rBackupFile
