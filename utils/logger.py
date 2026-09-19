# ============================================================================
# Configuration du système de logs
# ============================================================================


import logging
from pathlib import Path


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "scraper.log"


def get_logger(pName):
    """
    Crée et configure un logger.

    :param pName: Nom du logger.
    :return: Logger configuré.
    """

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    vLogger = logging.getLogger(
        pName
    )

    if vLogger.handlers:
        rLogger = vLogger

    else:
        vLogger.setLevel(
            logging.INFO
        )

        vFormatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        vFileHandler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        )

        vConsoleHandler = logging.StreamHandler()

        vFileHandler.setFormatter(
            vFormatter
        )

        vConsoleHandler.setFormatter(
            vFormatter
        )

        vLogger.addHandler(
            vFileHandler
        )

        vLogger.addHandler(
            vConsoleHandler
        )

        rLogger = vLogger

    return rLogger