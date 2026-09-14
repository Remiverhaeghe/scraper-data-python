"""
Affichage des données des livres. 
"""

from utils.logger import get_logger

logger = get_logger(__name__)

def display_books(books):
    """Affiche les livres dans la console."""

    if books.empty:
        print("Aucun livre trouvé.")
        return

    logger.info(
        "Affichage de %s livre(s)", 
        len(books)
    )

    print()
    print(
        books[
            [
            "title",
            "price",
            "rating",
            "availability"
            ]
        ].to_string(index=False)
    )
    print()
    print(f"{len(books)} livre(s) trouvé(s).")