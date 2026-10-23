"""Codes à usage unique de la double authentification (TOTP, RFC 6238)

Le même secret est partagé avec une application comme Google Authenticator :
toutes deux calculent un code à 6 chiffres qui change toutes les 30 secondes.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote

CODE_DIGITS = 6
STEP_SECONDS = 30

# Pas de 30 secondes acceptés autour de l'heure : une horloge un peu décalée
# ou un code saisi juste à la fin de sa période passent quand même.
ACCEPTED_DRIFT = 1


def generate_secret():
    """Retourne un nouveau secret aléatoire, en base 32 comme l'attendent les applications."""

    rSecret = base64.b32encode(secrets.token_bytes(20)).decode("ascii")

    return rSecret


def compute_code(pSecret, pStep):
    """Retourne le code à 6 chiffres d'un pas de temps (RFC 4226, troncature dynamique)."""

    vKey = base64.b32decode(pSecret.upper() + "=" * (-len(pSecret) % 8))
    vDigest = hmac.new(vKey, struct.pack(">Q", pStep), hashlib.sha1).digest()
    vOffset = vDigest[-1] & 0x0F
    vNumber = struct.unpack(">I", vDigest[vOffset : vOffset + 4])[0] & 0x7FFFFFFF

    rCode = str(vNumber % 10**CODE_DIGITS).zfill(CODE_DIGITS)

    return rCode


def find_code_step(pSecret, pCode, pTimestamp):
    """Retourne le pas de temps du code saisi s'il est valide, sinon None."""

    vCode = "".join(str(pCode or "").split())
    vStep = int(pTimestamp // STEP_SECONDS)

    rStep = next(
        (
            vCandidate
            for vCandidate in range(vStep - ACCEPTED_DRIFT, vStep + ACCEPTED_DRIFT + 1)
            if hmac.compare_digest(compute_code(pSecret, vCandidate), vCode)
        ),
        None,
    )

    return rStep


def build_provisioning_uri(pSecret, pAccount, pIssuer):
    """Retourne l'adresse otpauth:// à mettre dans le QR code de l'application."""

    rUri = (
        f"otpauth://totp/{quote(pIssuer)}:{quote(pAccount)}"
        f"?secret={pSecret}&issuer={quote(pIssuer)}&digits={CODE_DIGITS}"
        f"&period={STEP_SECONDS}"
    )

    return rUri
