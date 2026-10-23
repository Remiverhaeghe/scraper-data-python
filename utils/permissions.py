"""Moindres privilèges : compte d'exécution et droits du .env et de data/

Sur le NAS (Linux), l'application ne doit pas tourner en administrateur, et ses
secrets comme ses données ne doivent pas être lisibles par les autres comptes.
Sous Windows, les droits passent par les ACL : rien n'est vérifié.
"""

import os
import stat
from pathlib import Path

from config import DATABASE_FILE
from utils.logger import get_logger

logger = get_logger(__name__)

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def get_mode(pPath):
    """Retourne les droits d'un fichier ou d'un dossier, ou None s'il n'existe pas."""

    try:
        rMode = stat.S_IMODE(Path(pPath).stat().st_mode)

    except OSError:
        rMode = None

    return rMode


def is_posix():
    """Indique si les droits sont ceux de Linux ou de macOS, vérifiables ici."""

    rPosix = os.name == "posix"

    return rPosix


def get_user_id():
    """Retourne l'identifiant du compte qui exécute l'application (0 : root)."""

    rUserId = os.geteuid() if hasattr(os, "geteuid") else None

    return rUserId


def find_permission_problems(pEnvFile=ENV_FILE, pDataDirectory=None):
    """Retourne les écarts aux moindres privilèges, en clair ; None sous Windows."""

    if not is_posix():
        return None

    vDataDirectory = pDataDirectory or Path(DATABASE_FILE).parent
    rProblems = []

    if get_user_id() == 0:
        rProblems.append("lancée en administrateur (root) : utiliser un compte dédié")

    vEnvMode = get_mode(pEnvFile)

    if vEnvMode is not None and vEnvMode & 0o077:
        rProblems.append(".env lisible par d'autres comptes : chmod 600 .env")

    vDataMode = get_mode(vDataDirectory)

    if vDataMode is not None and vDataMode & 0o007:
        rProblems.append("data/ ouvert à tous les comptes : chmod 750 data")

    return rProblems


def warn_permission_problems():
    """Signale au démarrage chaque écart aux moindres privilèges."""

    for vProblem in find_permission_problems() or []:
        logger.warning("Droits d'exécution : %s", vProblem)
