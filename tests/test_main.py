import pandas as pd

import main


def test_main(monkeypatch):
    """Vérifie l'enchaînement des différentes étapes de l'application."""

    calls = []

    arguments = type(
        "Arguments",
        (),
        {
            "max_pages": 2,
            "title": "python",
            "max_price": 20,
            "min_rating": 4
        }
    )()

    books_scraped = ["book1", "book2"]

    books_filtered = pd.DataFrame([
        {
            "title": "Python débutant",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    # Simule la lecture des arguments de la ligne de commande.
    def mock_parse_arguments():
        calls.append("parse_arguments")
        return arguments

    # Simule le scraping afin de ne pas effectuer de requête HTTP.
    def mock_scrape_books(url, max_pages):
        calls.append("scrape_books")

        assert max_pages == 2

        return books_scraped

    # Simule l'enregistrement du fichier CSV.
    def mock_save_books(books, file_path):
        calls.append("save_books")

        assert books == books_scraped

    # Simule la lecture du fichier CSV.
    def mock_read_books(file_path):
        calls.append("read_books")

        return books_filtered

    # Simule le filtrage des livres avec les critères de la CLI.
    def mock_filter_books(books, title, max_price, min_rating):
        calls.append("filter_books")

        assert title == "python"
        assert max_price == 20
        assert min_rating == 4

        return books

    # Simule l'affichage des résultats dans la console.
    def mock_display_books(books):
        calls.append("display_books")

        assert books is books_filtered

    # Remplace temporairement les fonctions réelles par les fonctions simulées.
    monkeypatch.setattr(main, "parse_arguments", mock_parse_arguments)
    monkeypatch.setattr(main, "scrape_books", mock_scrape_books)
    monkeypatch.setattr(main, "save_books", mock_save_books)
    monkeypatch.setattr(main, "read_books", mock_read_books)
    monkeypatch.setattr(main, "filter_books", mock_filter_books)
    monkeypatch.setattr(main, "display_books", mock_display_books)

    # Exécute le point d'entrée de l'application.
    main.main()

    # Vérifie que les différentes étapes ont été exécutées dans le bon ordre.
    assert calls == [
        "parse_arguments",
        "scrape_books",
        "save_books",
        "read_books",
        "filter_books",
        "display_books"
    ]
