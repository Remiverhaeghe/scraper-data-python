# ============================================================================
# Tests des méthodes de gestion des URLs
# ============================================================================


from utils.url import build_absolute_url


def test_build_absolute_url():
    """
    Vérifie qu'une URL relative est correctement transformée
    en URL absolue.
    """

    vBaseUrl = "https://books.toscrape.com/catalogue/"
    vRelativeUrl = "a-light-in-the-attic_1000/index.html"

    rUrl = build_absolute_url(
        vBaseUrl,
        vRelativeUrl
    )

    assert rUrl == (
        "https://books.toscrape.com/catalogue/"
        "a-light-in-the-attic_1000/index.html"
    )


def test_build_absolute_url_empty():
    """
    Vérifie qu'une URL relative vide retourne une chaîne vide.
    """

    vBaseUrl = "https://books.toscrape.com/catalogue/"
    vRelativeUrl = ""

    rUrl = build_absolute_url(
        vBaseUrl,
        vRelativeUrl
    )

    assert rUrl == ""