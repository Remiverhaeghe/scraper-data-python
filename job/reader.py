# ============================================================================
# Lecture des offres d'emploi depuis un fichier CSV
# ============================================================================


from data.csv_reader import read_csv
from job.csv_schema import JOB_COLUMNS
from job.model import Job
from utils.logger import get_logger


logger = get_logger(__name__)


def read_jobs(pFilePath):
    """
    Lit les offres d'emploi depuis un fichier CSV.

    :param pFilePath: Chemin du fichier CSV.
    :return: Liste des offres d'emploi.
    """

    logger.info(
        "Lecture des offres depuis : %s",
        pFilePath
    )

    vData = read_csv(
        pFilePath,
        pColumns=JOB_COLUMNS
    )

    vJobs = []

    for _, vRow in vData.iterrows():
        vJob = Job.from_csv_row(
            vRow
        )
        vJobs.append(vJob)

    logger.info(
        "Lecture terminée : %s offre(s)",
        len(vJobs)
    )

    rJobs = vJobs

    return rJobs