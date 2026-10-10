"""Point d'entrée du mode ligne de commande"""

from book.application import process_books
from book.config import BookScrapingConfig
from cli.arguments import parse_arguments
from config import DATABASE_FILE, OUTPUT_FILE, URL
from job.application import process_jobs
from job.sources.configuration import build_job_config
from storage.database import initialize_database


def process_book_arguments(pArguments):
    """Construit la configuration de scraping des livres."""

    vConfig = BookScrapingConfig(
        max_items=pArguments.max_items,
        delay=pArguments.delay,
        timeout=pArguments.timeout,
        max_pages=pArguments.max_pages,
        title=pArguments.title,
        max_price=pArguments.max_price,
        min_rating=pArguments.min_rating,
    )

    vConfig.validate()

    rConfig = vConfig

    return rConfig


def process_job_arguments(pArguments):
    """Construit la configuration de scraping des offres d'emploi."""

    rConfig = build_job_config(pArguments)

    return rConfig


def main():
    """Initialise le mode ligne de commande et lance le traitement demandé."""

    vArguments = parse_arguments()

    initialize_database(DATABASE_FILE)

    if vArguments.type == "book":

        vConfig = process_book_arguments(vArguments)

        process_books(URL, OUTPUT_FILE, vConfig, pRefresh=vArguments.refresh)

    else:

        vConfig = process_job_arguments(vArguments)

        process_jobs(vConfig)


if __name__ == "__main__":
    main()
