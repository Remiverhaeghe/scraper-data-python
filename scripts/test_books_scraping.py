# ============================================================================
# Test manuel du scraping de Books to Scrape
# ============================================================================


from book.config import BookScrapingConfig
from book.service import scrape_books
from book.storage import save_books
from config import OUTPUT_FILE, URL


def main():
    """
    Exécute manuellement un scraping limité à deux pages
    et affiche un résumé du résultat.
    """

    vConfig = BookScrapingConfig(
        max_pages=2
    )

    vConfig.validate()

    vBooks = scrape_books(
        URL,
        vConfig
    )

    save_books(
        vBooks,
        OUTPUT_FILE
    )

    print(
        f"Nombre de livres trouvés : {len(vBooks)}"
    )

    if vBooks:
        print("\nPremier livre :")
        print(
            f"{vBooks[0].title} | "
            f"{vBooks[0].price} £ | "
            f"{vBooks[0].availability} | "
            f"{vBooks[0].rating}/5"
        )

        print("\nDernier livre :")
        print(
            f"{vBooks[-1].title} | "
            f"{vBooks[-1].price} £ | "
            f"{vBooks[-1].availability} | "
            f"{vBooks[-1].rating}/5"
        )


if __name__ == "__main__":
    main()