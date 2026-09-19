# ============================================================================
# Affichage des données des livres
# ============================================================================


from utils.logger import get_logger


logger = get_logger(__name__)


def display_books(pBooks):
    """
    Affiche les livres dans la console.

    :param pBooks: DataFrame contenant les livres à afficher.
    """

    if pBooks.empty:
        print("Aucun livre trouvé.")

    else:
        logger.info(
            "Affichage de %s livre(s)",
            len(pBooks)
        )

        print()
        print(
            pBooks[
                [
                    "title",
                    "price",
                    "rating",
                    "availability"
                ]
            ].to_string(index=False)
        )
        print()
        print(
            f"{len(pBooks)} livre(s) trouvé(s)."
        )