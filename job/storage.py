# ============================================================================
# Gestion du stockage des offres d'emploi
# ============================================================================


from job.csv_schema import JOB_COLUMNS
from data.csv_writer import save_csv
from utils.logger import get_logger


logger = get_logger(__name__)


def save_jobs(pJobs, pFilePath):
    """
    Enregistre les offres d'emploi dans un fichier CSV.

    :param pJobs: DataFrame contenant les offres à enregistrer.
    :param pFilePath: Chemin du fichier CSV de destination.
    """

    logger.info(
        "Enregistrement de %s offre(s) dans : %s",
        len(pJobs),
        pFilePath
    )

    try:
        save_csv(
            pJobs,
            pFilePath,
            JOB_COLUMNS
        )

    except OSError:
        logger.exception(
            "Erreur lors de l'enregistrement : %s",
            pFilePath
        )
        raise

    logger.info(
        "Enregistrement terminé : %s",
        pFilePath
    )