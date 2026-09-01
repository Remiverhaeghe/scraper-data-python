"""
Tests du modèle Book. 
"""

from book.model import Book

def test_book(): 
    """Vérifie la création d'un livre."""

    book = Book(
        title="A Light in the Arttic",
        price=51.77,
        availability="In stock", 
        rating=3,
        url="https://example.com/book"
    )

    assert book.title == "A Light in the Arttic"
    assert book.price == 51.77
    assert book.availability == "In stock"
    assert book.rating == 3 
    assert book.url == "https://example.com/book"