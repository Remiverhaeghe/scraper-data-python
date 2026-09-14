from data.reader import books_file_exists, read_books

def test_read_books(tmp_path): 
    """Vérifie la lecture d'un fichier CSV de livres."""

    file_path = tmp_path / "books.csv"

    file_path.write_text(
        "title,price,availability,rating,url\n"
        "Livre 1,10.50,In stock,4,https://example.com/book1\n"
        "Livre 2,25.00,In stock,5,https://example.com/book2\n",
        encoding="utf-8"
    )

    books = read_books(file_path)

    assert len(books) == 2
    assert books.iloc[0]["title"] == "Livre 1"
    assert books.iloc[0]["price"] == 10.50
    assert books.iloc[1]["rating"] == 5


def test_books_file_exists(tmp_path):
    """Vérifie qu'un fichier existant est correctement détecté."""

    file_path = tmp_path / "books.csv"

    file_path.touch()

    assert books_file_exists(file_path) is True


def test_books_file_does_not_exist(tmp_path):
    """Vérifie qu'un fichier inexistant est correctement détecté."""

    file_path = tmp_path / "books.csv"

    assert books_file_exists(file_path) is False


def test_read_empty_books_file(tmp_path):
    """Vérifie la lecture d'un fichier CSV vide."""

    file_path = tmp_path / "books.csv"

    file_path.touch()

    books = read_books(file_path)

    assert books.empty
    assert list(books.columns) == [
        "title",
        "price",
        "availability",
        "rating",
        "url"
    ]