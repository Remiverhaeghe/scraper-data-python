# ============================================================================
# Lecture des données spécifiques aux livres
# ============================================================================

from data.csv_reader import file_exists, read_csv
from book.csv_schema import BOOK_COLUMNS

def books_file_exists(pFilePath):
    """
    Vérifie si le fichier contenant les livres existe.
    """

    rExists = file_exists(pFilePath)

    return rExists


def read_books(pFilePath):
    """
    Lit un fichier CSV contenant les livres.
    """

    rBooks = read_csv(
        pFilePath,
        pColumns=BOOK_COLUMNS
    )

    return rBooks