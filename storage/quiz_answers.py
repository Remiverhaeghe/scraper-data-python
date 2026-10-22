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


def count_answers_by_day(pDatabaseFile):
    """Retourne, par jour, le nombre de réponses et de bonnes réponses."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rDays = {
            vDay: (vCount, vCorrect)
            for vDay, vCount, vCorrect in vConnection.execute("""
                SELECT substr(answered_at, 1, 10), COUNT(*), SUM(correct)
                FROM quiz_answer
                GROUP BY substr(answered_at, 1, 10)
                """)
        }

    finally:
        vConnection.close()

    return rDays


def count_answers_by_question(pDatabaseFile):
    """Retourne, par question, le nombre de réponses et de bonnes réponses."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rQuestions = {
            vQuestionId: (vCount, vCorrect)
            for vQuestionId, vCount, vCorrect in vConnection.execute("""
                SELECT question_id, COUNT(*), SUM(correct)
                FROM quiz_answer
                GROUP BY question_id
                """)
        }

    finally:
        vConnection.close()

    return rQuestions


def get_last_answers(pDatabaseFile):
    """Retourne, par question, si la dernière réponse donnée était juste."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vRows = vConnection.execute(
            "SELECT question_id, correct FROM quiz_answer ORDER BY answered_at, id"
        ).fetchall()

    finally:
        vConnection.close()

    # Lues par heure de réponse : une réponse du téléphone envoyée en retard
    # reprend sa place, et la plus récente remplace les autres.
    rAnswers = {vQuestionId: bool(vCorrect) for vQuestionId, vCorrect in vRows}

    return rAnswers


def get_answer_history(pDatabaseFile):
    """Retourne toutes les réponses, dans l'ordre : (question, juste, date)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rHistory = [
            (vQuestionId, bool(vCorrect), vAnsweredAt)
            for vQuestionId, vCorrect, vAnsweredAt in vConnection.execute(
                "SELECT question_id, correct, answered_at FROM quiz_answer "
                "ORDER BY answered_at, id"
            )
        ]

    finally:
        vConnection.close()

    return rHistory


def save_synced_answers(pDatabaseFile, pAnswers):
    """Enregistre des réponses venues du téléphone ; retourne le nombre ajouté.

    pAnswers contient (identifiant, question, thème, juste, date). Une réponse
    déjà reçue sous le même identifiant est ignorée.
    """

    vConnection = connect_database(pDatabaseFile)

    try:
        vBefore = vConnection.total_changes
        vConnection.executemany(
            """
            INSERT OR IGNORE INTO quiz_answer
                (client_id, question_id, theme, correct, answered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (vClientId, vQuestionId, vTheme, int(bool(vCorrect)), vAnsweredAt)
                for vClientId, vQuestionId, vTheme, vCorrect, vAnsweredAt in pAnswers
            ],
        )
        vConnection.commit()

        rAdded = vConnection.total_changes - vBefore

    finally:
        vConnection.close()

    return rAdded
