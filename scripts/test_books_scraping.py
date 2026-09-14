"""
Test manuel du scraping de Books to Scrape.
"""

from book.service import scrape_books
from book.storage import save_books


URL = "https://books.toscrape.com/"


def main():
    """Récupère et affiche un résumé du scraping."""

    books = scrape_books(URL, max_pages=2)

    save_books(books, "output/book.csv")

    print(f"Nombre de livres trouvés : {len(books)}")

    if not books:
        return

    print("\nPremier livre :")
    print(
        f"{books[0].title} | "
        f"{books[0].price} £ | "
        f"{books[0].availability} | "
        f"{books[0].rating}/5"
    )

    print("\nDernier livre :")
    print(
        f"{books[-1].title} | "
        f"{books[-1].price} £ | "
        f"{books[-1].availability} | "
        f"{books[-1].rating}/5"
    )


if __name__ == "__main__":
    main()