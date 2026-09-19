# ============================================================================
# Lecture des données issues du scraping
# ============================================================================


from pathlib import Path

import pandas as pd


def books_file_exists(pFilePath):
    """
    Vérifie si le fichier de données existe.

    :param pFilePath: Chemin du fichier de données.
    :return: True si le fichier existe, sinon False.
    """

    vFilePath = Path(pFilePath)

    rExists = vFilePath.exists()

    return rExists


def read_books(pFilePath):
    """
    Lit un fichier CSV contenant les livres.

    :param pFilePath: Chemin du fichier CSV.
    :return: DataFrame contenant les livres.
    """

    try:
        vBooks = pd.read_csv(
            pFilePath
        )

    except pd.errors.EmptyDataError:
        vBooks = pd.DataFrame(
            columns=[
                "title",
                "price",
                "availability",
                "rating",
                "url"
            ]
        )

    rBooks = vBooks

    return rBooks