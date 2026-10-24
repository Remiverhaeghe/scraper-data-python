"""Sauvegarde complète chiffrée par mot de passe, pour une clé USB

L'archive (base et pièces jointes) est chiffrée avec une clé tirée du mot de
passe : elle se restaure sur un autre PC sans le fichier .env, mais un mot de
passe oublié la rend illisible.
"""

import base64
import io
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from storage.archive import export_archive, restore_archive
from utils.logger import get_logger

logger = get_logger(__name__)

# En-tête du fichier : format, puis sel aléatoire propre à chaque sauvegarde
FILE_MAGIC = b"JBK1"
SALT_SIZE = 16
ENCRYPTED_ARCHIVE_SUFFIX = ".jbk"

MIN_PASSWORD_LENGTH = 10

# Coût de Scrypt : environ 32 Mo de mémoire par essai, ce qui freine le
# cassage du mot de passe sans gêner une sauvegarde.
SCRYPT_COST = 2**15


def derive_key(pPassword, pSalt):
    """Retourne la clé de chiffrement tirée du mot de passe et du sel."""

    vKey = Scrypt(salt=pSalt, length=32, n=SCRYPT_COST, r=8, p=1).derive(
        pPassword.encode("utf-8")
    )

    rKey = base64.urlsafe_b64encode(vKey)

    return rKey


def check_password(pPassword):
    """Lève ValueError si le mot de passe est trop court pour protéger la copie."""

    if len(pPassword or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Mot de passe trop court : {MIN_PASSWORD_LENGTH} caractères au moins."
        )


def export_encrypted_archive(pDatabaseFile, pDirectory, pPassword, pNow):
    """Écrit la sauvegarde complète chiffrée dans le dossier ; retourne le fichier.

    Lève ValueError pour un mot de passe trop court, OSError si le dossier n'est
    pas accessible en écriture.
    """

    check_password(pPassword)

    vBuffer = io.BytesIO()
    vCount = export_archive(pDatabaseFile, vBuffer)
    vSalt = os.urandom(SALT_SIZE)
    vContent = (
        FILE_MAGIC
        + vSalt
        + Fernet(derive_key(pPassword, vSalt)).encrypt(vBuffer.getvalue())
    )

    rFile = (
        Path(pDirectory) / f"jobboard-{pNow:%Y%m%d-%H%M%S}{ENCRYPTED_ARCHIVE_SUFFIX}"
    )

    # Écriture sous un nom provisoire : une clé retirée trop tôt ne laisse jamais
    # une copie tronquée sous le nom définitif.
    vPartial = rFile.with_name(rFile.name + ".partiel")
    vPartial.write_bytes(vContent)
    vPartial.replace(rFile)

    logger.info(
        "Sauvegarde chiffrée écrite : %s, base et %s pièce(s) jointe(s)",
        rFile.name,
        vCount,
    )

    return rFile


def read_encrypted_archive(pFile, pPassword):
    """Déchiffre une sauvegarde ; retourne l'archive .zip en mémoire.

    Lève ValueError si le fichier n'en est pas une ou si le mot de passe est faux.
    """

    vContent = Path(pFile).read_bytes()

    if not vContent.startswith(FILE_MAGIC):
        raise ValueError("Ce fichier n'est pas une sauvegarde chiffrée JobBoard.")

    vSalt = vContent[len(FILE_MAGIC) : len(FILE_MAGIC) + SALT_SIZE]

    try:
        vArchive = Fernet(derive_key(pPassword or "", vSalt)).decrypt(
            vContent[len(FILE_MAGIC) + SALT_SIZE :]
        )

    except InvalidToken as vException:
        raise ValueError("Mot de passe incorrect, ou fichier abîmé.") from vException

    rArchive = io.BytesIO(vArchive)

    return rArchive


def restore_encrypted_archive(pDatabaseFile, pFile, pPassword, pNow):
    """Remplace les données par celles de la sauvegarde chiffrée ; retourne la
    sauvegarde des données actuelles, faite avant tout remplacement.
    """

    rBackupFile = restore_archive(
        pDatabaseFile, read_encrypted_archive(pFile, pPassword), pNow
    )

    logger.info("Sauvegarde chiffrée restaurée : %s", Path(pFile).name)

    return rBackupFile
