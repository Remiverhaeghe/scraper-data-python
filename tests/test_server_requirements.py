"""Tests du fichier verrouillé des dépendances de l'image Docker"""

import re
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent

PIN_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", re.MULTILINE)


def read_text(pFileName):
    """Retourne le contenu d'un fichier de dépendances du projet."""

    rText = (PROJECT_DIRECTORY / pFileName).read_text(encoding="utf-8")

    return rText


def read_pins(pFileName):
    """Retourne les paquets et versions épinglés d'un fichier de dépendances."""

    # Nom normalisé comme le fait pip (PEP 503) : et_xmlfile vaut et-xmlfile.
    rPins = {
        re.sub(r"[-_.]+", "-", vName).lower(): vVersion
        for vName, vVersion in PIN_PATTERN.findall(read_text(pFileName))
    }

    return rPins


def test_lock_matches_server_requirements_and_has_hashes():
    """Vérifie que le fichier verrouillé suit requirements-server.txt, empreintes comprises."""

    vLocked = read_pins("requirements-server.lock")
    vBlocks = [
        vBlock
        for vBlock in re.split(r"\n(?=\S)", read_text("requirements-server.lock"))
        if "==" in vBlock
    ]

    assert {
        vName: vVersion
        for vName, vVersion in read_pins("requirements-server.txt").items()
        if vLocked.get(vName) != vVersion
    } == {}
    assert len(vBlocks) == len(vLocked)
    assert all("--hash=sha256:" in vBlock for vBlock in vBlocks)


def test_server_requirements_follow_the_main_ones():
    """Vérifie que l'image utilise les mêmes versions que l'application."""

    vMain = read_pins("requirements.txt")

    assert {
        vName: vVersion
        for vName, vVersion in read_pins("requirements-server.txt").items()
        if vMain.get(vName) != vVersion
    } == {}
