"""
Test de la configuration de l'application.
"""

from config import (
    MAX_RATING,
    MIN_RATING,
    OUTPUT_FILE,
    REQUEST_TIMEOUT,
    URL
)


def test_config():
    """Vérifie que la configuration de l'application est cohérente."""

    assert URL
    assert OUTPUT_FILE
    assert REQUEST_TIMEOUT > 0
    assert MIN_RATING <= MAX_RATING