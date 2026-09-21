# ============================================================================
# Orchestration du traitement complet des livres
# ============================================================================


from book.display import display_books
from book.filter import filter_books
from book.reader import books_file_exists, read_books
from book.service import scrape_books
from book.storage import save_books
from config import DATABASE_FILE
from scraper.history_service import record_history
from utils.logger import get_logger


logger = get_logger(__name__)


def process_books(
    pUrl,
    pOutputFile,
    pConfig,
    pRefresh=False
):
    """
    Lance le traitement complet des livres.

    :param pUrl: URL de départ du scraping.
    :param pOutputFile: Fichier CSV de sortie.
    :param pConfig: Configuration du scraping.
    :param pRefresh: Force un nouveau scraping.
    :return: Résultat du scraping ou None si le fichier existant est utilisé.
    """

    logger.info(
        "Début du traitement des livres"
    )

    vResult = None

    if pRefresh or not books_file_exists(
        pOutputFile
    ):
        logger.info(
            "Lancement du scraping des livres"
        )

        vResult = scrape_books(
            pUrl,
            pConfig
        )

        save_books(
            vResult.items,
            pOutputFile
        )

        record_history(
            DATABASE_FILE,
            "book",
            pUrl,
            vResult
        )

    vBooks = read_books(
        pOutputFile
    )

    vBooks = filter_books(
        vBooks,
        title=pConfig.title,
        max_price=pConfig.max_price,
        min_rating=pConfig.min_rating
    )

    display_books(
        vBooks
    )

    logger.info(
        "Traitement des livres terminé : %s livre(s)",
        len(vBooks)
    )

    rResult = vResult

    return rResult