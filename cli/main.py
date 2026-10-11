"""Point d'entrée du mode ligne de commande"""

from cli.arguments import parse_arguments
from config import DATABASE_FILE
from job.application import process_jobs
from job.sources.configuration import build_job_config
from storage.database import initialize_database


def process_job_arguments(pArguments):
    """Construit la configuration de scraping des offres d'emploi."""

    rConfig = build_job_config(pArguments)

    return rConfig


def main():
    """Initialise le mode ligne de commande et lance le traitement demandé."""

    vArguments = parse_arguments()

    # Même initialisation que l'interface : les migrations s'appliquent d'abord.
    initialize_database(DATABASE_FILE)

    vConfig = process_job_arguments(vArguments)

    process_jobs(vConfig)


if __name__ == "__main__":
    main()
