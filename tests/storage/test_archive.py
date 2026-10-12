"""Tests de l'export et de la restauration de la sauvegarde complète"""

import sqlite3
import zipfile
from datetime import datetime

import pandas as pd
import pytest

import storage.archive as archive
from storage.archive import (
    ARCHIVE_DATABASE_NAME,
    export_archive,
    restore_archive,
)
from storage.attachments import add_attachment, get_attachment_directory
from storage.backup import BACKUP_DIRECTORY_NAME
from storage.database import initialize_database
from storage.job_offers import count_offers, save_offers

NOW = datetime(2026, 10, 12, 9, 30)


def create_database(pDirectory, pTitles):
    """Crée une base avec des offres et une pièce jointe sur la première."""

    pDirectory.mkdir()
    rDatabaseFile = pDirectory / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {"source": "remotive", "source_id": str(vIndex), "title": vTitle}
                for vIndex, vTitle in enumerate(pTitles)
            ]
        ),
        NOW,
    )
    add_attachment(rDatabaseFile, "remotive", "0", "cv.pdf", b"%PDF cv", NOW)

    return rDatabaseFile


def test_export_then_restore_replaces_data(tmp_path):
    """Vérifie l'aller-retour : base et pièces jointes restaurées, anciennes gardées."""

    vSource = create_database(tmp_path / "ancien", ["A", "B", "C"])
    vTarget = create_database(tmp_path / "nouveau", ["Z"])
    vArchive = tmp_path / "sauvegarde.zip"

    assert export_archive(vSource, vArchive) == 1

    vBackupFile = restore_archive(vTarget, vArchive, NOW)

    assert count_offers(vTarget) == 3
    assert "avant-restauration" in vBackupFile.name
    assert [
        vFile.read_bytes() for vFile in get_attachment_directory(vTarget).iterdir()
    ] == [b"%PDF cv"]
    # Les pièces jointes remplacées sont rangées avec les sauvegardes.
    assert any(
        vPath.name.startswith("attachments-")
        for vPath in (tmp_path / "nouveau" / BACKUP_DIRECTORY_NAME).iterdir()
    )


def write_archive(pPath, pEntries):
    """Écrit une archive avec les fichiers donnés."""

    with zipfile.ZipFile(pPath, "w") as vArchive:
        for vName, vContent in pEntries.items():
            vArchive.writestr(vName, vContent)


@pytest.mark.parametrize(
    "pEntries, pMessage",
    [
        ({"autre.txt": "x"}, "base de données est absente"),
        (
            {ARCHIVE_DATABASE_NAME: "x", "attachments/../../evil.pdf": "x"},
            "fichier inattendu",
        ),
        ({ARCHIVE_DATABASE_NAME: "pas une base"}, "base est illisible"),
    ],
)
def test_restore_refuses_invalid_archives(tmp_path, pEntries, pMessage):
    """Vérifie le refus d'une archive incomplète, piégée ou illisible, sans rien changer."""

    vTarget = create_database(tmp_path / "base", ["Z"])
    vArchive = tmp_path / "archive.zip"
    write_archive(vArchive, pEntries)

    with pytest.raises(ValueError, match=pMessage):
        restore_archive(vTarget, vArchive, NOW)

    assert count_offers(vTarget) == 1
    assert not (tmp_path / "evil.pdf").exists()


def test_restore_refuses_other_files_and_versions(tmp_path):
    """Vérifie le refus d'un fichier non .zip et d'une base trop récente."""

    vTarget = create_database(tmp_path / "base", ["Z"])
    vText = tmp_path / "archive.zip"
    vText.write_text("texte", encoding="utf-8")

    with pytest.raises(ValueError, match="pas un fichier .zip"):
        restore_archive(vTarget, vText, NOW)

    vFuture = tmp_path / "future.db"
    vConnection = sqlite3.connect(vFuture)
    vConnection.execute("PRAGMA user_version = 999")
    vConnection.close()

    vArchive = tmp_path / "future.zip"
    write_archive(vArchive, {ARCHIVE_DATABASE_NAME: vFuture.read_bytes()})

    with pytest.raises(ValueError, match="version de base 999"):
        restore_archive(vTarget, vArchive, NOW)


def test_export_skips_missing_attachment(tmp_path, caplog):
    """Vérifie qu'une pièce jointe absente du disque est signalée et ignorée."""

    vSource = create_database(tmp_path / "base", ["A"])

    for vFile in get_attachment_directory(vSource).iterdir():
        vFile.unlink()

    assert export_archive(vSource, tmp_path / "sauvegarde.zip") == 0
    assert "Pièce jointe absente du disque" in caplog.text


@pytest.mark.parametrize(
    "pLimit, pMessage",
    [
        ("MAX_ATTACHMENT_BYTES", "trop volumineux"),
        ("MAX_ARCHIVE_BYTES", "contenu trop volumineux"),
    ],
)
def test_restore_refuses_oversized_archives(tmp_path, monkeypatch, pLimit, pMessage):
    """Vérifie le refus d'un fichier ou d'une archive au-delà des limites."""

    vSource = create_database(tmp_path / "ancien", ["A"])
    vTarget = create_database(tmp_path / "nouveau", ["Z"])
    vArchive = tmp_path / "sauvegarde.zip"
    export_archive(vSource, vArchive)

    monkeypatch.setattr(archive, pLimit, 3)

    with pytest.raises(ValueError, match=pMessage):
        restore_archive(vTarget, vArchive, NOW)


def test_restore_refuses_foreign_database(tmp_path):
    """Vérifie le refus d'une base SQLite qui n'est pas celle de l'application."""

    vTarget = create_database(tmp_path / "base", ["Z"])
    vForeign = tmp_path / "autre.db"
    vConnection = sqlite3.connect(vForeign)
    vConnection.execute("CREATE TABLE client (id INTEGER)")
    vConnection.execute("PRAGMA user_version = 1")
    vConnection.close()

    vArchive = tmp_path / "autre.zip"
    write_archive(vArchive, {ARCHIVE_DATABASE_NAME: vForeign.read_bytes()})

    with pytest.raises(ValueError, match="pas une base de l'application"):
        restore_archive(vTarget, vArchive, NOW)
