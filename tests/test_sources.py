"""Contrôles des fichiers sources du dépôt"""

import re
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]

# Dossiers écrits par l'application ou les outils, hors du code relu
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "data",
    "logs",
    "output",
    "__pycache__",
    # Fichiers générés par Flutter
    ".dart_tool",
    "build",
}

CHECKED_SUFFIXES = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".qss",
    ".dart",
    ".yaml",
}

# Caractères de contrôle, sauf tabulation et fins de ligne : une séquence mal
# échappée dans un script devient ainsi un caractère invisible.
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def get_source_files():
    """Retourne les fichiers texte du dépôt à contrôler."""

    rFiles = [
        vPath
        for vPath in PROJECT_DIRECTORY.rglob("*")
        if vPath.suffix in CHECKED_SUFFIXES
        and vPath.is_file()
        and not IGNORED_DIRECTORIES & set(vPath.relative_to(PROJECT_DIRECTORY).parts)
    ]

    return rFiles


def test_sources_have_no_control_character():
    """Vérifie qu'aucun fichier source ne contient de caractère de contrôle."""

    vFaulty = [
        str(vPath.relative_to(PROJECT_DIRECTORY))
        for vPath in get_source_files()
        if CONTROL_CHARACTERS.search(
            vPath.read_text(encoding="utf-8", errors="replace")
        )
    ]

    assert vFaulty == []
