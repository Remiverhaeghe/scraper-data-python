# ============================================================================
# Tests du point d'entrée de l'application
# ============================================================================


import pandas as pd

import main


def test_main(monkeypatch):
    """
    Vérifie l'enchaînement des différentes étapes de l'application.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "title": "python",
            "max_price": 20,
            "min_rating": 4,
            "refresh": True
        }
    )()

    vBooksScraped = [
        "book1",
        "book2"
    ]

    vBooksFiltered = pd.DataFrame([
        {
            "title": "Python débutant",
            "price": 15.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    def mock_parse_arguments():
        """Simule la lecture des arguments de la ligne de commande."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_scrape_books(pUrl, pConfig):
        """Simule le scraping sans effectuer de requête HTTP."""

        vCalls.append("scrape_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2

        return vBooksScraped

    def mock_save_books(pBooks, pFilePath):
        """Simule l'enregistrement du fichier CSV."""

        vCalls.append("save_books")

        assert pBooks == vBooksScraped

    def mock_read_books(pFilePath):
        """Simule la lecture du fichier CSV."""

        vCalls.append("read_books")

        return vBooksFiltered

    def mock_filter_books(
        pBooks,
        title,
        max_price,
        min_rating
    ):
        """Simule le filtrage des livres."""

        vCalls.append("filter_books")

        assert title == "python"
        assert max_price == 20
        assert min_rating == 4

        return pBooks

    def mock_display_books(pBooks):
        """Simule l'affichage des résultats."""

        vCalls.append("display_books")

        assert pBooks is vBooksFiltered

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )
    monkeypatch.setattr(
        main,
        "scrape_books",
        mock_scrape_books
    )
    monkeypatch.setattr(
        main,
        "save_books",
        mock_save_books
    )
    monkeypatch.setattr(
        main,
        "read_books",
        mock_read_books
    )
    monkeypatch.setattr(
        main,
        "filter_books",
        mock_filter_books
    )
    monkeypatch.setattr(
        main,
        "display_books",
        mock_display_books
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "scrape_books",
        "save_books",
        "read_books",
        "filter_books",
        "display_books"
    ]


def test_main_without_refresh(monkeypatch):
    """
    Vérifie que le scraping n'est pas lancé sans --refresh
    lorsque le fichier existe.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": None,
            "delay": 0.0,
            "timeout": 10,
            "max_pages": None,
            "refresh": False,
            "title": None,
            "max_price": None,
            "min_rating": None
        }
    )()

    vBooks = pd.DataFrame([
        {
            "title": "Livre existant",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_books_file_exists(pFilePath):
        """Simule l'existence du fichier de données."""

        vCalls.append("books_file_exists")

        return True

    def mock_scrape_books(pUrl, pConfig):
        """Vérifie que le scraping n'est pas lancé."""

        vCalls.append("scrape_books")

        raise AssertionError(
            "Le scraping ne doit pas être lancé sans --refresh."
        )

    def mock_read_books(pFilePath):
        """Simule la lecture du fichier de données."""

        vCalls.append("read_books")

        return vBooks

    def mock_filter_books(
        pBooks,
        title,
        max_price,
        min_rating
    ):
        """Simule le filtrage des livres."""

        vCalls.append("filter_books")

        return pBooks

    def mock_display_books(pBooks):
        """Simule l'affichage des résultats."""

        vCalls.append("display_books")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )
    monkeypatch.setattr(
        main,
        "books_file_exists",
        mock_books_file_exists
    )
    monkeypatch.setattr(
        main,
        "scrape_books",
        mock_scrape_books
    )
    monkeypatch.setattr(
        main,
        "read_books",
        mock_read_books
    )
    monkeypatch.setattr(
        main,
        "filter_books",
        mock_filter_books
    )
    monkeypatch.setattr(
        main,
        "display_books",
        mock_display_books
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "books_file_exists",
        "read_books",
        "filter_books",
        "display_books"
    ]


def test_main_without_refresh_and_without_file(monkeypatch):
    """
    Vérifie que le scraping démarre si le CSV est absent.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "refresh": False,
            "title": None,
            "max_price": None,
            "min_rating": None
        }
    )()

    vBooksScraped = [
        "book1",
        "book2"
    ]

    vBooksFiltered = pd.DataFrame([
        {
            "title": "Livre récupéré",
            "price": 10.0,
            "availability": "In stock",
            "rating": 5,
            "url": "https://example.com/book"
        }
    ])

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_books_file_exists(pFilePath):
        """Simule l'absence du fichier de données."""

        vCalls.append("books_file_exists")

        return False

    def mock_scrape_books(pUrl, pConfig):
        """Simule le scraping."""

        vCalls.append("scrape_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2

        return vBooksScraped

    def mock_save_books(pBooks, pFilePath):
        """Simule l'enregistrement du fichier CSV."""

        vCalls.append("save_books")

        assert pBooks == vBooksScraped

    def mock_read_books(pFilePath):
        """Simule la lecture du fichier CSV."""

        vCalls.append("read_books")

        return vBooksFiltered

    def mock_filter_books(
        pBooks,
        title,
        max_price,
        min_rating
    ):
        """Simule le filtrage des livres."""

        vCalls.append("filter_books")

        return pBooks

    def mock_display_books(pBooks):
        """Simule l'affichage des résultats."""

        vCalls.append("display_books")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )
    monkeypatch.setattr(
        main,
        "books_file_exists",
        mock_books_file_exists
    )
    monkeypatch.setattr(
        main,
        "scrape_books",
        mock_scrape_books
    )
    monkeypatch.setattr(
        main,
        "save_books",
        mock_save_books
    )
    monkeypatch.setattr(
        main,
        "read_books",
        mock_read_books
    )
    monkeypatch.setattr(
        main,
        "filter_books",
        mock_filter_books
    )
    monkeypatch.setattr(
        main,
        "display_books",
        mock_display_books
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "books_file_exists",
        "scrape_books",
        "save_books",
        "read_books",
        "filter_books",
        "display_books"
    ]