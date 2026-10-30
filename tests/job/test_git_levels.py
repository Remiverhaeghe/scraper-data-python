"""Tests des niveaux du bac à sable Git et de leur progression"""

from datetime import datetime

import pytest

from job.git_levels import (
    LEVELS,
    build_level_list,
    build_level_view,
    is_goal_reached,
    run_level_command,
)
from job.git_sandbox import MAX_HISTORY, replay
from storage.database import initialize_database
from storage.git_levels import get_git_level_results

NOW = datetime(2026, 10, 15, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


@pytest.mark.parametrize("pLevel", LEVELS, ids=lambda pLevel: pLevel.id)
def test_level_is_complete_and_solvable(pLevel):
    """Vérifie un niveau : textes présents, départ différent de l'objectif."""

    assert pLevel.title and pLevel.series and pLevel.intro and pLevel.hint
    assert not is_goal_reached(pLevel, replay(pLevel.setup))
    assert is_goal_reached(pLevel, replay(pLevel.setup + pLevel.solution))


def test_level_identifiers_are_unique():
    """Vérifie que deux niveaux ne partagent pas le même identifiant."""

    vIds = [vLevel.id for vLevel in LEVELS]

    assert len(vIds) == len(set(vIds))


def test_goal_compares_shape_not_new_identifiers():
    """Vérifie qu'un autre chemin vers le même graphe réussit, pas un graphe voisin."""

    vLevels = {vLevel.id: vLevel for vLevel in LEVELS}
    vBranch = vLevels["nouvelle-branche"]
    vRebase = vLevels["rebase"]

    assert is_goal_reached(
        vBranch,
        replay(
            vBranch.setup + ("git branch essai", "git checkout essai", "git commit")
        ),
    )
    assert not is_goal_reached(vRebase, replay(vRebase.setup + ("git merge ecran",)))


def test_level_is_played_then_saved_with_best_count(database_file):
    """Vérifie une commande refusée, la réussite, puis le meilleur résultat gardé."""

    vHistory, vMessage, vTone = run_level_command(
        database_file, "fusion", [], "git merge absente", NOW
    )

    assert (vHistory, vTone) == ([], "danger")
    assert "Référence inconnue" in vMessage

    vHistory, vMessage, vTone = run_level_command(
        database_file,
        "fusion",
        ["git commit", "git reset HEAD^"],
        "git merge correctif",
        NOW,
    )

    assert vTone == "success"
    assert vMessage == (
        "Niveau réussi en 3 commande(s), la solution de référence en utilise 1."
    )
    assert (
        run_level_command(database_file, "fusion", vHistory, "git commit", NOW)[2]
        == "warning"
    )

    vMessage = run_level_command(
        database_file, "fusion", [], "git  merge   correctif", NOW
    )[1]

    assert vMessage == "Niveau réussi en 1 commande(s) : parcours optimal."
    assert get_git_level_results(database_file) == {"fusion": 1}

    run_level_command(
        database_file,
        "fusion",
        ["git commit", "git reset HEAD^"],
        "git merge correctif",
        NOW,
    )
    vLevels = {vItem["id"]: vItem for vItem in build_level_list(database_file)}

    assert (vLevels["fusion"]["best"], vLevels["fusion"]["par"]) == (1, 1)
    assert vLevels["rebase"]["best"] is None


def test_command_in_progress_is_kept_in_history(database_file):
    """Vérifie qu'une commande juste, sans atteindre l'objectif, complète l'historique."""

    assert run_level_command(
        database_file, "premiers-commits", [], "git commit", NOW
    ) == (["git commit"], "Commit C1 enregistré", "info")


def test_level_view_follows_the_history():
    """Vérifie l'affichage d'un niveau : graphes, réussite et niveau suivant."""

    vView = build_level_view("premiers-commits", ["git commit"])

    assert not vView["done"]
    assert vView["next_id"] == "nouvelle-branche"
    assert vView["graph"].count("<circle") == 2
    assert vView["goal"].count("<circle") == 3
    assert build_level_view("premiers-commits", ["git commit"] * 2)["done"]
    assert build_level_view(LEVELS[-1].id, [])["next_id"] is None


@pytest.mark.parametrize(
    ("pLevelId", "pHistory", "pMessage"),
    [
        ("inconnu", [], "Niveau inconnu"),
        ("fusion", ["git bisect"], "non prise en charge"),
        ("fusion", ["git status"] * (MAX_HISTORY + 1), "recommencez le niveau"),
    ],
)
def test_invalid_level_or_history_is_refused(pLevelId, pHistory, pMessage):
    """Vérifie le refus d'un niveau inconnu ou d'un historique altéré ou trop long."""

    with pytest.raises(ValueError, match=pMessage):
        build_level_view(pLevelId, pHistory)


def test_history_limit_is_reported(database_file):
    """Vérifie le message lorsque la limite de commandes est atteinte."""

    vHistory = ["git status"] * MAX_HISTORY

    assert run_level_command(database_file, "fusion", vHistory, "git status", NOW) == (
        vHistory,
        f"Limite de {MAX_HISTORY} commandes atteinte.",
        "warning",
    )
