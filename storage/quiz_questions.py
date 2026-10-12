"""Questions de révision importées, rangées dans la base avec les autres données"""

import json

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def save_imported_questions(pDatabaseFile, pThemeKey, pThemeLabel, pQuestions, pNow):
    """Enregistre des questions déjà vérifiées dans un thème."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            """
            INSERT INTO quiz_question (question_id, theme, theme_label, content, added_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    vQuestion["id"],
                    pThemeKey,
                    pThemeLabel,
                    json.dumps(vQuestion, ensure_ascii=False),
                    pNow.isoformat(),
                )
                for vQuestion in pQuestions
            ],
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info(
        "Révision : %s question(s) importée(s) dans le thème %s",
        len(pQuestions),
        pThemeLabel,
    )


def get_imported_questions(pDatabaseFile):
    """Retourne les questions importées : (clé du thème, libellé, question)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT theme, theme_label, content FROM quiz_question ORDER BY added_at"
        ).fetchall()

    finally:
        vConnection.close()

    rQuestions = [
        (vTheme, vLabel, json.loads(vContent)) for vTheme, vLabel, vContent in vRows
    ]

    return rQuestions
