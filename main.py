# ============================================================================
# Point d'entrée de l'application
# ============================================================================


from book.config import BookScrapingConfig
from book.service import scrape_books
from book.storage import save_books
from cli.arguments import parse_arguments
from config import OUTPUT_FILE, URL
from data.display import display_books
from data.filter import filter_books
from data.reader import books_file_exists, read_books


def main():
    """
    Lance le scraping, le filtrage et l'affichage des livres.
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

    if vArguments.refresh or not books_file_exists(OUTPUT_FILE):
        vBooks = scrape_books(
            URL,
            vConfig
        )

        save_books(
            vBooks,
            OUTPUT_FILE
        )

    vBooks = read_books(OUTPUT_FILE)

    vBooks = filter_books(
        vBooks,
        title=vArguments.title,
        max_price=vArguments.max_price,
        min_rating=vArguments.min_rating
    )

    display_books(vBooks)


if __name__ == "__main__":
    main()