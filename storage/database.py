# ============================================================================
# Gestion de la connexion à la base SQLite
# ============================================================================


import sqlite3
from pathlib import Path


def connect_database(pDatabasePath):
    """
    Ouvre une connexion vers la base SQLite.

    :param pDatabasePath: Chemin vers le fichier SQLite.
    :return: Connexion SQLite ouverte.
    """

    vDatabasePath = Path(pDatabasePath)

    vDatabasePath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    vConnection = sqlite3.connect(
        vDatabasePath
    )

    rConnection = vConnection

    return rConnection