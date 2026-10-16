"""Tests des schémas à construire : bibliothèque, vérification, correction et dessin"""

import random

import pytest

from job.quiz_types import (
    build_response,
    check_typed_fields,
    grade_answer,
    prepare_question,
)
from job.schema_building import get_labels, get_palette_limits, read_answer
from job.schema_drawing import (
    render_correction,
    render_expected,
    route_wire,
    wrap_label,
)
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
            "même identifiant",
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


def small_question(pTypes, pConnections, **pExtra):
    """Construit une question de schéma réduite à quelques composants."""

    rQuestion = {
        **MOTOR_FEEDER,
        "components": [
            {"type": vType, "x": 0, "y": vIndex} for vIndex, vType in enumerate(pTypes)
        ],
        "connections": pConnections,
        "distractors": [],
        **pExtra,
    }

    return rQuestion


def test_non_symmetric_parts_keep_their_terminals():
    """Vérifie qu'un vérin double effet branché à l'envers est refusé."""

    vQuestion = small_question(
        ["distributeur_52", "verin_double"],
        [["distributeur_52", "4", "verin_double", "fond"]],
    )
    vResponse = answer(
        ["distributeur_52", "verin_double"],
        [["distributeur_52", "4", "verin_double", "tige"]],
    )

    assert not grade_answer(vQuestion, vResponse)[0]


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

    vQuestion = small_question(
        ["poste", "switch"], [["poste", "bas", "switch", "haut"]]
    )
    vResponse = answer(["poste", "switch"], [["switch", "bas", "poste", "haut"]])

    assert grade_answer(vQuestion, vResponse)[0]


def test_facing_terminals_are_joined_by_a_short_bend():
    """Vérifie le coude direct entre deux bornes proches et face à face."""

    assert route_wire(((100, 320), -1), ((60, 270), 1), 30) == "M100,320 V295 H60 V270"


def test_correction_draws_both_schemas_and_marks_wrong_wires():
    """Vérifie la correction : schéma construit à côté de l'attendu, fil faux en rouge."""

    vResponse = answer(
        EXPECTED_TYPES,
        [
            ["reseau", "sortie", "sectionneur", "1"],
            ["reseau", "sortie", "moteur", "entrée"],
        ],
    )
    vResponse["components"][0]["x"] = 500

    vSvg = render_correction(MOTOR_FEEDER, vResponse)

    assert ">Votre schéma</text>" in vSvg and ">Schéma attendu</text>" in vSvg
    assert vSvg.count('stroke="#dc2626"') == 1
    assert read_answer(vResponse)[1]["reseau"] == (9, 0)


TWO_CYLINDERS = {
    **MOTOR_FEEDER,
    "id": "deux-verins",
    "components": [
        {"type": "frl", "x": 0, "y": 0},
        {"id": "d1", "type": "distributeur_52", "x": 1, "y": 1},
        {"id": "d2", "type": "distributeur_52", "x": 2, "y": 1},
        {
            "id": "v1",
            "type": "verin_double",
            "x": 1,
            "y": 0,
            "label": "Vérin de serrage",
        },
        {"id": "v2", "type": "verin_double", "x": 2, "y": 0},
    ],
    "connections": [
        ["frl", "2", "d1", "1"],
        ["frl", "2", "d2", "1"],
        ["d1", "4", "v1", "fond"],
        ["d1", "2", "v1", "tige"],
        ["d2", "4", "v2", "fond"],
        ["d2", "2", "v2", "tige"],
    ],
    "distractors": ["verin_simple"],
}


def two_cylinders_answer(pWires):
    """Construit une réponse aux identifiants choisis par l'éditeur."""

    rAnswer = {
        "components": [
            {"id": vId, "type": vType, "x": 0, "y": vIndex}
            for vIndex, (vId, vType) in enumerate(
                (
                    ("frl", "frl"),
                    ("distributeur_52-1", "distributeur_52"),
                    ("distributeur_52-2", "distributeur_52"),
                    ("verin_double-1", "verin_double"),
                    ("verin_double-2", "verin_double"),
                )
            )
        ],
        "wires": pWires,
    }

    return rAnswer


def test_identical_components_are_matched_whatever_their_numbers():
    """Vérifie qu'un schéma juste est reconnu, quels que soient les numéros choisis."""

    assert check_typed_fields(TWO_CYLINDERS) == ""
    assert get_palette_limits(TWO_CYLINDERS) == {
        "frl": 1,
        "distributeur_52": 2,
        "verin_double": 2,
        "verin_simple": 1,
    }

    vResponse = two_cylinders_answer(
        [
            ["frl", "2", "distributeur_52-2", "1"],
            ["frl", "2", "distributeur_52-1", "1"],
            ["distributeur_52-2", "4", "verin_double-1", "fond"],
            ["distributeur_52-2", "2", "verin_double-1", "tige"],
            ["distributeur_52-1", "4", "verin_double-2", "fond"],
            ["distributeur_52-1", "2", "verin_double-2", "tige"],
        ]
    )

    assert grade_answer(TWO_CYLINDERS, vResponse) == (
        True,
        "Schéma conforme",
        "Unité FRL (2) – Distributeur 5/2 1 (1) ; Unité FRL (2) – Distributeur 5/2 2 (1)"
        " ; Distributeur 5/2 1 (4) – Vérin de serrage (fond) ; Distributeur 5/2 1 (2)"
        " – Vérin de serrage (tige) ; Distributeur 5/2 2 (4) – Vérin double effet 2"
        " (fond) ; Distributeur 5/2 2 (2) – Vérin double effet 2 (tige)",
    )


def test_wrong_wiring_of_identical_components_is_named_clearly():
    """Vérifie l'écart nommé quand un distributeur pilote les deux vérins."""

    vResponse = two_cylinders_answer(
        [
            ["frl", "2", "distributeur_52-1", "1"],
            ["distributeur_52-1", "4", "verin_double-1", "fond"],
            ["distributeur_52-1", "2", "verin_double-1", "tige"],
            ["distributeur_52-1", "4", "verin_double-2", "fond"],
            ["distributeur_52-1", "2", "verin_double-2", "tige"],
        ]
    )

    vCorrect, vChosen, _ = grade_answer(TWO_CYLINDERS, vResponse)
    vSvg = render_correction(TWO_CYLINDERS, vResponse)

    assert not vCorrect
    assert "liaisons manquantes : Distributeur 5/2 2 (1) – Unité FRL (2)" in vChosen
    assert "liaisons en trop : Distributeur 5/2 1 (2) –" in vChosen
    assert vSvg.count('stroke="#dc2626"') == 2
    assert ">Vérin de serrage</text>" in vSvg


def test_palette_limits_and_identifiers_are_enforced():
    """Vérifie le plafond d'exemplaires, les identifiants et les noms affichés."""

    vResponse = two_cylinders_answer([])
    vResponse["components"].append({"id": "x", "type": "verin_double"})

    with pytest.raises(ValueError, match="Trop de composants : Vérin double effet"):
        read_answer(vResponse, get_palette_limits(TWO_CYLINDERS))

    vResponse["components"][-1] = {"id": "Pas Valide", "type": "frl"}

    with pytest.raises(ValueError, match="illisible"):
        read_answer(vResponse)

    assert get_labels(TWO_CYLINDERS["components"])["v2"] == "Vérin double effet 2"
    assert get_labels(MOTOR_FEEDER["components"])["fusible"] == "Fusible"


@pytest.mark.parametrize(
    ("pChange", "pMessage"),
    [
        (
            {
                "components": TWO_CYLINDERS["components"][:4]
                + [{"id": "v1", "type": "verin_double", "x": 3, "y": 3}]
            },
            "même identifiant",
        ),
        (
            {
                "components": [
                    {"id": f"f{vIndex}", "type": "fusible", "x": vIndex, "y": 0}
                    for vIndex in range(7)
                ],
                "connections": [["f0", "1", "f1", "1"]],
            },
            "trop de composants identiques",
        ),
        (
            {
                "components": TWO_CYLINDERS["components"][:4]
                + [{"id": "v2", "type": "verin_double", "x": 3, "y": 3, "label": " "}]
            },
            "composants",
        ),
    ],
)
def test_malformed_identical_components_are_refused(pChange, pMessage):
    """Vérifie le refus d'identifiants en double, d'un calcul démesuré ou d'un nom vide."""

    assert pMessage in check_typed_fields({**TWO_CYLINDERS, **pChange})
