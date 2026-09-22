# ============================================================================
# Gestion du stockage des livres
# ============================================================================


from book.csv_schema import BOOK_COLUMNS
from data.csv_writer import save_csv
from utils.logger import get_logger


logger = get_logger(__name__)


def save_books(pBooks, pFilePath):
    """
    Enregistre les livres dans un fichier CSV.

    :param pBooks: DataFrame contenant les livres.
    :param pFilePath: Chemin du fichier CSV de destination.
    """

    logger.info(
        "Enregistrement de %s livre(s) dans : %s",
        len(pBooks),
        pFilePath
    )

    try:
        save_csv(
            pBooks,
            pFilePath,
            BOOK_COLUMNS
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