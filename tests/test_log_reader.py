"""Tests de la lecture des logs"""

import pytest

from utils.log_reader import (
    clear_logs,
    export_logs,
    list_log_files,
    read_log_entries,
)

DAY_ONE = """2026-10-09 08:00:00,100 | INFO | job.application | Début du traitement
2026-10-09 08:00:05,200 | ERROR | web.app | Erreur inattendue
Traceback (most recent call last):
  ValueError: valeur | invalide
"""

DAY_TWO = """2026-10-10 09:00:00,100 | WARNING | job.sources.aggregator | Source en panne
2026-10-10 09:30:00,100 | INFO | scheduler.runner | Recherche planifiée lancée
"""


@pytest.fixture
def log_directory(tmp_path):
    """Crée deux journées de logs et un fichier sans rapport."""

    (tmp_path / "scraper-2026-10-09.log").write_text(DAY_ONE, encoding="utf-8")
    (tmp_path / "scraper-2026-10-10.log").write_text(DAY_TWO, encoding="utf-8")
    (tmp_path / "scraper.log").write_text("ancien format", encoding="utf-8")

    return tmp_path


def test_list_log_files_newest_first(log_directory):
    """Vérifie l'ordre des fichiers et l'exclusion des autres fichiers."""

    assert [vFile.name for vFile in list_log_files(log_directory)] == [
        "scraper-2026-10-10.log",
        "scraper-2026-10-09.log",
    ]


def test_read_log_entries_newest_first_with_traceback(log_directory):
    """Vérifie l'ordre des entrées et le rattachement d'une trace d'erreur."""

    vEntries = read_log_entries(log_directory)

    assert [vEntry["time"] for vEntry in vEntries] == [
        "2026-10-10 09:30:00",
        "2026-10-10 09:00:00",
        "2026-10-09 08:00:05",
        "2026-10-09 08:00:00",
    ]
    assert vEntries[2]["level_label"] == "Erreur"
    assert vEntries[2]["module"] == "web.app"
    assert vEntries[2]["message"].endswith("ValueError: valeur | invalide")


@pytest.mark.parametrize(
    "pLevel, pSearch, pExpected",
    [
        ("WARNING", None, ["Source en panne", "Erreur inattendue"]),
        ("ERROR", None, ["Erreur inattendue"]),
        (None, "SCHEDULER", ["Recherche planifiée lancée"]),
        ("inconnu", "panne", ["Source en panne"]),
    ],
)
def test_read_log_entries_filters(log_directory, pLevel, pSearch, pExpected):
    """Vérifie les filtres par niveau minimal et par texte, module compris."""

    vEntries = read_log_entries(log_directory, pLevel=pLevel, pSearch=pSearch)

    assert [vEntry["message"].split("\n")[0] for vEntry in vEntries] == pExpected


def test_read_log_entries_respects_limit(log_directory):
    """Vérifie que la lecture s'arrête au nombre d'entrées demandé."""

    assert len(read_log_entries(log_directory, pLimit=3)) == 3


def test_export_logs_oldest_first(log_directory):
    """Vérifie que l'export assemble les journaux du plus ancien au plus récent."""

    assert export_logs(log_directory) == DAY_ONE + DAY_TWO


def test_clear_logs_empties_today_and_removes_others(log_directory):
    """Vérifie que le journal du jour est vidé et les autres supprimés."""

    assert clear_logs(log_directory) == 3
    assert sorted(vFile.name for vFile in log_directory.iterdir()) == [
        "scraper-2026-10-10.log"
    ]
    assert (log_directory / "scraper-2026-10-10.log").read_text(encoding="utf-8") == ""
