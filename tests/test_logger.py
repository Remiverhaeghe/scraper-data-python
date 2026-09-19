# ============================================================================
# Tests du système de logs
# ============================================================================


from pathlib import Path

from utils.logger import get_logger


def test_logger():
    """
    Vérifie la création et la configuration du logger.
    """

    vLogger = get_logger(
        "test"
    )

    vLogger.info(
        "Test du système de logs"
    )

    vLogFile = Path(
        "logs/scraper.log"
    )

    assert vLogger.name == "test"
    assert vLogger.level > 0
    assert len(vLogger.handlers) == 2
    assert vLogFile.exists()


def test_logger_writes_message_to_file():
    """
    Vérifie qu'un message est écrit dans le fichier de logs.
    """

    vLogger = get_logger(
        "test_file"
    )

    vLogger.info(
        "Message de test"
    )

    vLogFile = Path(
        "logs/scraper.log"
    )

    vContent = vLogFile.read_text(
        encoding="utf-8"
    )

    assert "Message de test" in vContent