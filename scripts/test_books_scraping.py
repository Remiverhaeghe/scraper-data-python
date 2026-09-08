"""
Test manuel du scraping de Books to Scrape.
"""

from book.parser import extract_books, parse_html
from scraper.http_client import fetch_page


URL = "https://books.toscrape.com/"


def main():
    """Récupère et analyse une vraie page."""

    html = fetch_page(URL)
    soup = parse_html(html)

    books = extract_books(
        soup,
        URL
    )

    print(f"Nombre de livres trouvés : {len(books)}")

    for book in books:
        print(
            f"{book.title} | "
            f"{book.price} £ | "
            f"{book.availability} | "
            f"{book.rating}/5"
        )


if __name__ == "__main__":
    main()