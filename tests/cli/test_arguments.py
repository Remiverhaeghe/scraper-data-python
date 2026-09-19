# ============================================================================
# Tests de la gestion des arguments de ligne de commande
# ============================================================================


from unittest.mock import patch

from cli.arguments import parse_arguments


def test_parse_arguments_default_values():
    """
    Vérifie les valeurs par défaut des arguments.
    """

    with patch(
        "sys.argv",
        ["main.py"]
    ):
        vArguments = parse_arguments()

    assert vArguments.max_items is None
    assert vArguments.delay == 0.0
    assert vArguments.timeout == 10
    assert vArguments.max_pages is None
    assert vArguments.refresh is False
    assert vArguments.title is None
    assert vArguments.max_price is None
    assert vArguments.min_rating is None


def test_parse_arguments_common_configuration():
    """
    Vérifie la récupération des paramètres communs au scraping.
    """

    with patch(
        "sys.argv",
        [
            "main.py",
            "--max-items",
            "100",
            "--delay",
            "2.5",
            "--timeout",
            "30"
        ]
    ):
        vArguments = parse_arguments()

    assert vArguments.max_items == 100
    assert vArguments.delay == 2.5
    assert vArguments.timeout == 30


def test_parse_arguments_book_configuration():
    """
    Vérifie la récupération des paramètres spécifiques aux livres.
    """

    with patch(
        "sys.argv",
        [
            "main.py",
            "--max-pages",
            "5",
            "--title",
            "Python",
            "--max-price",
            "50.0",
            "--min-rating",
            "4",
            "--refresh"
        ]
    ):
        vArguments = parse_arguments()

    assert vArguments.max_pages == 5
    assert vArguments.title == "Python"
    assert vArguments.max_price == 50.0
    assert vArguments.min_rating == 4
    assert vArguments.refresh is True