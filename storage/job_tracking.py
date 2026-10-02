# ============================================================================
# Suivi de la première et dernière récupération des offres
# ============================================================================


from datetime import datetime

import pandas as pd

from storage.database import connect_database


def track_jobs(pDatabaseFile, pItems, pScrapedAt):
    """
    Met à jour le suivi des offres récupérées.

    Une nouvelle offre reçoit une date de première découverte.
    Une offre déjà connue conserve cette date et met à jour
    uniquement sa date de dernière récupération.

    Les offres sans source_id ne peuvent pas être suivies
    entre deux exécutions.

    :param pDatabaseFile: Chemin de la base SQLite.
    :param pItems: DataFrame contenant les offres.
    :param pScrapedAt: Date et heure de récupération.
    :return: DataFrame enrichi avec scraped_at et first_seen_at.
    """

    vConnection = connect_database(
        pDatabaseFile
    )

    try:
        vItems = pItems.copy()

        vItems["scraped_at"] = pScrapedAt
        vItems["first_seen_at"] = None

        for vIndex, vJob in vItems.iterrows():

            vSource = vJob["source"]
            vSourceId = vJob["source_id"]

            if pd.isna(vSourceId):
                continue

            vSourceId = str(vSourceId)

            vCursor = vConnection.execute(
                """
                SELECT first_seen_at
                FROM job_tracking
                WHERE source = ?
                AND source_id = ?
                """,
                (
                    vSource,
                    vSourceId
                )
            )

            vRow = vCursor.fetchone()

            if vRow is None:

                vFirstSeenAt = pScrapedAt.isoformat()

                vConnection.execute(
                    """
                    INSERT INTO job_tracking (
                        source,
                        source_id,
                        first_seen_at,
                        last_seen_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        vSource,
                        vSourceId,
                        vFirstSeenAt,
                        pScrapedAt.isoformat()
                    )
                )

            else:

                vFirstSeenAt = vRow[0]

                vConnection.execute(
                    """
                    UPDATE job_tracking
                    SET last_seen_at = ?
                    WHERE source = ?
                    AND source_id = ?
                    """,
                    (
                        pScrapedAt.isoformat(),
                        vSource,
                        vSourceId
                    )
                )

            vItems.loc[
                vIndex,
                "first_seen_at"
            ] = datetime.fromisoformat(
                vFirstSeenAt
            )

        vConnection.commit()

    finally:
        vConnection.close()

    rItems = vItems

    return rItems