"""Tests du système de logs"""

import logging
from datetime import date

import pytest

import utils.logger as logger_module
from utils.logger import (
    DEFAULT_LOG_RETENTION_DAYS,
    DailyFileHandler,
    get_log_file,
    get_logger,
    get_retention_days,
    purge_old_logs,
)


class FakeDate(date):
    """Date du jour réglable, pour simuler le passage à minuit."""

    current = date(2026, 10, 10)

    @classmethod
    def today(cls):
        return cls.current


def test_logger_uses_shared_outputs():
    """Vérifie qu'un logger de module écrit dans les sorties communes."""

    vLogger = get_logger("test")
    vRootHandlers = logging.getLogger().handlers

    assert vLogger.name == "test"
    assert vLogger.handlers == []
    assert (
        sum(isinstance(vHandler, DailyFileHandler) for vHandler in vRootHandlers) == 1
    )

    get_logger("autre")

    assert len(logging.getLogger().handlers) == len(vRootHandlers)


@pytest.mark.parametrize(
    "pValue, pDays", [("30", 30), ("0", 1), ("abc", 14), (None, 14)]
)
def test_get_retention_days(monkeypatch, pValue, pDays):
    """Vérifie la durée de conservation lue dans l'environnement."""

    if pValue is None:
        monkeypatch.delenv("LOG_RETENTION_DAYS", raising=False)
    else:
        monkeypatch.setenv("LOG_RETENTION_DAYS", pValue)

    assert get_retention_days() == pDays
    assert DEFAULT_LOG_RETENTION_DAYS == 14


def test_purge_old_logs_keeps_recent_and_other_files(tmp_path):
    """Vérifie que seuls les fichiers du jour trop anciens sont supprimés."""

    for vName in (
        "scraper-2026-09-20.log",
        "scraper-2026-09-30.log",
        "scraper-2026-10-10.log",
        "scraper.log",
        "notes.txt",
    ):
        (tmp_path / vName).write_text("x", encoding="utf-8")

    vDeleted = purge_old_logs(tmp_path, date(2026, 10, 10), 14)

    assert vDeleted == ["scraper-2026-09-20.log"]
    assert sorted(vFile.name for vFile in tmp_path.iterdir()) == [
        "notes.txt",
        "scraper-2026-09-30.log",
        "scraper-2026-10-10.log",
        "scraper.log",
    ]


def test_daily_handler_switches_file_at_midnight(tmp_path, monkeypatch):
    """Vérifie l'écriture dans le fichier du jour, puis dans celui du lendemain."""

    monkeypatch.setattr(logger_module, "date", FakeDate)
    FakeDate.current = date(2026, 10, 10)

    (tmp_path / "scraper-2026-09-01.log").write_text("ancien", encoding="utf-8")

    vHandler = DailyFileHandler(tmp_path, 14)
    vHandler.setFormatter(logging.Formatter("%(message)s"))

    vLogger = logging.getLogger("test_daily")
    vLogger.propagate = False
    vLogger.addHandler(vHandler)

    try:
        vLogger.warning("Premier jour")
        FakeDate.current = date(2026, 10, 11)
        vLogger.warning("Lendemain")

    finally:
        vLogger.removeHandler(vHandler)
        vHandler.close()

    assert not (tmp_path / "scraper-2026-09-01.log").exists()
    assert "Premier jour" in get_log_file(tmp_path, date(2026, 10, 10)).read_text(
        encoding="utf-8"
    )
    assert (
        get_log_file(tmp_path, date(2026, 10, 11)).read_text(encoding="utf-8").strip()
        == "Lendemain"
    )
