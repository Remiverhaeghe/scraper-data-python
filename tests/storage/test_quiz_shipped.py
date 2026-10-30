"""Tests des guides et schémas : livrés avec l'application ou importés"""

import re
from datetime import datetime

from job.quiz import load_quiz
from job.quiz_generation import load_catalog
from job.quiz_import import UNSAFE_SVG_PATTERN
from job.quiz_types import MAX_SCHEMA_LENGTH
from storage.database import initialize_database
from utils.markdown import render_markdown
from storage.quiz_questions import (
    get_quiz_asset,
    get_quiz_assets,
    get_quiz_guide,
    get_quiz_guides,
    load_shipped_assets,
    load_shipped_guides,
    save_quiz_assets,
    save_quiz_guides,
)


def test_shipped_guide_is_listed_then_replaced_by_an_imported_one(tmp_path):
    """Vérifie le guide livré, puis la priorité d'un guide importé du même nom."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vLean = get_quiz_guide(vDatabaseFile, "lean")

    assert vLean["title"] == "Lean et amélioration continue"
    assert "Takt time" in vLean["content"]
    assert {"name": "lean", "theme": "lean", "title": vLean["title"]} in (
        get_quiz_guides(vDatabaseFile)
    )

    save_quiz_guides(
        vDatabaseFile,
        [("lean", "lean", "Lean importé", "# Lean importé")],
        datetime(2026, 10, 30),
    )

    assert get_quiz_guide(vDatabaseFile, "lean")["title"] == "Lean importé"
    assert [vGuide["name"] for vGuide in get_quiz_guides(vDatabaseFile)].count(
        "lean"
    ) == 1


def test_every_shipped_guide_belongs_to_a_theme():
    """Vérifie que chaque guide livré porte le nom d'un thème connu."""

    vThemes = set(load_quiz()) | {vTheme["id"] for vTheme in load_catalog()}

    assert load_shipped_guides()
    assert set(load_shipped_guides()) <= vThemes


def test_shipped_schemas_are_safe_and_used_by_their_questions():
    """Vérifie les schémas livrés : sans script, assez légers, cités et bien zonés."""

    vAssets = load_shipped_assets()
    vQuestions = [
        vQuestion
        for vTheme in load_quiz().values()
        for vQuestion in vTheme["questions"]
    ]

    assert vAssets
    assert not [
        vName for vName, vSvg in vAssets.items() if UNSAFE_SVG_PATTERN.search(vSvg)
    ]
    assert all(len(vSvg) <= MAX_SCHEMA_LENGTH for vSvg in vAssets.values())

    for vQuestion in vQuestions:
        if "visual" not in vQuestion:
            continue

        vSvg = vAssets[vQuestion["visual"]["asset"]]
        vWidth, vHeight = map(
            float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', vSvg).groups()
        )

        for vZone in vQuestion.get("zones", []):
            vX, vY, vZoneWidth, vZoneHeight = vZone["rect"]

            assert vX + vZoneWidth <= vWidth and vY + vZoneHeight <= vHeight, vZone


def test_shipped_schema_is_served_unless_an_imported_one_replaces_it(tmp_path):
    """Vérifie le schéma livré, sa présence dans la liste et la priorité de l'import."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert "<svg" in get_quiz_asset(vDatabaseFile, "lean-trs.svg")
    assert "lean-trs.svg" in get_quiz_assets(vDatabaseFile)
    assert "lean-trs.svg" not in get_quiz_assets(vDatabaseFile, pShipped=False)

    save_quiz_assets(
        vDatabaseFile, {"lean-trs.svg": "<svg>importé</svg>"}, datetime(2026, 10, 30)
    )

    assert get_quiz_asset(vDatabaseFile, "lean-trs.svg") == "<svg>importé</svg>"


def test_shipped_guide_links_render_whole():
    """Vérifie que chaque lien d'un guide livré est rendu entier, parenthèses encodées."""

    for vName, vGuide in load_shipped_guides().items():
        vLinks = re.findall(r"\]\((https?://[^)\s]*)\)", vGuide["content"])
        vRendered = re.findall(r'href="([^"]+)"', render_markdown(vGuide["content"]))

        assert vLinks, vName
        assert vRendered == vLinks, vName
