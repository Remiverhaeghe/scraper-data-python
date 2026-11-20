"""Tests du paquet de révision livré dans l'application mobile"""

from tools.mobile_package import (
    PACKAGE_FILE,
    build_starter_package,
    read_starter_package,
    write_starter_package,
)


def test_shipped_package_follows_the_shipped_themes():
    """Vérifie que le paquet de l'appli suit les thèmes livrés.

    En cas d'échec : python -m tools.mobile_package, puis commiter le fichier.
    """

    vShipped = read_starter_package()

    assert vShipped is not None, f"{PACKAGE_FILE} manque"
    assert vShipped == build_starter_package()


def test_package_has_only_shipped_content(tmp_path):
    """Vérifie l'écriture : thèmes et questions livrés, fichier identique d'une fois sur l'autre."""

    vFile = tmp_path / "depart.json.gz"
    write_starter_package(vFile)
    vFirst = vFile.read_bytes()
    write_starter_package(vFile)

    vPackage = read_starter_package(vFile)
    assert vFile.read_bytes() == vFirst
    assert vPackage["themes"] and vPackage["questions"]
    assert vPackage["generated_at"] == "2026-01-01T00:00:00"
    assert read_starter_package(tmp_path / "absent.json.gz") is None
