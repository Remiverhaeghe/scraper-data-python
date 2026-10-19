"""Persistance des réglages modifiables depuis les interfaces"""

import json

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def get_setting_values(pDatabaseFile):
    """Retourne les réglages enregistrés, sous forme de texte, par clé."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rValues = dict(vConnection.execute("SELECT key, value FROM app_setting"))

    finally:
        vConnection.close()

    return rValues


def save_setting_values(pDatabaseFile, pValues):
    """Enregistre plusieurs réglages en une seule transaction."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO app_setting (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            [(vKey, str(vValue)) for vKey, vValue in pValues.items()],
        )

        vConnection.commit()

    finally:
        vConnection.close()


def load_json_setting(pDatabaseFile, pKey, pDefault, pExpectedType=None):
    """Retourne un réglage JSON, ou pDefault s'il est absent, illisible ou mal formé."""

    vValue = get_setting_values(pDatabaseFile).get(pKey)

    rValue = pDefault

    if vValue:
        try:
            vData = json.loads(vValue)

        except ValueError:
            logger.warning("Réglage %s illisible : valeur par défaut utilisée", pKey)

        else:
            if pExpectedType is None or isinstance(vData, pExpectedType):
                rValue = vData
            else:
                logger.warning(
                    "Réglage %s de forme inattendue : valeur par défaut utilisée", pKey
                )

    return rValue


def save_json_setting(pDatabaseFile, pKey, pValue):
    """Enregistre un réglage en JSON ; None l'efface."""

    save_setting_values(
        pDatabaseFile,
        {pKey: "" if pValue is None else json.dumps(pValue, ensure_ascii=False)},
    )
