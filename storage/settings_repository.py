"""Persistance des réglages modifiables depuis les interfaces"""

from storage.database import connect_database


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
