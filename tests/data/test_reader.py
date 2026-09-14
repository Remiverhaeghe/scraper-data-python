from data.reader import read_books

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