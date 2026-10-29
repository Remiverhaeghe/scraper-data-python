"""Authentification du tableau de bord : mot de passe, session signée et tentatives"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from collections import defaultdict, deque
from datetime import timedelta

from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger
from utils.totp import find_code_step

logger = get_logger(__name__)

# Variables du fichier .env requises pour ouvrir le tableau de bord
AUTH_SETTINGS = ("WEB_USERNAME", "WEB_PASSWORD_HASH", "WEB_SESSION_SECRET")

# Nom de l'algorithme d'empreinte, et non un mot de passe.
PASSWORD_ALGORITHM = "pbkdf2_sha256"  # nosec B105

# Valeur recommandée par l'OWASP pour PBKDF2-SHA256
PASSWORD_ITERATIONS = 600_000

SESSION_COOKIE = "jobboard_session"
SESSION_DURATION = timedelta(hours=12)
# « Rester connecté » sur un appareil de confiance ; « Déconnecter tous les
# appareils » refuse ensuite toute session ouverte avant ce moment.
REMEMBERED_SESSION_DURATION = timedelta(days=30)
SESSIONS_REVOKED_KEY = "web_sessions_revoked_at"

MAX_LOGIN_FAILURES = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)


def get_missing_auth_settings():
    """Retourne les variables d'authentification non renseignées."""

    rMissing = [vName for vName in AUTH_SETTINGS if not os.getenv(vName)]

    return rMissing


def hash_password(pPassword, pIterations=PASSWORD_ITERATIONS):
    """Calcule l'empreinte salée d'un mot de passe : algorithme:tours:sel:hash."""

    vSalt = secrets.token_hex(16)
    vHash = hashlib.pbkdf2_hmac(
        "sha256", pPassword.encode("utf-8"), bytes.fromhex(vSalt), pIterations
    )

    rHash = f"{PASSWORD_ALGORITHM}:{pIterations}:{vSalt}:{vHash.hex()}"

    return rHash


def verify_password(pPassword, pStoredHash):
    """Indique si le mot de passe correspond à l'empreinte enregistrée."""

    rValid = False

    try:
        vAlgorithm, vIterations, vSalt, vHash = pStoredHash.split(":")

        if vAlgorithm == PASSWORD_ALGORITHM:
            vCandidate = hashlib.pbkdf2_hmac(
                "sha256",
                pPassword.encode("utf-8"),
                bytes.fromhex(vSalt),
                int(vIterations),
            )

            # Comparaison à durée constante : le temps de réponse ne révèle rien.
            rValid = hmac.compare_digest(vCandidate.hex(), vHash)

    except (AttributeError, ValueError):
        logger.error("Empreinte WEB_PASSWORD_HASH illisible : régénérez-la")

    return rValid


class SecondFactor:
    """Vérifie le code à 6 chiffres quand WEB_TOTP_SECRET est renseigné.

    Un code accepté ne l'est qu'une fois : intercepté, il ne resservirait pas.
    """

    def __init__(self):
        """Commence sans code déjà utilisé."""
        self.last_step = None

    @staticmethod
    def is_enabled():
        """Indique si la double authentification est demandée."""
        rEnabled = bool(os.getenv("WEB_TOTP_SECRET"))

        return rEnabled

    def check(self, pCode, pTimestamp):
        """Vérifie le code saisi ; toujours vrai sans double authentification."""
        if not self.is_enabled():
            return True

        vStep = find_code_step(os.getenv("WEB_TOTP_SECRET"), pCode, pTimestamp)

        rValid = vStep is not None and (
            self.last_step is None or vStep > self.last_step
        )

        if rValid:
            self.last_step = vStep

        return rValid


second_factor = SecondFactor()


def check_credentials(pUsername, pPassword):
    """Vérifie l'identifiant et le mot de passe saisis contre la configuration."""

    vExpectedUsername = os.getenv("WEB_USERNAME", "")

    # Le mot de passe est toujours vérifié, pour une durée identique quel que soit
    # l'identifiant saisi.
    vPasswordValid = verify_password(pPassword, os.getenv("WEB_PASSWORD_HASH", ""))

    rValid = (
        hmac.compare_digest(
            pUsername.encode("utf-8"), vExpectedUsername.encode("utf-8")
        )
        and vPasswordValid
    )

    return rValid


def encode_part(pData):
    """Encode des octets en base64 compatible avec un cookie."""

    rText = base64.urlsafe_b64encode(pData).decode("ascii").rstrip("=")

    return rText


def decode_part(pText):
    """Décode une partie de jeton encodée par encode_part."""

    rData = base64.urlsafe_b64decode(pText + "=" * (-len(pText) % 4))

    return rData


def sign(pPayload, pSecret):
    """Signe le contenu d'un jeton avec le secret de session."""

    rSignature = encode_part(
        hmac.new(pSecret.encode("utf-8"), pPayload.encode("ascii"), "sha256").digest()
    )

    return rSignature


def get_session_duration(pRemember):
    """Retourne la durée d'une session : 30 jours si l'appareil est mémorisé."""

    rDuration = REMEMBERED_SESSION_DURATION if pRemember else SESSION_DURATION

    return rDuration


def create_session_token(pSecret, pUsername, pNow, pRemember=False):
    """Crée le jeton de session signé, avec son expiration et son jeton CSRF."""

    vPayload = encode_part(
        json.dumps(
            {
                "user": pUsername,
                "issued": pNow.timestamp(),
                "expires": (pNow + get_session_duration(pRemember)).timestamp(),
                "csrf": secrets.token_urlsafe(32),
            }
        ).encode("utf-8")
    )

    rToken = f"{vPayload}.{sign(vPayload, pSecret)}"

    return rToken


def read_session_token(pSecret, pToken, pNow, pRevokedAt=None):
    """Retourne la session d'un jeton valide, non expiré ni révoqué, sinon None.

    pRevokedAt écarte les sessions ouvertes avant cet instant (horodatage).
    """

    rSession = None

    try:
        vPayload, vSignature = pToken.split(".")

        if hmac.compare_digest(vSignature, sign(vPayload, pSecret)):
            vSession = json.loads(decode_part(vPayload))

            if vSession["expires"] > pNow.timestamp() and (
                pRevokedAt is None or vSession.get("issued", 0) > pRevokedAt
            ):
                rSession = vSession

    except (AttributeError, ValueError, KeyError, TypeError):
        rSession = None

    return rSession


def get_sessions_revoked_at(pDatabaseFile):
    """Retourne l'instant de la dernière déconnexion de tous les appareils, ou None."""

    vValue = get_setting_values(pDatabaseFile).get(SESSIONS_REVOKED_KEY)

    rRevokedAt = float(vValue) if vValue else None

    return rRevokedAt


def revoke_sessions(pDatabaseFile, pNow):
    """Déconnecte tous les appareils : les sessions ouvertes avant pNow sont refusées."""

    save_setting_values(pDatabaseFile, {SESSIONS_REVOKED_KEY: str(pNow.timestamp())})

    logger.info("Sessions du tableau de bord révoquées sur tous les appareils")


def is_safe_redirect(pTarget):
    """Indique si une adresse de retour reste sur le site, sans redirection ouverte."""

    rSafe = (
        bool(pTarget)
        and pTarget.startswith("/")
        and not pTarget.startswith("//")
        and "\\" not in pTarget
    )

    return rSafe


class LoginRateLimiter:
    """Bloque une adresse après trop d'échecs de connexion récents."""

    def __init__(self, pMaxFailures=MAX_LOGIN_FAILURES, pWindow=LOGIN_FAILURE_WINDOW):
        """Crée un compteur vide ; les échecs sont gardés en mémoire."""
        self.max_failures = pMaxFailures
        self.window = pWindow
        self.failures = defaultdict(deque)

    def forget_old_failures(self, pAddress, pNow):
        """Oublie les échecs sortis de la fenêtre d'observation."""
        vFailures = self.failures[pAddress]

        while vFailures and vFailures[0] <= pNow - self.window:
            vFailures.popleft()

    def is_blocked(self, pAddress, pNow):
        """Indique si l'adresse a atteint le nombre d'échecs autorisés."""
        self.forget_old_failures(pAddress, pNow)

        rBlocked = len(self.failures[pAddress]) >= self.max_failures

        return rBlocked

    def record_failure(self, pAddress, pNow):
        """Ajoute un échec de connexion pour l'adresse."""
        self.failures[pAddress].append(pNow)

    def reset(self, pAddress):
        """Efface les échecs de l'adresse après une connexion réussie."""
        self.failures.pop(pAddress, None)
