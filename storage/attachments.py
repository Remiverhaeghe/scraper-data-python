"""Pièces jointes des candidatures : fichiers rangés à côté de la base"""

import sqlite3
import uuid
from pathlib import Path

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

# Dossier des fichiers joints, à côté de la base
ATTACHMENT_DIRECTORY_NAME = "attachments"

# Documents et images d'une candidature ; tout autre type est refusé.
ALLOWED_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
)

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_FILE_NAME_LENGTH = 150


def get_attachment_directory(pDatabaseFile):
    """Retourne le dossier des pièces jointes de la base."""

    rDirectory = Path(pDatabaseFile).parent / ATTACHMENT_DIRECTORY_NAME

    return rDirectory


def clean_file_name(pFileName):
    """Garde seulement le nom du fichier, sans chemin, raccourci si besoin."""

    # Un nom envoyé par un navigateur peut contenir un chemin (« ..\\cv.pdf »).
    vName = Path(str(pFileName or "").replace("\\", "/")).name.strip()

    vPath = Path(vName)

    if len(vName) > MAX_FILE_NAME_LENGTH:
        vName = vPath.stem[: MAX_FILE_NAME_LENGTH - len(vPath.suffix)] + vPath.suffix

    rName = vName

    return rName


def add_attachment(pDatabaseFile, pSource, pSourceId, pFileName, pContent, pNow):
    """Range un fichier joint à une offre ; retourne son identifiant.

    Lève ValueError pour un fichier vide, trop gros ou d'un type non accepté.
    """

    vFileName = clean_file_name(pFileName)
    vExtension = Path(vFileName).suffix.lower()

    if not vFileName or vExtension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Type de fichier non accepté : " + ", ".join(ALLOWED_EXTENSIONS) + "."
        )

    if not pContent:
        raise ValueError("Le fichier est vide.")

    if len(pContent) > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Fichier trop volumineux : {MAX_ATTACHMENT_BYTES // (1024 * 1024)} Mo "
            "au maximum."
        )

    vDirectory = get_attachment_directory(pDatabaseFile)
    vDirectory.mkdir(parents=True, exist_ok=True)

    # Nom aléatoire sur le disque : aucun nom fourni ne peut viser un autre fichier.
    vStoredName = uuid.uuid4().hex + vExtension
    vStoredFile = vDirectory / vStoredName

    vStoredFile.write_bytes(pContent)

    vConnection = connect_database(pDatabaseFile)

    try:
        vCursor = vConnection.execute(
            """
            INSERT INTO job_attachment
                (source, source_id, file_name, stored_name, size, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pSource,
                str(pSourceId),
                vFileName,
                vStoredName,
                len(pContent),
                pNow.isoformat(),
            ),
        )

        vConnection.commit()

    except sqlite3.Error:
        # Sans ligne en base, le fichier écrit ne serait jamais retrouvé.
        vStoredFile.unlink(missing_ok=True)
        raise

    finally:
        vConnection.close()

    logger.info(
        "Pièce jointe ajoutée : %s %s, %s octet(s)", pSource, pSourceId, len(pContent)
    )

    rAttachmentId = vCursor.lastrowid

    return rAttachmentId


def get_attachments(pDatabaseFile, pSource, pSourceId):
    """Retourne les pièces jointes d'une offre, la plus récente en tête."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vRows = vConnection.execute(
            """
            SELECT id, file_name, size, added_at
            FROM job_attachment
            WHERE source = ? AND source_id = ?
            ORDER BY added_at DESC, id DESC
            """,
            (pSource, str(pSourceId)),
        ).fetchall()

    finally:
        vConnection.close()

    rAttachments = [dict(vRow) for vRow in vRows]

    return rAttachments


def get_attachment(pDatabaseFile, pAttachmentId):
    """Retourne une pièce jointe et le chemin de son fichier, ou None."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.row_factory = sqlite3.Row

        vRow = vConnection.execute(
            "SELECT * FROM job_attachment WHERE id = ?", (pAttachmentId,)
        ).fetchone()

    finally:
        vConnection.close()

    rAttachment = None

    if vRow is not None:
        rAttachment = dict(vRow)
        rAttachment["path"] = (
            get_attachment_directory(pDatabaseFile) / rAttachment["stored_name"]
        )

    return rAttachment


def delete_attachment(pDatabaseFile, pAttachmentId):
    """Supprime une pièce jointe et son fichier ; retourne False si elle n'existe pas."""

    vAttachment = get_attachment(pDatabaseFile, pAttachmentId)

    if vAttachment is not None:
        vConnection = connect_database(pDatabaseFile)

        try:
            vConnection.execute(
                "DELETE FROM job_attachment WHERE id = ?", (pAttachmentId,)
            )
            vConnection.commit()

        finally:
            vConnection.close()

        vAttachment["path"].unlink(missing_ok=True)

        logger.info("Pièce jointe supprimée : %s", pAttachmentId)

    rDeleted = vAttachment is not None

    return rDeleted
