"""Jetons d'accès secrets : abonnement à l'agenda, application mobile

Un jeton donne accès sans session à une partie des données : il n'est jamais
journalisé, et un nouveau jeton remplace l'ancien, qui cesse de fonctionner.
"""

import secrets

from storage.settings_repository import get_setting_values, save_setting_values

# 32 octets aléatoires : impossible à deviner, même en essayant en boucle
TOKEN_BYTES = 32


def get_access_token(pDatabaseFile, pKey):
    """Retourne le jeton enregistré sous pKey, ou None s'il n'a pas été créé."""

    rToken = get_setting_values(pDatabaseFile).get(pKey) or None

    return rToken


def renew_access_token(pDatabaseFile, pKey):
    """Crée un nouveau jeton sous pKey ; l'ancien cesse de fonctionner."""

    rToken = secrets.token_urlsafe(TOKEN_BYTES)

    save_setting_values(pDatabaseFile, {pKey: rToken})

    return rToken


def check_access_token(pDatabaseFile, pKey, pToken):
    """Indique si le jeton reçu correspond à celui enregistré sous pKey."""

    vExpected = get_access_token(pDatabaseFile, pKey)

    # Comparaison en temps constant : la durée ne révèle rien du jeton attendu.
    rValid = bool(vExpected and pToken) and secrets.compare_digest(
        vExpected.encode(), str(pToken).encode()
    )

    return rValid
