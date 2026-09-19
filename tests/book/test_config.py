# ============================================================================
# Tests de la configuration du scraping des livres
# ============================================================================


import pytest

from book.config import BookScrapingConfig


def test_default_configuration():
    """
    Vérifie les valeurs par défaut de la configuration Books.
    """

    vConfig = BookScrapingConfig()

    assert vConfig.max_items is None
    assert vConfig.delay == 0.0
    assert vConfig.timeout == 10
    assert vConfig.start_page == 1
    assert vConfig.max_pages is None
    assert vConfig.avoid_duplicates is True
    assert vConfig.title is None
    assert vConfig.max_price is None
    assert vConfig.min_rating is None


def test_valid_configuration():
    """
    Vérifie qu'une configuration valide ne provoque pas d'erreur.
    """

    vConfig = BookScrapingConfig(
        max_items=100,
        delay=1.0,
        timeout=30,
        start_page=2,
        max_pages=5,
        title="Python",
        max_price=50.0,
        min_rating=4
    )

    vConfig.validate()


def test_invalid_max_items():
    """
    Vérifie qu'un nombre maximum d'éléments invalide est rejeté.
    """

    vConfig = BookScrapingConfig(max_items=0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_delay():
    """
    Vérifie qu'un délai négatif est rejeté.
    """

    vConfig = BookScrapingConfig(delay=-1.0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_timeout():
    """
    Vérifie qu'un timeout nul ou négatif est rejeté.
    """

    vConfig = BookScrapingConfig(timeout=0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_start_page():
    """
    Vérifie qu'une page de départ invalide est rejetée.
    """

    vConfig = BookScrapingConfig(start_page=0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_max_pages():
    """
    Vérifie qu'un nombre maximum de pages invalide est rejeté.
    """

    vConfig = BookScrapingConfig(max_pages=0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_max_price():
    """
    Vérifie qu'un prix maximum négatif est rejeté.
    """

    vConfig = BookScrapingConfig(max_price=-10.0)

    with pytest.raises(ValueError):
        vConfig.validate()


def test_invalid_min_rating():
    """
    Vérifie qu'une note minimale en dehors de l'intervalle autorisé est rejetée.
    """

    vConfig = BookScrapingConfig(min_rating=6)

    with pytest.raises(ValueError):
        vConfig.validate()

def test_invalid_min_rating_below_minimum():
    """
    Vérifie qu'une note minimale inférieure à 1 est rejetée.
    """

    vConfig = BookScrapingConfig(
        min_rating=0
    )

    with pytest.raises(ValueError):
        vConfig.validate()