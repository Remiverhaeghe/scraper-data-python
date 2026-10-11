"""Réponses aux questions de révision, pour suivre la progression"""

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def save_quiz_answer(pDatabaseFile, pQuestionId, pTheme, pCorrect, pNow):
    """Enregistre une réponse à une question de révision."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO quiz_answer (question_id, theme, correct, answered_at)
            VALUES (?, ?, ?, ?)
            """,
            (pQuestionId, pTheme, int(bool(pCorrect)), pNow.isoformat()),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info(
        "Réponse de révision : %s, %s", pQuestionId, "juste" if pCorrect else "fausse"
    )


def get_last_answers(pDatabaseFile):
    """Retourne, par question, si la dernière réponse donnée était juste."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT question_id, correct FROM quiz_answer ORDER BY id"
        ).fetchall()

    finally:
        vConnection.close()

    # Les réponses sont lues dans l'ordre : la plus récente remplace les autres.
    rAnswers = {vQuestionId: bool(vCorrect) for vQuestionId, vCorrect in vRows}

    return rAnswers
