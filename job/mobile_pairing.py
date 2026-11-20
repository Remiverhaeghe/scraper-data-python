"""Connexion du téléphone par un code à 6 chiffres

Le PC affiche un code court ; le téléphone, qui a trouvé le serveur sur le Wi-Fi,
l'envoie et reçoit en échange le jeton de l'application mobile. Le code ne sert
qu'une fois, expire au bout de dix minutes et tombe après cinq essais faux : un
million de combinaisons pour cinq tentatives ne laissent aucune chance de le
deviner. Seule son empreinte est enregistrée, jamais le code lui-même.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from job.mobile_sync import get_mobile_token, renew_mobile_token
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

PAIRING_DIGITS = 6
PAIRING_LIFETIME = timedelta(minutes=10)
PAIRING_MAX_ATTEMPTS = 5

PAIRING_HASH_KEY = "mobile_pairing_hash"
PAIRING_EXPIRES_KEY = "mobile_pairing_expires"
PAIRING_ATTEMPTS_KEY = "mobile_pairing_attempts"


def hash_code(pCode, pSalt):
    """Retourne l'empreinte du code, salée par une valeur propre à chaque code."""

    rHash = hashlib.sha256(f"{pSalt}:{pCode}".encode()).hexdigest()

    return rHash


def create_pairing_code(pDatabaseFile, pNow=None):
    """Crée un code de connexion ; le précédent cesse de fonctionner."""

    vNow = pNow or datetime.now()
    rCode = f"{secrets.randbelow(10**PAIRING_DIGITS):0{PAIRING_DIGITS}d}"
    vSalt = secrets.token_hex(8)

    save_setting_values(
        pDatabaseFile,
        {
            PAIRING_HASH_KEY: f"{vSalt}${hash_code(rCode, vSalt)}",
            PAIRING_EXPIRES_KEY: (vNow + PAIRING_LIFETIME).isoformat(),
            PAIRING_ATTEMPTS_KEY: "0",
        },
    )

    # Le code n'est pas journalisé : il donne accès aux révisions pendant dix minutes.
    logger.info("Code de connexion du téléphone créé")

    return rCode


def clear_pairing_code(pDatabaseFile):
    """Efface le code en cours."""

    save_setting_values(
        pDatabaseFile,
        {PAIRING_HASH_KEY: "", PAIRING_EXPIRES_KEY: "", PAIRING_ATTEMPTS_KEY: "0"},
    )


def format_pairing_code(pCode):
    """Écrit le code en deux groupes de trois chiffres, plus faciles à recopier."""

    rText = f"{pCode[:3]} {pCode[3:]}"

    return rText


def redeem_pairing_code(pDatabaseFile, pCode, pNow=None):
    """Échange un code valide contre le jeton mobile ; None si le code est refusé.

    Le jeton existant est rendu tel quel, pour ne pas déconnecter un autre
    téléphone ; il est créé s'il n'existe pas encore.
    """

    vNow = pNow or datetime.now()
    vValues = get_setting_values(pDatabaseFile)
    vStored = vValues.get(PAIRING_HASH_KEY) or ""
    vExpires = vValues.get(PAIRING_EXPIRES_KEY) or ""
    vAttempts = int(vValues.get(PAIRING_ATTEMPTS_KEY) or 0)
    vCode = "".join(vCharacter for vCharacter in str(pCode) if vCharacter.isdigit())

    if not vStored or not vExpires or vNow > datetime.fromisoformat(vExpires):
        logger.warning("Code de connexion du téléphone refusé : aucun code en cours")
        return None

    vSalt, _, vHash = vStored.partition("$")

    if not secrets.compare_digest(hash_code(vCode, vSalt), vHash):
        vAttempts += 1

        if vAttempts >= PAIRING_MAX_ATTEMPTS:
            clear_pairing_code(pDatabaseFile)
            logger.warning(
                "Code de connexion du téléphone effacé après %s essais", vAttempts
            )
        else:
            save_setting_values(pDatabaseFile, {PAIRING_ATTEMPTS_KEY: str(vAttempts)})
            logger.warning("Code de connexion du téléphone faux (essai %s)", vAttempts)

        return None

    clear_pairing_code(pDatabaseFile)
    rToken = get_mobile_token(pDatabaseFile) or renew_mobile_token(pDatabaseFile)
    logger.info("Téléphone connecté par code")

    return rToken
