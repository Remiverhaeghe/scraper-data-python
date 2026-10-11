"""Tests des pièces jointes des candidatures"""

from datetime import datetime

import pandas as pd
import pytest

from storage.attachments import (
    MAX_ATTACHMENT_BYTES,
    add_attachment,
    clean_file_name,
    delete_attachment,
    get_attachment,
    get_attachments,
)
from storage.database import initialize_database
from storage.job_offers import save_offers
from storage.maintenance import reset_database

NOW = datetime(2026, 10, 11, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une offre."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame([{"source": "remotive", "source_id": "1", "title": "Java"}]),
        NOW,
    )

    return rDatabaseFile


@pytest.mark.parametrize(
    "pFileName, pExpected",
    [
        ("cv.pdf", "cv.pdf"),
        ("..\\..\\secret\\cv.pdf", "cv.pdf"),
        ("../../etc/passwd", "passwd"),
        ("x" * 200 + ".pdf", "x" * 146 + ".pdf"),
        (None, ""),
    ],
)
def test_clean_file_name(pFileName, pExpected):
    """Vérifie que seul le nom du fichier est gardé, sans chemin."""

    assert clean_file_name(pFileName) == pExpected


def test_attachment_round_trip(database_file):
    """Vérifie l'ajout, la lecture puis la suppression d'une pièce jointe."""

    vId = add_attachment(database_file, "remotive", "1", "CV Rémi.pdf", b"%PDF", NOW)

    vAttachment = get_attachment(database_file, vId)

    assert vAttachment["path"].read_bytes() == b"%PDF"
    assert vAttachment["path"].parent == database_file.parent / "attachments"
    assert vAttachment["stored_name"] != "CV Rémi.pdf"
    assert get_attachments(database_file, "remotive", "1") == [
        {"id": vId, "file_name": "CV Rémi.pdf", "size": 4, "added_at": NOW.isoformat()}
    ]

    assert delete_attachment(database_file, vId) is True
    assert not vAttachment["path"].exists()
    assert get_attachments(database_file, "remotive", "1") == []
    assert delete_attachment(database_file, vId) is False


@pytest.mark.parametrize(
    "pFileName, pContent, pMessage",
    [
        ("script.exe", b"MZ", "Type de fichier non accepté"),
        ("cv.pdf", b"", "Le fichier est vide"),
        ("cv.pdf", b"x" * (MAX_ATTACHMENT_BYTES + 1), "trop volumineux"),
    ],
    ids=["type", "vide", "taille"],
)
def test_add_attachment_refuses_invalid_files(
    database_file, pFileName, pContent, pMessage
):
    """Vérifie le refus des fichiers d'un autre type, vides ou trop gros."""

    with pytest.raises(ValueError, match=pMessage):
        add_attachment(database_file, "remotive", "1", pFileName, pContent, NOW)

    assert not (database_file.parent / "attachments").exists() or not any(
        (database_file.parent / "attachments").iterdir()
    )


def test_reset_keeps_attachment_files(database_file):
    """Vérifie que la réinitialisation range les fichiers joints avec les sauvegardes."""

    add_attachment(database_file, "remotive", "1", "cv.pdf", b"%PDF", NOW)

    reset_database(database_file, NOW)

    vMoved = database_file.parent / "backups" / "attachments-20261011-100000"

    assert [vFile.suffix for vFile in vMoved.iterdir()] == [".pdf"]
    assert not (database_file.parent / "attachments").exists()
