"""Tests des schémas à construire : bibliothèque, vérification, correction et dessin"""

import random

import pytest

from job.quiz_types import (
    build_response,
    check_typed_fields,
    grade_answer,
    prepare_question,
)
from job.schema_building import compare_edges, read_answer
from job.schema_drawing import render_expected, route_wire, wrap_label
from job.schema_library import COMPONENT_TYPES, COMPONENTS, HEIGHT, WIDTH, build_icon

MOTOR_FEEDER = {
    "id": "depart-moteur",
    "level": "intermédiaire",
    "type": "construction",
    "question": "Construire le départ d'un moteur triphasé.",
    "explanation": "Sectionner, protéger, commander puis protéger contre les surcharges.",
    "components": [
        {"type": "reseau", "x": 0, "y": 0},
        {"type": "sectionneur", "x": 0, "y": 1},
        {"type": "fusible", "x": 0, "y": 2},
        {"type": "contacteur", "x": 0, "y": 3},
        {"type": "relais_thermique", "x": 0, "y": 4},
        {"type": "moteur", "x": 0, "y": 5},
    ],
    "connections": [
        ["reseau", "sortie", "sectionneur", "1"],
        ["sectionneur", "2", "fusible", "1"],
        ["fusible", "2", "contacteur", "1"],
        ["contacteur", "2", "relais_thermique", "1"],
        ["relais_thermique", "2", "moteur", "entrée"],
    ],
    "distractors": ["differentiel", "transformateur"],
}


def answer(pTypes, pWires):
    """Construit une réponse au format de l'éditeur."""

    rAnswer = {
        "components": [{"type": vType, "x": 0, "y": 0} for vType in pTypes],
        "wires": [list(vWire) for vWire in pWires],
    }

    return rAnswer


EXPECTED_TYPES = [vItem["type"] for vItem in MOTOR_FEEDER["components"]]


def test_library_symbols_are_complete_and_inside_their_frame():
    """Vérifie chaque composant : clé unique, bornes dans le cadre, icône SVG."""

    assert len(COMPONENTS) == len(COMPONENT_TYPES)

    for vType in COMPONENT_TYPES:
        assert vType.label and vType.ports and vType.drawing
        assert all(
            0 <= vX <= WIDTH and 0 <= vY <= HEIGHT for _, (vX, vY) in vType.ports
        )
        assert build_icon(vType.key).startswith("<svg")


def test_construction_question_is_checked_and_prepared():
    """Vérifie la question et la palette : attendus et leurres, dans le désordre."""

    assert check_typed_fields(MOTOR_FEEDER) == ""

    vPalette = prepare_question(MOTOR_FEEDER, random.Random(3))["shuffled"]

    assert sorted(vPalette) == sorted(
        EXPECTED_TYPES + ["differentiel", "transformateur"]
    )


@pytest.mark.parametrize(
    ("pChange", "pMessage"),
    [
        ({"components": MOTOR_FEEDER["components"][:1]}, "composants"),
        (
            {
                "components": MOTOR_FEEDER["components"]
                + [{"type": "moteur", "x": 1, "y": 0}]
            },
            "qu'une fois",
        ),
        (
            {
                "components": MOTOR_FEEDER["components"][:5]
                + [{"type": "moteur", "x": 0, "y": 0}]
            },
            "même case",
        ),
        ({"components": [{"type": "inconnu", "x": 0, "y": 0}] * 2}, "composants"),
        (
            {"connections": [["reseau", "sortie", "sectionneur", "9"]]},
            "liaison invalide",
        ),
        ({"connections": MOTOR_FEEDER["connections"][:4]}, "relié à rien"),
        ({"distractors": ["moteur"]}, "leurres"),
    ],
)
def test_malformed_construction_question_is_refused(pChange, pMessage):
    """Vérifie le refus explicite d'une question de construction mal formée."""

    assert pMessage in check_typed_fields({**MOTOR_FEEDER, **pChange})


def test_correct_schema_is_accepted_even_with_a_symmetric_part_reversed():
    """Vérifie qu'un fusible branché à l'envers reste juste, pas un sens imposé."""

    vWires = [
        ["sectionneur", "1", "reseau", "sortie"],
        ["sectionneur", "2", "fusible", "2"],
        ["fusible", "1", "contacteur", "1"],
        ["contacteur", "2", "relais_thermique", "1"],
        ["moteur", "entrée", "relais_thermique", "2"],
    ]

    vCorrect, vChosen, vExpected = grade_answer(
        MOTOR_FEEDER, answer(EXPECTED_TYPES, vWires)
    )

    assert (vCorrect, vChosen) == (True, "Schéma conforme")
    assert vExpected.startswith(
        "Réseau d'alimentation – Sectionneur ; Sectionneur – Fusible"
    )


def test_wrong_schema_lists_missing_and_extra_parts():
    """Vérifie le détail des écarts : composants et liaisons manquants ou en trop."""

    vCorrect, vChosen, _ = grade_answer(
        MOTOR_FEEDER,
        answer(
            ["reseau", "fusible", "contacteur", "differentiel", "moteur"],
            [
                ["reseau", "sortie", "fusible", "1"],
                ["fusible", "2", "contacteur", "1"],
                ["contacteur", "2", "moteur", "entrée"],
            ],
        ),
    )

    assert not vCorrect
    assert "composants manquants : Relais thermique, Sectionneur" in vChosen
    assert "composants en trop : Interrupteur différentiel" in vChosen
    assert "liaisons en trop : Contact de puissance du contacteur – Moteur" in vChosen


def test_non_symmetric_parts_keep_their_terminals():
    """Vérifie qu'un vérin double effet branché à l'envers est refusé."""

    vMissing, vExtra = compare_edges(
        [["distributeur_52", "4", "verin_double", "fond"]],
        [("distributeur_52", "4", "verin_double", "tige")],
        {"distributeur_52", "verin_double"},
    )

    assert vMissing and vExtra


@pytest.mark.parametrize(
    ("pResponse", "pMessage"),
    [
        ("texte", "illisible"),
        ({"components": []}, "au moins un composant"),
        ({"components": [{"type": "inconnu"}]}, "illisible"),
        ({"components": [{"type": "moteur"}, {"type": "moteur"}]}, "illisible"),
        (
            {
                "components": [{"type": "moteur"}],
                "wires": [["moteur", "entrée", "fusible", "1"]],
            },
            "illisible",
        ),
        ({"components": [{"type": "moteur"}] * 17}, "trop grand"),
    ],
)
def test_unreadable_answers_are_refused(pResponse, pMessage):
    """Vérifie le refus d'une réponse vide, illisible ou démesurée."""

    with pytest.raises(ValueError, match=pMessage):
        read_answer(pResponse)


@pytest.mark.parametrize(
    ("pText", "pMessage"),
    [
        ("", "au moins un composant"),
        ("{pas du json", "illisible"),
        ("x" * 20_001, "trop grand"),
    ],
)
def test_web_schema_text_is_parsed_safely(pText, pMessage):
    """Vérifie la lecture du schéma envoyé en JSON par le navigateur."""

    with pytest.raises(ValueError, match=pMessage):
        build_response(MOTOR_FEEDER, None, pText, [])


def test_expected_schema_is_drawn_with_wires_and_labels():
    """Vérifie le dessin du schéma attendu et le tracé des fils."""

    vSvg = render_expected(MOTOR_FEEDER)

    assert vSvg.startswith("<svg") and "<title>Schéma attendu</title>" in vSvg
    assert vSvg.count("<path") >= len(MOTOR_FEEDER["connections"])
    assert ">Relais thermique</text>" in vSvg
    assert route_wire(((10, 100), 1), ((10, 150), -1), 0) == "M10,100 V150"
    assert route_wire(((10, 100), 1), ((250, 50), -1), 200, 1).startswith(
        "M10,100 V119"
    )
    assert wrap_label("Contact de puissance du contacteur") == [
        "Contact de",
        "puissance du",
        "contacteur",
    ]


def test_network_devices_accept_either_terminal():
    """Vérifie qu'un équipement réseau se câble indifféremment en haut ou en bas."""

    vMissing, vExtra = compare_edges(
        [["poste", "bas", "switch", "haut"]],
        [("switch", "bas", "poste", "haut")],
        {"poste", "switch"},
    )

    assert not vMissing and not vExtra


def test_facing_terminals_are_joined_by_a_short_bend():
    """Vérifie le coude direct entre deux bornes proches et face à face."""

    assert route_wire(((100, 320), -1), ((60, 270), 1), 30) == "M100,320 V295 H60 V270"
