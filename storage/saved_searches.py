"""Persistance des recherches enregistrées"""

import json

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_NAME_LENGTH = 80


def get_saved_searches(pDatabaseFile):
    """Retourne les recherches enregistrées, triées par nom."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT name, sources, criteria FROM saved_search"
            " ORDER BY name COLLATE NOCASE"
        ).fetchall()

    finally:
        vConnection.close()

    rSearches = [
        {
            "name": vName,
            "sources": json.loads(vSources),
            "criteria": json.loads(vCriteria),
        }
        for vName, vSources, vCriteria in vRows
    ]

    return rSearches


def save_search(pDatabaseFile, pName, pSources, pCriteria, pNow):
    """Enregistre une recherche ; un nom déjà utilisé remplace l'ancienne."""

    vName = (pName or "").strip()

    if not vName:
        raise ValueError("Donnez un nom à la recherche.")

    if len(vName) > MAX_NAME_LENGTH:
        raise ValueError(f"Nom trop long : {MAX_NAME_LENGTH} caractères au plus.")

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO saved_search (name, sources, criteria, saved_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                sources = excluded.sources,
                criteria = excluded.criteria,
                saved_at = excluded.saved_at
            """,
            (
                vName,
                json.dumps(list(pSources)),
                json.dumps(pCriteria, ensure_ascii=False),
                pNow.isoformat(),
            ),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Recherche enregistrée : %s (%s source(s))", vName, len(pSources))

    rName = vName

    return rName


def delete_saved_search(pDatabaseFile, pName):
    """Supprime une recherche enregistrée."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute("DELETE FROM saved_search WHERE name = ?", (pName,))
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Recherche enregistrée supprimée : %s", pName)
