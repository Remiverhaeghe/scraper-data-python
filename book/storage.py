"""
Gestion du stockage des livres
"""

import csv
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

def save_books(books, file_path):
    """Enregistre une liste de livres dans un fichier CSV."""

    file_path = Path(file_path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    logger.info(
        "Enregistrement de %s livre(s) dans : %s", 
        len(books), 
        file_path
    )

    with file_path.open(
        mode="w", 
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "title",
            "price",
            "availability",
            "rating",
            "url"
        ])

        for book in books:
            writer.writerow([
                book.title,
                book.price,
                book.availability,
                book.rating, 
                book.url
            ])

    logger.info(
        "Enregistrement terminé : %s",
        file_path
    )