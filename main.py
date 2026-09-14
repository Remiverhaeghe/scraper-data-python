"""
Point d'entrée de l'application.
"""

from book.service import scrape_books
from book.storage import save_books
from cli.arguments import parse_arguments
from config import OUTPUT_FILE, URL
from data.display import display_books
from data.filter import filter_books
from data.reader import read_books


def main():
    """Lance le scraping, le filtrage et l'affichage des livres."""

    arguments = parse_arguments()

    books = scrape_books(
        URL,
        max_pages=arguments.max_pages
    )

    save_books(books, OUTPUT_FILE)

    books = read_books(OUTPUT_FILE)

    books = filter_books(
        books,
        title=arguments.title,
        max_price=arguments.max_price,
        min_rating=arguments.min_rating
    )

    display_books(books)

if __name__ == "__main__":
    main()