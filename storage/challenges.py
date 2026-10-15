"""Défis de programmation : graines des données personnelles et tentatives"""

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def get_challenge_seed(pDatabaseFile, pChallenge, pNewSeed, pNow):
    """Retourne la graine d'un défi, créée avec pNewSeed au premier appel."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            "INSERT OR IGNORE INTO challenge_seed (challenge, seed, created_at) "
            "VALUES (?, ?, ?)",
            (pChallenge, pNewSeed, pNow.isoformat()),
        )
        vConnection.commit()

        rSeed = vConnection.execute(
            "SELECT seed FROM challenge_seed WHERE challenge = ?", (pChallenge,)
        ).fetchone()[0]

    finally:
        vConnection.close()

    return rSeed


def save_challenge_attempt(pDatabaseFile, pChallenge, pPart, pAnswer, pCorrect, pNow):
    """Enregistre une réponse proposée à une partie de défi."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO challenge_attempt (challenge, part, answer, correct, answered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pChallenge, pPart, pAnswer, int(bool(pCorrect)), pNow.isoformat()),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info(
        "Défi %s, partie %s : réponse %s",
        pChallenge,
        pPart,
        "juste" if pCorrect else "fausse",
    )


def get_challenge_attempts(pDatabaseFile):
    """Retourne toutes les tentatives : (défi, partie, réponse, juste, date)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rAttempts = [
            (vChallenge, vPart, vAnswer, bool(vCorrect), vAnsweredAt)
            for vChallenge, vPart, vAnswer, vCorrect, vAnsweredAt in vConnection.execute(
                "SELECT challenge, part, answer, correct, answered_at "
                "FROM challenge_attempt ORDER BY answered_at, id"
            )
        ]

    finally:
        vConnection.close()

    return rAttempts
