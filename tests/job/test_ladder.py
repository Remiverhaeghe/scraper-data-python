"""Tests du simulateur d'automate : langage, dessin, niveaux et progression"""

from datetime import datetime

import pytest

from job.ladder import LadderError, evaluate, parse_program, render_svg
from job.ladder_game import (
    build_ladder_overview,
    get_level,
    load_levels,
    render_chronogram,
    run_level,
    save_attempt,
)
from job.progress import load_activity
from storage.database import initialize_database

NOW = datetime(2026, 10, 30, 10, 0)


def test_program_is_parsed_into_rungs():
    """Vérifie les bobines, SET, TON, CTU, les commentaires et le contact à ouverture."""

    vRungs = parse_program(
        "# commentaire\nmoteur = (marche | moteur) & !arret\n\n"
        "SET x1 = depart\nt1 = TON(x1, 500ms)\nlot = CTU(piece, 5, acquit)",
        {"marche", "arret", "depart", "piece", "acquit"},
    )

    assert [vRung["kind"] for vRung in vRungs] == ["coil", "set", "ton", "ctu"]
    assert vRungs[0]["line"] == 2
    assert vRungs[2]["preset"] == 0.5
    assert vRungs[3]["preset"] == 5
    assert evaluate(vRungs[0]["expr"], {"marche": True, "arret": False})
    assert not evaluate(vRungs[0]["expr"], {"marche": True, "arret": True})


@pytest.mark.parametrize(
    ("pProgram", "pMessage"),
    [
        ("moteur = !(marche | arret)", "devant une parenthèse"),
        ("marche = arret", "est une entrée"),
        ("moteur = marche &", "ligne incomplète"),
        ("moteur = marche arret", "en trop"),
        ("t = TON(marche, 0s)", "positive"),
        ("Moteur = marche", "nom de variable"),
        ("moteur = marche ; arret", "caractère inattendu"),
    ],
)
def test_writing_errors_name_the_line(pProgram, pMessage):
    """Vérifie un message clair, avec le numéro de ligne, pour chaque faute."""

    with pytest.raises(LadderError, match=pMessage) as vError:
        parse_program(f"\n{pProgram}", {"marche", "arret"})

    assert vError.value.line == 2


def test_ladder_is_drawn_with_live_contacts():
    """Vérifie le dessin : contacts, bobine, boîte TON et contact passant coloré."""

    vRungs = parse_program(
        "moteur = (marche | moteur) & arret\nt = TON(moteur, 2s)", set()
    )
    vSvg = render_svg(vRungs, {"arret": True})

    assert vSvg.startswith("<svg") and "<script" not in vSvg
    assert ">TON<" in vSvg and ">marche<" in vSvg
    assert "#16a34a" in vSvg


@pytest.mark.parametrize("pLevel", list(load_levels().values()))
def test_solution_passes_and_starter_fails(pLevel):
    """Vérifie que chaque solution passe tous les tests et que le départ ne suffit pas."""

    vSolution = run_level(pLevel, pLevel["solution"])

    assert vSolution["passed"], [
        vCheck["message"] for vCheck in vSolution["checks"] if not vCheck["passed"]
    ]
    assert not run_level(pLevel, pLevel["starter"])["passed"]


@pytest.mark.parametrize(
    ("pLevelId", "pProgram"),
    [
        ("marche-arret", "moteur = marche | moteur & arret"),
        ("marche-arret", "moteur = (marche | moteur) & !arret"),
        (
            "grafcet-percage",
            "SET x1 = depart & haut & !x1 & !x2 & !x3\nRESET x1 = x1 & bas\n"
            "SET x2 = x1 & bas\nt = TON(x2, 1s)\nSET x3 = x2 & t\nRESET x2 = x3\n"
            "RESET x3 = x3 & haut\ndescendre = x1\nmonter = x3\nrotation = x1 | x2 | x3",
        ),
        ("grafcet-percage", "descendre = depart | descendre\nmonter = descendre"),
    ],
)
def test_classic_mistakes_fail(pLevelId, pProgram):
    """Vérifie les erreurs classiques : priorité, contact inversé, ordre des lignes."""

    assert not run_level(get_level(pLevelId), pProgram)["passed"]


def test_chronogram_and_progress(tmp_path):
    """Vérifie le chronogramme, la réussite datée une fois et les points gagnés."""

    vLevel = get_level("temporisation")
    vRun = run_level(vLevel, vLevel["solution"])
    vSvg = render_chronogram(vRun["signals"], vRun["samples"], {"depart"})

    assert ">fin_sortie<" in vSvg and ">6 s<" in vSvg

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    assert not save_attempt(
        vDatabaseFile, "temporisation", "sortir = depart", False, NOW
    )
    assert save_attempt(vDatabaseFile, "temporisation", vLevel["solution"], True, NOW)
    assert not save_attempt(
        vDatabaseFile, "temporisation", vLevel["solution"], True, NOW
    )

    vRow = next(
        vRow
        for vRow in build_ladder_overview(vDatabaseFile)["rows"]
        if vRow["id"] == "temporisation"
    )

    assert vRow["passed"] and vRow["program"] == vLevel["solution"]
    assert load_activity(vDatabaseFile)[NOW.date()]["xp"] == 25
    assert run_level(vLevel, "")["error"] == "Le programme est vide."
