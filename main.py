# ============================================================================
# Point d'entrée de l'application
# ============================================================================


from book.application import process_books
from book.config import BookScrapingConfig
from cli.arguments import parse_arguments
from config import OUTPUT_FILE, URL


def main():
    """
    Lance l'application de scraping des livres.
    """

    vArguments = parse_arguments()

    vConfig = BookScrapingConfig(
        max_items=vArguments.max_items,
        delay=vArguments.delay,
        timeout=vArguments.timeout,
        max_pages=vArguments.max_pages,
        title=vArguments.title,
        max_price=vArguments.max_price,
        min_rating=vArguments.min_rating
    )

    vConfig.validate()

    process_books(
        URL,
        OUTPUT_FILE,
        vConfig,
        pRefresh=vArguments.refresh
    )


if __name__ == "__main__":
    main()