# ============================================================================
# Tests du modèle Book
# ============================================================================


from book.model import Book


def test_book():
    """
    Vérifie la création d'un livre avec ses différentes propriétés.
    """

    vBook = Book(
        title="A Light in the Arttic",
        price=51.77,
        availability="In stock",
        rating=3,
        url="https://example.com/book"
    )

    assert vBook.title == "A Light in the Arttic"
    assert vBook.price == 51.77
    assert vBook.availability == "In stock"
    assert vBook.rating == 3
    assert vBook.url == "https://example.com/book"