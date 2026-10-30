"""Tests des montages électriques : solutions, erreurs classiques, schémas libres"""

from datetime import datetime

import pytest

from job.circuit_levels import (
    build_circuit_overview,
    build_values,
    delete_schema,
    find_schema,
    get_solution,
    load_levels,
    read_schema,
    run_level,
    save_attempt,
    save_schema,
)
from job.progress import load_activity
from storage.database import initialize_database


@pytest.mark.parametrize("pLevel", list(load_levels().values()))
def test_every_solution_passes_through_the_editor_format(pLevel):
    """Vérifie que chaque solution, relue comme un envoi de l'éditeur, réussit."""

    vComponents, vWires, vValues = get_solution(pLevel)
    vRead = read_schema({"components": vComponents, "wires": vWires}, pLevel["palette"])

    assert run_level(pLevel, *vRead, vValues)["passed"]


def run_mistake(pLevelId, pWires, pValues=None):
    """Retourne le résultat d'un niveau câblé autrement que la solution."""

    vLevel = load_levels()[pLevelId]
    vComponents = vLevel["solution_components"]

    return run_level(
        vLevel,
        vComponents,
        pWires,
        build_values(
            vComponents, pValues or {}, vLevel.get("values"), vLevel.get("editable")
        ),
    )


def test_classic_mistakes_fail_with_details():
    """Vérifie le neutre coupé, les lampes en série et l'ampèremètre en parallèle."""

    vNeutral = run_mistake(
        "lampe-simple",
        [
            ["alimentation", "L", "disjoncteur", "1"],
            ["disjoncteur", "2", "lampe_bornes", "1"],
            ["lampe_bornes", "2", "interrupteur", "1"],
            ["interrupteur", "2", "alimentation", "N"],
        ],
    )
    vSeries = run_mistake(
        "deux-lampes",
        [
            ["alimentation", "L", "disjoncteur", "1"],
            ["disjoncteur", "2", "interrupteur", "1"],
            ["interrupteur", "2", "lampe_bornes-1", "1"],
            ["lampe_bornes-1", "2", "lampe_bornes-2", "1"],
            ["lampe_bornes-2", "2", "alimentation", "N"],
        ],
    )
    vParallel = run_mistake(
        "mesure-courant",
        [
            ["alimentation", "L", "disjoncteur", "1"],
            ["disjoncteur", "2", "interrupteur", "1"],
            ["interrupteur", "2", "lampe_bornes", "1"],
            ["lampe_bornes", "2", "alimentation", "N"],
            ["amperemetre", "1", "lampe_bornes", "1"],
            ["amperemetre", "2", "lampe_bornes", "2"],
        ],
    )
    vLed = run_mistake(
        "led-resistance", load_levels()["led-resistance"]["solution_wires"]
    )

    assert "Lampe : reste sous 230 V" in vNeutral["checks"][0]["details"]
    assert "Lampe 1 : faible" in vSeries["checks"][0]["details"]
    assert any("Disjoncteur" in vText for vText in vParallel["checks"][0]["details"])
    assert not vLed["passed"]


def test_schema_outside_the_palette_is_refused():
    """Vérifie le refus d'un schéma vide ou d'un composant hors palette."""

    vPalette = load_levels()["lampe-simple"]["palette"]

    with pytest.raises(ValueError):
        read_schema({"components": [], "wires": []}, vPalette)

    with pytest.raises(ValueError):
        read_schema(
            {"components": [{"id": "pile", "type": "pile", "x": 0, "y": 0}]}, vPalette
        )


def test_progress_and_free_schemas(tmp_path):
    """Vérifie la réussite datée, l'XP et les schémas libres enregistrés puis supprimés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vNow = datetime(2026, 10, 30, 9, 0)
    vSchema = {"components": [], "wires": []}

    assert save_attempt(vDatabaseFile, "diviseur", vSchema, {}, True, vNow)
    assert not save_attempt(vDatabaseFile, "diviseur", vSchema, {}, True, vNow)
    assert load_activity(vDatabaseFile)[vNow.date()]["xp"] == 20

    save_schema(vDatabaseFile, "  Mon   montage ", vSchema, {"pile": 12})
    save_schema(vDatabaseFile, "Mon montage", vSchema, {"pile": 5})

    with pytest.raises(ValueError):
        save_schema(vDatabaseFile, "   ", vSchema, {})

    vOverview = build_circuit_overview(vDatabaseFile)

    assert vOverview["passed"] == 1
    assert vOverview["schemas"] == ["Mon montage"]
    assert find_schema(vDatabaseFile, "Mon montage")["values"] == {"pile": 5}

    delete_schema(vDatabaseFile, "Mon montage")

    assert find_schema(vDatabaseFile, "Mon montage") is None
