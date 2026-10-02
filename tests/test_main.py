# ============================================================================
# Tests du point d'entrée de l'application
# ============================================================================


import main


def test_main_processes_books(monkeypatch):
    """
    Vérifie que main lance le traitement des livres par défaut.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
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

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(
        pUrl,
        pOutputFile,
        pConfig,
        pRefresh
    ):
        """Simule le traitement complet des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2
        assert pConfig.title == "python"
        assert pConfig.max_price == 20
        assert pConfig.min_rating == 4
        assert pRefresh is True

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )

    monkeypatch.setattr(
        main,
        "process_books",
        mock_process_books
    )

    monkeypatch.setattr(
        main,
        "initialize_database",
        mock_initialize_database
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "initialize_database",
        "process_books"
    ]


def test_main_processes_jobs(monkeypatch):
    """
    Vérifie que main lance le traitement des offres d'emploi.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "job",
            "max_items": 100,
            "delay": 1.0,
            "timeout": 30,
            "max_pages": 2,
            "title": None,
            "max_price": None,
            "min_rating": None,
            "refresh": False
        }
    )()

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_jobs(pConfig):
        """Simule le traitement complet des offres."""

        vCalls.append("process_jobs")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )

    monkeypatch.setattr(
        main,
        "process_jobs",
        mock_process_jobs
    )

    monkeypatch.setattr(
        main,
        "initialize_database",
        mock_initialize_database
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "initialize_database",
        "process_jobs"
    ]


def test_main_without_refresh(monkeypatch):
    """
    Vérifie que l'option refresh est correctement transmise
    au traitement des livres.
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
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

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(
        pUrl,
        pOutputFile,
        pConfig,
        pRefresh
    ):
        """Simule le traitement des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items is None
        assert pConfig.delay == 0.0
        assert pConfig.timeout == 10
        assert pConfig.max_pages is None
        assert pRefresh is False

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )

    monkeypatch.setattr(
        main,
        "process_books",
        mock_process_books
    )

    monkeypatch.setattr(
        main,
        "initialize_database",
        mock_initialize_database
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "initialize_database",
        "process_books"
    ]


def test_main_without_file(monkeypatch):
    """
    Vérifie que main délègue la gestion du fichier
    et du scraping à process_books().
    """

    vCalls = []

    vArguments = type(
        "Arguments",
        (),
        {
            "type": "book",
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

    def mock_parse_arguments():
        """Simule la lecture des arguments."""

        vCalls.append("parse_arguments")

        return vArguments

    def mock_process_books(
        pUrl,
        pOutputFile,
        pConfig,
        pRefresh
    ):
        """Simule le traitement des livres."""

        vCalls.append("process_books")

        assert pConfig.max_items == 100
        assert pConfig.delay == 1.0
        assert pConfig.timeout == 30
        assert pConfig.max_pages == 2
        assert pRefresh is False

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base."""

        vCalls.append("initialize_database")

    monkeypatch.setattr(
        main,
        "parse_arguments",
        mock_parse_arguments
    )

    monkeypatch.setattr(
        main,
        "process_books",
        mock_process_books
    )

    monkeypatch.setattr(
        main,
        "initialize_database",
        mock_initialize_database
    )

    main.main()

    assert vCalls == [
        "parse_arguments",
        "initialize_database",
        "process_books"
    ]