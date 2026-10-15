"""Tests de l'import groupé des lots de révision validés"""

from datetime import datetime

import pytest

import job.quiz_packs as quiz_packs
from job.quiz import flag_question, get_flagged_questions, load_active_quiz
from job.quiz_import import describe_quiz_import
from job.quiz_packs import import_validated_packs, list_validated_packs
from storage.database import initialize_database
from tools.quiz_lot import build_pack

NOW = datetime(2026, 10, 15, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def write_pack(pFolder, pTheme):
    """Écrit l'archive validée d'un lot du dépôt dans pFolder."""

    vName, vContent = build_pack(pTheme)
    (pFolder / vName).write_bytes(vContent)


def test_list_validated_packs_keeps_only_validated_archives(tmp_path, monkeypatch):
    """Vérifie que seules les archives « -valide.zip » sont proposées."""

    (tmp_path / "b-l1-valide.zip").write_bytes(b"")
    (tmp_path / "a-l1-valide.zip").write_bytes(b"")
    (tmp_path / "lot-chatgpt-ecarte.zip").write_bytes(b"")

    assert [vPack.name for vPack in list_validated_packs(tmp_path)] == [
        "a-l1-valide.zip",
        "b-l1-valide.zip",
    ]
    assert list_validated_packs(tmp_path / "absent") == []

    monkeypatch.setattr(quiz_packs, "QUIZ_PACKS_DIRECTORY", str(tmp_path))

    assert len(list_validated_packs()) == 2


def test_import_validated_packs_imports_then_changes_nothing(database_file, tmp_path):
    """Vérifie l'import groupé puis une réimportation sans effet."""

    vFolder = tmp_path / "packs"
    vFolder.mkdir()
    write_pack(vFolder, "grafcet")
    write_pack(vFolder, "regulation")

    vFirst = import_validated_packs(database_file, NOW, vFolder)

    assert (vFirst["added"], vFirst["warnings"], vFirst["rejected"]) == (200, [], [])
    assert len(vFirst["quality"]) == 2
    assert {"grafcet", "regulation"} <= set(load_active_quiz(database_file))

    flag_question(database_file, "grafcet-l1-001")

    vSecond = import_validated_packs(database_file, NOW, vFolder)

    assert (vSecond["added"], vSecond["replaced"], vSecond["unchanged"]) == (0, 0, 200)
    assert describe_quiz_import(vSecond).startswith(
        "0 question(s) ajoutée(s), 200 inchangée(s) dans 2 thèmes"
    )
    # Une réimportation identique ne remet pas une question signalée en jeu.
    assert "grafcet-l1-001" in get_flagged_questions(database_file)


def test_unreadable_archive_does_not_block_the_others(database_file, tmp_path):
    """Vérifie qu'une archive illisible est écartée sans bloquer les suivantes."""

    (tmp_path / "abime-l1-valide.zip").write_bytes(b"pas une archive")
    write_pack(tmp_path, "grafcet")

    vReport = import_validated_packs(database_file, NOW, tmp_path)

    assert vReport["added"] == 100
    assert len(vReport["rejected"]) == 1
    assert vReport["rejected"][0].startswith("abime-l1-valide.zip : ")


def test_import_validated_packs_needs_an_archive(database_file, tmp_path):
    """Vérifie le message quand le dossier ne contient aucune archive validée."""

    with pytest.raises(ValueError, match="Aucune archive"):
        import_validated_packs(database_file, NOW, tmp_path)
