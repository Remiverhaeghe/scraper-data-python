"""Lecture de vos données personnelles, table par table, pour leur export"""

import sqlite3

from storage.database import connect_database

# Fichier de l'export et requête qui le remplit : seules ces données sont
# exportées, jamais les secrets ni les offres que vous n'avez pas suivies.
PERSONAL_QUERIES = {
    "candidatures": """
        SELECT a.*, o.title, o.company, o.location, o.url
        FROM job_application a
        LEFT JOIN job_offer o ON o.source = a.source AND o.source_id = a.source_id
        ORDER BY a.applied_at, a.source, a.source_id
        """,
    "historique_des_statuts": "SELECT * FROM application_history ORDER BY id",
    "relances": "SELECT * FROM job_follow_up ORDER BY followed_up_at",
    "journal_entretien": "SELECT * FROM interview_note ORDER BY interviewed_at",
    "pieces_jointes": """
        SELECT id, source, source_id, file_name, size, added_at
        FROM job_attachment ORDER BY id
        """,
    "recherches_enregistrees": "SELECT * FROM saved_search ORDER BY saved_at",
    "historique_recherches": "SELECT * FROM history ORDER BY id",
    "reponses_revision": "SELECT * FROM quiz_answer ORDER BY id",
    "defis": "SELECT * FROM challenge_attempt ORDER BY id",
    "niveaux_git": "SELECT * FROM git_level_result ORDER BY level",
    "tests_recrutement": "SELECT * FROM aptitude_session ORDER BY id",
}


def read_personal_data(pDatabaseFile):
    """Retourne vos données par nom de fichier d'export : liste de lignes."""

    vConnection = connect_database(pDatabaseFile)
    vConnection.row_factory = sqlite3.Row

    try:
        rData = {
            vName: [dict(vRow) for vRow in vConnection.execute(vQuery)]
            for vName, vQuery in PERSONAL_QUERIES.items()
        }

    finally:
        vConnection.close()

    return rData


def read_attachment_files(pDatabaseFile):
    """Retourne chaque pièce jointe : identifiant, nom choisi et nom de stockage."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rFiles = vConnection.execute(
            "SELECT id, file_name, stored_name FROM job_attachment ORDER BY id"
        ).fetchall()

    finally:
        vConnection.close()

    return rFiles
