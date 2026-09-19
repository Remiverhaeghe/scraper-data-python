# ============================================================================
# Gestion du stockage des livres
# ============================================================================


import csv
from pathlib import Path

from utils.logger import get_logger


logger = get_logger(__name__)


def save_books(pBooks, pFilePath):
    """
    Enregistre une liste de livres dans un fichier CSV.

    :param pBooks: Liste des livres à enregistrer.
    :param pFilePath: Chemin du fichier CSV de destination.
    """

    vFilePath = Path(pFilePath)

    vFilePath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    logger.info(
        "Enregistrement de %s livre(s) dans : %s",
        len(pBooks),
        vFilePath
    )

    try:
        with vFilePath.open(
            mode="w",
            encoding="utf-8",
            newline=""
        ) as vFile:

            vWriter = csv.writer(vFile)

            vWriter.writerow([
                "title",
                "price",
                "availability",
                "rating",
                "url"
            ])

            for vBook in pBooks:
                vWriter.writerow([
                    vBook.title,
                    vBook.price,
                    vBook.availability,
                    vBook.rating,
                    vBook.url
                ])

    except OSError:
        logger.exception(
            "Erreur lors de l'enregistrement : %s",
            vFilePath
        )
        raise

    logger.info(
        "Enregistrement terminé : %s",
        vFilePath
    )