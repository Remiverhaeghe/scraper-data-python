"""Décisions prises sur les offres publiées sur plusieurs sources"""

from storage.database import connect_database
from utils.logger import get_logger

logger = get_logger(__name__)


def get_decisions(pDatabaseFile):
    """Retourne la décision prise pour chaque empreinte d'offre."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rDecisions = dict(
            vConnection.execute("SELECT fingerprint, decision FROM duplicate_decision")
        )

    finally:
        vConnection.close()

    return rDecisions


def save_decision(pDatabaseFile, pFingerprint, pDecision, pNow):
    """Enregistre la fusion ou la séparation des annonces d'une même empreinte."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute(
            """
            INSERT INTO duplicate_decision (fingerprint, decision, decided_at)
            VALUES (?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                decision = excluded.decision,
                decided_at = excluded.decided_at
            """,
            (pFingerprint, pDecision, pNow.isoformat()),
        )
        vConnection.commit()

    finally:
        vConnection.close()

    logger.info("Décision sur une offre multi-sources : %s", pDecision)
