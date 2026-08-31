"""
Tests du système de logs.
"""

from pathlib import Path

from utils.logger import get_logger


def test_logger():
    """Vérifie la création du logger."""

    logger = get_logger("test")
    logger.info("Test du système de logs")

    log_file = Path("logs/scraper.log")

    assert logger.name == "test"
    assert logger.level > 0
    assert len(logger.handlers) == 2
    assert log_file.exists()