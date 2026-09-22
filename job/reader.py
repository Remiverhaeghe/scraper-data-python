# ============================================================================
# Lecture des offres d'emploi depuis un fichier CSV
# ============================================================================


from data.csv_reader import read_csv
from job.csv_schema import JOB_COLUMNS
from utils.logger import get_logger


logger = get_logger(__name__)


def read_jobs(pFilePath):
    """
    Lit les offres d'emploi depuis un fichier CSV.

    :param pFilePath: Chemin du fichier CSV.
    :return: DataFrame contenant les offres d'emploi.
    """

    logger.info(
        "Lecture des offres depuis : %s",
        pFilePath
    )

    vJobs = read_csv(
        pFilePath,
        pColumns=JOB_COLUMNS
    )

    logger.info(
        "Lecture terminée : %s offre(s)",
        len(vJobs)
    )

    rJobs = vJobs

    return rJobs