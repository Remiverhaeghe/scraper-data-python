"""Compétences repérées dans le texte des offres, calculées une fois puis lues

Chercher la centaine de compétences du dictionnaire dans chaque annonce coûtait
six secondes pour mille offres, à chaque affichage. Elles sont maintenant
enregistrées en base : après chaque recherche et au démarrage, seules les offres
sans résultat sont analysées. Une empreinte du dictionnaire relance l'analyse
de toutes les offres quand une compétence est ajoutée ou modifiée.
"""

import hashlib
import json
import time

from job.enrichment import SKILLS, detect_skills
from storage.database import connect_database
from storage.settings_repository import get_setting_values, save_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Empreinte du dictionnaire avec lequel les compétences en base ont été repérées
SKILLS_VERSION_KEY = "detected_skills_version"
SKILLS_VERSION = hashlib.sha256(
    json.dumps(SKILLS, sort_keys=True, ensure_ascii=False).encode("utf-8")
).hexdigest()[:16]

# Offres analysées puis enregistrées ensemble
BATCH_SIZE = 500

TEXT_COLUMNS = ("title", "description", "missions", "requirements")


def clear_detected_skills(pDatabaseFile):
    """Efface les compétences repérées, à recalculer avec le nouveau dictionnaire."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.execute("UPDATE job_offer SET detected_skills = NULL")
        vConnection.commit()

    finally:
        vConnection.close()


def get_offers_to_analyse(pDatabaseFile, pLimit):
    """Retourne la clé et le texte des offres dont les compétences restent à repérer."""

    vConnection = connect_database(pDatabaseFile)

    try:
        rRows = vConnection.execute(
            f"SELECT source, source_id, {', '.join(TEXT_COLUMNS)} "  # nosec B608
            "FROM job_offer WHERE detected_skills IS NULL LIMIT ?",
            (pLimit,),
        ).fetchall()

    finally:
        vConnection.close()

    return rRows


def save_detected_skills(pDatabaseFile, pRows):
    """Enregistre les compétences repérées, données par (json, source, id)."""

    vConnection = connect_database(pDatabaseFile)

    try:
        vConnection.executemany(
            "UPDATE job_offer SET detected_skills = ? "
            "WHERE source = ? AND source_id = ?",
            pRows,
        )
        vConnection.commit()

    finally:
        vConnection.close()


def refresh_detected_skills(pDatabaseFile, _pNow=None):
    """Repère les compétences des offres qui n'en ont pas encore ; retourne leur nombre.

    La date n'est pas utilisée : la signature est celle des tâches du planificateur.
    """

    vStart = time.perf_counter()

    if get_setting_values(pDatabaseFile).get(SKILLS_VERSION_KEY) != SKILLS_VERSION:
        clear_detected_skills(pDatabaseFile)
        save_setting_values(pDatabaseFile, {SKILLS_VERSION_KEY: SKILLS_VERSION})
        logger.info(
            "Dictionnaire de compétences modifié : analyse de toutes les offres"
        )

    rCount = 0

    while vRows := get_offers_to_analyse(pDatabaseFile, BATCH_SIZE):
        save_detected_skills(
            pDatabaseFile,
            [
                (
                    json.dumps(
                        detect_skills(" ".join(str(vText or "") for vText in vTexts)),
                        ensure_ascii=False,
                    ),
                    vSource,
                    vSourceId,
                )
                for vSource, vSourceId, *vTexts in vRows
            ],
        )
        rCount += len(vRows)

    if rCount:
        logger.info(
            "Compétences repérées dans %s offre(s) en %.1f s",
            rCount,
            time.perf_counter() - vStart,
        )

    return rCount


def refresh_detected_skills_safely(pDatabaseFile):
    """Lance l'analyse en arrière-plan ; une erreur est journalisée sans bloquer.

    L'affichage reste juste en attendant : sans résultat en base, les
    compétences d'une offre sont cherchées à la volée.
    """

    try:
        refresh_detected_skills(pDatabaseFile)

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Échec de l'analyse des compétences des offres")
