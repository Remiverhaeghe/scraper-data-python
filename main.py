"""
Point d'entrée de l'application.
"""

from book.service import scrape_books
from book.storage import save_books
from cli.arguments import parse_arguments
from config import OUTPUT_FILE, URL


def main():
    """Lance le scraping et l'enregistrement des livres."""

    arguments = parse_arguments()

    books = scrape_books(
        URL,
        max_pages=arguments.max_pages
    )

    save_books(books, OUTPUT_FILE)


if __name__ == "__main__":
    main()