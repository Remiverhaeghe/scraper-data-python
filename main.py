"""
Point d'entrée de l'application.
"""

from book.service import scrape_books
from book.storage import save_books
from config import OUTPUT_FILE, URL


def main():
    """Lance le scraping et l'enregistrement des livres."""

    books = scrape_books(URL)

    save_books(books, OUTPUT_FILE)


if __name__ == "__main__":
    main()