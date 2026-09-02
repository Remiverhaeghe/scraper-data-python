from utils.url import build_absolute_url


def test_build_absolute_url():
    """Vérifie la construction d'une URL absolue."""

    result = build_absolute_url(
        "https://books.toscrape.com/catalogue/",
        "a-light-in-the-attic_1000/index.html"
    )

    assert result == (
        "https://books.toscrape.com/catalogue/"
        "a-light-in-the-attic_1000/index.html"
    )


def test_build_absolute_url_empty():
    """Vérifie la gestion d'une URL vide."""

    result = build_absolute_url(
        "https://books.toscrape.com/catalogue/",
        ""
    )

    assert result == ""