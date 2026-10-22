"""Traductions déjà faites, gardées pour ne pas les recalculer"""

import hashlib

from storage.database import connect_database


def build_text_key(pText):
    """Retourne la clé d'un texte : son empreinte SHA-256, sans garder le texte lui-même."""

    rKey = hashlib.sha256(str(pText).encode("utf-8")).hexdigest()

    return rKey


def get_translation(pDatabaseFile, pText):
    """Retourne la traduction déjà faite de ce texte, ou None."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRow = vConnection.execute(
            "SELECT translation FROM translation_cache WHERE text_key = ?",
            (build_text_key(pText),),
        ).fetchone()

    finally:
        vConnection.close()

    rTranslation = vRow[0] if vRow else None

    return rTranslation


def save_translation(pDatabaseFile, pText, pTranslation, pNow):
    """Garde la traduction d'un texte, pour le bureau comme pour le web."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO translation_cache (text_key, translation, translated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(text_key) DO UPDATE SET
                translation = excluded.translation,
                translated_at = excluded.translated_at
            """,
            (build_text_key(pText), pTranslation, pNow.isoformat(timespec="seconds")),
        )
        vConnection.commit()

    finally:
        vConnection.close()
