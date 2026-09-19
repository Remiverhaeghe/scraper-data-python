# ============================================================================
# Tests de la configuration générale de l'application
# ============================================================================


from config import (
    MAX_RATING,
    MIN_RATING,
    OUTPUT_FILE,
    URL
)


def test_url():
    """
    Vérifie que l'URL du site Books to Scrape est configurée.
    """

    assert URL == "https://books.toscrape.com/"


def test_output_file():
    """
    Vérifie que le fichier de sortie est correctement configuré.
    """

    assert OUTPUT_FILE == "output/books.csv"


def test_rating_limits():
    """
    Vérifie les limites des notes.
    """

    assert MIN_RATING == 1
    assert MAX_RATING == 5