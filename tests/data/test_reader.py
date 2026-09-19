# ============================================================================
# Tests de la lecture des données des livres
# ============================================================================


from data.reader import (
    books_file_exists,
    read_books
)


def test_read_books(tmp_path):
    """
    Vérifie la lecture d'un fichier CSV de livres.
    """

    vFilePath = tmp_path / "books.csv"

    vFilePath.write_text(
        "title,price,availability,rating,url\n"
        "Livre 1,10.50,In stock,4,https://example.com/book1\n"
        "Livre 2,25.00,In stock,5,https://example.com/book2\n",
        encoding="utf-8"
    )

    vBooks = read_books(
        vFilePath
    )

    assert len(vBooks) == 2
    assert vBooks.iloc[0]["title"] == "Livre 1"
    assert vBooks.iloc[0]["price"] == 10.50
    assert vBooks.iloc[1]["rating"] == 5


def test_books_file_exists(tmp_path):
    """
    Vérifie qu'un fichier existant est correctement détecté.
    """

    vFilePath = tmp_path / "books.csv"

    vFilePath.touch()

    assert books_file_exists(
        vFilePath
    ) is True


def test_books_file_does_not_exist(tmp_path):
    """
    Vérifie qu'un fichier inexistant est correctement détecté.
    """

    vFilePath = tmp_path / "books.csv"

    assert books_file_exists(
        vFilePath
    ) is False


def test_read_empty_books_file(tmp_path):
    """
    Vérifie la lecture d'un fichier CSV vide.
    """

    vFilePath = tmp_path / "books.csv"

    vFilePath.touch()

    vBooks = read_books(
        vFilePath
    )

    assert vBooks.empty
    assert list(vBooks.columns) == [
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]