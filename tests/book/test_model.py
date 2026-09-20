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


def test_book_from_csv_row():
    """
    Vérifie la création d'un livre depuis une ligne CSV.
    """

    vRow = {
        "title": "A Light in the Arttic",
        "price": "51.77",
        "availability": "In stock",
        "rating": "3",
        "url": "https://example.com/book"
    }

    rBook = Book.from_csv_row(
        vRow
    )

    assert isinstance(rBook, Book)
    assert rBook.title == "A Light in the Arttic"
    assert rBook.price == 51.77
    assert rBook.availability == "In stock"
    assert rBook.rating == 3
    assert rBook.url == "https://example.com/book"


def test_book_to_csv_row():
    """
    Vérifie la conversion d'un livre vers une ligne CSV.
    """

    vBook = Book(
        title="A Light in the Arttic",
        price=51.77,
        availability="In stock",
        rating=3,
        url="https://example.com/book"
    )

    rRow = vBook.to_csv_row()

    assert rRow == [
        "A Light in the Arttic",
        51.77,
        "In stock",
        3,
        "https://example.com/book"
    ]