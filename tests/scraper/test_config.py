# ============================================================================
# Tests de la configuration commune aux scrapers
# ============================================================================


import pytest

from scraper.config import ScrapingConfig


def test_default_configuration():
    """
    Vérifie les valeurs par défaut de la configuration.
    """

    vConfig = ScrapingConfig()

    assert vConfig.max_items is None
    assert vConfig.delay == 0.0
    assert vConfig.timeout == 10
    assert vConfig.max_response_size_mb == 5.0


def test_max_response_size_in_bytes():
    """
    Vérifie la conversion de la taille maximale en octets.
    """

    vConfig = ScrapingConfig(
        max_response_size_mb=10
    )

    assert vConfig.max_response_size == 10 * 1024 * 1024


def test_max_response_size_accepts_decimal_value():
    """
    Vérifie qu'une taille décimale en Mo est correctement convertie.
    """

    vConfig = ScrapingConfig(
        max_response_size_mb=2.5
    )

    assert vConfig.max_response_size == int(2.5 * 1024 * 1024)


def test_validate_rejects_invalid_max_response_size():
    """
    Vérifie qu'une taille maximale invalide est refusée.
    """

    vConfig = ScrapingConfig(
        max_response_size_mb=0
    )

    with pytest.raises(ValueError):
        vConfig.validate()