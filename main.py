"""
Point d'entrée de l'application.
"""

import argparse

from book.service import scrape_books
from book.storage import save_books
from config import OUTPUT_FILE, URL


def parse_arguments():
    """Analyse les arguments fournis en ligne de commande."""

    parser = argparse.ArgumentParser(
        description="Scrape les livres depuis Books to Scrape."
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Nombre maximum de pages à scraper."
    )

    return parser.parse_args()


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