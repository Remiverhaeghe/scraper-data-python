"""Tests des niveaux de l'atelier Excel : solutions, erreurs classiques, progression"""

from datetime import datetime

from job.achievements import ACHIEVEMENTS
from job.excel_levels import (
    build_excel_overview,
    get_level,
    load_excel_progress,
    load_levels,
    run_level,
    save_attempt,
)
from job.progress import load_activity
from storage.database import initialize_database


def test_every_solution_passes_and_empty_formula_fails():
    """Vérifie chaque niveau : solution réussie, cellule vide refusée."""

    for vLevel in load_levels().values():
        vSolution = run_level(vLevel, vLevel["solution"])

        assert vSolution["passed"], (vLevel["id"], vSolution["message"])
        assert not run_level(vLevel, "=")["passed"], vLevel["id"]


def test_classic_mistakes_get_their_advice():
    """Vérifie les $ oubliés, la recherche approchée et le nombre resté en texte."""

    vTax = run_level(get_level("taux-fige"), "=B2*(1+F1)")
    vLookup = run_level(get_level("recherchev"), "=RECHERCHEV(A2;$F$2:$H$7;2)")
    vYear = run_level(get_level("annee-serie"), "=STXT(A2;4;4)")

    assert vTax["message"].startswith("5 cellules sur 6 diffèrent")
    assert "$F$1" in vTax["advice"][0]
    assert "recherche approchée" in vLookup["advice"][0]
    assert vYear["message"].endswith("B2 : 2019 obtenu (un texte), un nombre attendu.")
    assert vYear["cells"][0]["ok"] is False


def test_formulas_that_dodge_the_exercise_are_refused():
    """Vérifie une valeur recopiée, une fonction imposée absente et une boucle."""

    assert "pas sur des valeurs" in run_level(get_level("nb-si"), "=6")["message"]
    assert run_level(get_level("somme-semaine"), "=B2+C2+D2+E2+F2")["message"] == (
        "Ce niveau attend la fonction SOMME."
    )
    assert "circulaire" in run_level(get_level("nb-si"), "=NB.SI(H2;1)")["message"]


def test_grid_shows_targets_and_formatted_values():
    """Vérifie la feuille affichée : cibles, euros, dates et valeurs calculées."""

    vGrid = run_level(get_level("cout-main-oeuvre"), "=B2*C2")["grid"]
    vDates = run_level(get_level("prochaine-visite"), "")["grid"]

    assert vGrid["columns"] == ["A", "B", "C", "D"]
    assert vGrid["targets"] == ["D2", "D3", "D4", "D5", "D6"]
    assert vGrid["rows"][1] == ["Vidange presse", "2,5", "48,00 €", "120,00 €"]
    assert vDates["rows"][1][1:] == ["31/01/2026", "1", ""]


def test_progress_points_and_trophies(tmp_path):
    """Vérifie la formule gardée, la première réussite datée, l'XP et les trophées."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vNow = datetime(2026, 11, 6, 9, 0)

    assert save_attempt(vDatabaseFile, "nb-si", "=NB(B2:B11)", False, vNow) is False
    assert save_attempt(vDatabaseFile, "nb-si", "=NB.SI(B2:B11;G2)", True, vNow)
    assert save_attempt(vDatabaseFile, "nb-si", "=NB.SI.ENS(B2:B11;G2)", True) is False

    vOverview = build_excel_overview(vDatabaseFile)
    vRows = {
        vRow["id"]: vRow for vSeries in vOverview["series"] for vRow in vSeries["rows"]
    }

    assert load_excel_progress(vDatabaseFile)["levels"]["nb-si"]["passed_at"] == (
        "2026-11-06T09:00:00"
    )
    assert vRows["nb-si"]["formula"] == "=NB.SI.ENS(B2:B11;G2)"
    assert vRows["si-et"]["formula"] == "="
    assert (vOverview["passed"], vOverview["total"]) == (1, len(load_levels()))
    assert load_activity(vDatabaseFile)[vNow.date()]["xp"] == 15
    assert [vEntry[5] for vEntry in ACHIEVEMENTS if vEntry[0] == "excel-all"] == [
        len(load_levels())
    ]
