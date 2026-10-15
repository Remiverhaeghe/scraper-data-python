"""Tests des types de questions : vérification, présentation et correction"""

import json
import random
from datetime import datetime

import pytest

from job.mobile_sync import build_quiz_package, check_synced_answer
from job.quiz import answer_question, check_question, find_question, load_active_quiz
from job.quiz_exam import answer_exam, load_exam, start_exam
from job.quiz_generation import assess_questions
from job.quiz_import import import_questions
from job.quiz_types import (
    build_response,
    check_typed_fields,
    format_number,
    grade_answer,
    parse_number,
    prepare_question,
)
from storage.database import initialize_database
from storage.quiz_answers import get_last_answers

NOW = datetime(2026, 10, 15, 10, 0)

NUMERIC = {
    "id": "ohm-courant",
    "level": "débutant",
    "type": "numerique",
    "question": "Courant dans 100 Ω sous 0,23 V ?",
    "value": 0.0023,
    "unit": "A",
    "tolerance": 2,
    "explanation": "I = U / R = 0,23 / 100 = 2,3 mA.",
}
ORDER = {
    "id": "consignation-ordre",
    "level": "intermédiaire",
    "type": "ordre",
    "question": "Remettre la consignation dans l'ordre.",
    "items": ["Séparer", "Condamner", "Identifier", "Vérifier l'absence de tension"],
    "explanation": "Séparer, condamner, identifier, puis vérifier.",
}
PAIRS = {
    "id": "grandeurs-unites",
    "level": "débutant",
    "type": "association",
    "question": "Associer chaque grandeur à son unité.",
    "pairs": [["Tension", "V"], ["Courant", "A"], ["Puissance", "W"]],
    "explanation": "Volt, ampère, watt.",
}
COMPLETION = {
    "id": "java-boucle",
    "level": "débutant",
    "type": "saisie",
    "question": "Compléter la boucle pour parcourir le tableau.",
    "code": "for (int i = 0; i < tab.____; i++) {}",
    "accepted": ["length"],
    "explanation": "Un tableau Java expose sa taille par length.",
}
QCM = {
    "id": "unite-tension",
    "level": "débutant",
    "question": "Unité de la tension ?",
    "choices": ["Volt", "Ampère"],
    "answer": 0,
    "explanation": "La tension se mesure en volts.",
}


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec une question de chaque type."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)

    vReport = import_questions(
        rDatabaseFile,
        "",
        json.dumps(
            {
                "theme": "Électricité",
                "questions": [NUMERIC, ORDER, PAIRS, COMPLETION, QCM],
            }
        ),
        NOW,
    )

    assert vReport["added"] == 5, vReport["rejected"]

    return rDatabaseFile


@pytest.mark.parametrize("pQuestion", [NUMERIC, ORDER, PAIRS, COMPLETION, QCM])
def test_valid_questions_pass_the_checks(pQuestion):
    """Vérifie qu'une question bien formée de chaque type est acceptée."""

    assert check_typed_fields(pQuestion) == ""
    check_question(pQuestion, "test.json")


@pytest.mark.parametrize(
    ("pQuestion", "pMessage"),
    [
        ({**QCM, "type": "ouverte"}, "type inconnu"),
        ({**NUMERIC, "value": "2,3"}, "valeur numérique attendue"),
        ({**NUMERIC, "value": True}, "valeur numérique attendue"),
        ({**NUMERIC, "unit": "m A"}, "unité invalide"),
        ({**NUMERIC, "tolerance": 50}, "tolérance attendue"),
        ({**ORDER, "items": ["A", "A", "B"]}, "éléments distincts"),
        ({**PAIRS, "pairs": [["A", "1"], ["B"], ["C", "3"]]}, "paires"),
        (
            {**PAIRS, "pairs": [["A", "1"], ["B", "1"], ["C", "3"]]},
            "même correspondance",
        ),
        ({**COMPLETION, "code": "sans trou"}, "un seul trou"),
        ({**COMPLETION, "accepted": []}, "réponses acceptées"),
        ({key: value for key, value in ORDER.items() if key != "items"}, "manquant"),
        ({**QCM, "answer": True}, "réponse hors des choix"),
    ],
)
def test_malformed_questions_are_refused(pQuestion, pMessage):
    """Vérifie le refus explicite d'une question mal formée."""

    with pytest.raises(ValueError, match=pMessage):
        check_question(pQuestion, "test.json")


@pytest.mark.parametrize(
    ("pText", "pUnit", "pValue"),
    [
        ("2,3", "A", 2.3),
        ("2.3 A", "A", 2.3),
        ("2,3 mA", "A", 0.0023),
        ("4,7kΩ", "Ω", 4700.0),
        ("1e-3", "", 0.001),
        ("10 µF", "F", 1e-5),
        ("10 uF", "F", 1e-5),
    ],
)
def test_parse_number_reads_units_and_prefixes(pText, pUnit, pValue):
    """Vérifie la lecture d'une valeur, avec virgule, unité ou préfixe."""

    assert parse_number(pText, pUnit) == pytest.approx(pValue)


@pytest.mark.parametrize(
    ("pText", "pUnit", "pMessage"),
    [
        ("deux", "A", "Nombre attendu, par exemple 2,5 A"),
        ("2,3 V", "A", "Unité attendue : A"),
        ("2,3 A", "", "Nombre sans unité"),
    ],
)
def test_parse_number_refuses_unreadable_values(pText, pUnit, pMessage):
    """Vérifie le refus d'une valeur illisible ou d'une autre unité."""

    with pytest.raises(ValueError, match=pMessage):
        parse_number(pText, pUnit)


def test_grade_answer_for_each_type():
    """Vérifie la correction de chaque type et le texte des réponses affichées."""

    assert grade_answer(NUMERIC, "2,3 mA") == (True, "2,3 mA", "0,0023 A")
    assert grade_answer(NUMERIC, "2,4 mA")[0] is False
    assert grade_answer(ORDER, [0, 1, 2, 3])[0]
    assert grade_answer(ORDER, [1, 0, 2, 3])[1] == (
        "Condamner → Séparer → Identifier → Vérifier l'absence de tension"
    )
    assert grade_answer(PAIRS, [0, 1, 2]) == (
        True,
        "Tension → V ; Courant → A ; Puissance → W",
        "Tension → V ; Courant → A ; Puissance → W",
    )
    assert grade_answer(PAIRS, [1, 0, 2])[0] is False
    assert grade_answer(COMPLETION, "  length ") == (True, "length", "length")
    assert grade_answer(COMPLETION, "Length")[0] is False
    assert grade_answer(QCM, 1) == (False, "Ampère", "Volt")
    assert format_number(4700.0) == "4700" and format_number(0.5) == "0,5"


@pytest.mark.parametrize(
    ("pQuestion", "pResponse", "pMessage"),
    [
        (ORDER, [0, 0, 1, 2], "sa propre place"),
        (ORDER, [0, 1], "Réponse incomplète"),
        (PAIRS, [0, 1, 7], "Réponse incomplète"),
        (PAIRS, "0,1,2", "Réponse incomplète"),
        (COMPLETION, "  ", "Saisissez une réponse"),
        (QCM, None, "Question ou réponse inconnue"),
        (QCM, 5, "Question ou réponse inconnue"),
    ],
)
def test_grade_answer_refuses_unreadable_responses(pQuestion, pResponse, pMessage):
    """Vérifie le refus d'une réponse incomplète ou hors limites."""

    with pytest.raises(ValueError, match=pMessage):
        grade_answer(pQuestion, pResponse)


def test_prepare_question_shuffles_and_never_shows_the_order_solved():
    """Vérifie le mélange gardant les indices et un ordre jamais déjà résolu."""

    for vSeed in range(30):
        vOrder = prepare_question(ORDER, random.Random(vSeed))["shuffled"]

        assert [vIndex for vIndex, _ in vOrder] != [0, 1, 2, 3]
        assert sorted(vOrder) == list(enumerate(ORDER["items"]))

    vPairs = prepare_question(PAIRS, random.Random(1))

    assert sorted(vPairs["shuffled"]) == [(0, "V"), (1, "A"), (2, "W")]
    assert vPairs["type_label"] == "Association"
    assert prepare_question(NUMERIC, random.Random(1))["shuffled"] == []
    assert prepare_question(QCM, random.Random(1))["type"] == "qcm"


def test_build_response_picks_the_field_of_the_type():
    """Vérifie le choix du champ de formulaire selon le type."""

    assert build_response(QCM, 1, "", []) == 1
    assert build_response(NUMERIC, None, "2,3", []) == "2,3"
    assert build_response(COMPLETION, None, "length", []) == "length"
    assert build_response(ORDER, None, "", [2, 1, 0, 3]) == [2, 1, 0, 3]


def test_typed_questions_are_imported_answered_and_kept_off_mobile(database_file):
    """Vérifie l'import, une réponse illisible non comptée et le contenu mobile."""

    vQuiz = load_active_quiz(database_file)

    with pytest.raises(ValueError, match="Unité attendue"):
        answer_question(database_file, vQuiz, "ohm-courant", "2,3 V", NOW)

    assert "ohm-courant" not in get_last_answers(database_file)

    vResult = answer_question(database_file, vQuiz, "ohm-courant", "2,3 mA", NOW)

    assert vResult["correct"] and vResult["answer"] == "0,0023 A"

    vMobileIds = {
        vQuestion["id"]
        for vQuestion in build_quiz_package(database_file, NOW)["questions"]
    }

    assert "unite-tension" in vMobileIds
    assert not vMobileIds & {"ohm-courant", "consignation-ordre", "java-boucle"}

    with pytest.raises(ValueError, match="question inconnue"):
        check_synced_answer(
            vQuiz,
            {
                "id": "a" * 16,
                "question_id": "ohm-courant",
                "choice": 0,
                "answered_at": NOW.isoformat(),
            },
            NOW,
        )


def test_exam_keeps_the_question_after_an_unreadable_response(database_file):
    """Vérifie qu'une réponse illisible à l'examen ne fait pas avancer."""

    vQuiz = load_active_quiz(database_file)
    start_exam(database_file, vQuiz, None, NOW)
    vQuestion = find_question(vQuiz, load_exam(database_file)["ids"][0])[0]

    with pytest.raises(ValueError):
        answer_exam(database_file, vQuiz, build_response(vQuestion, 9, " ", [9]), NOW)

    assert load_exam(database_file)["index"] == 0


def test_quality_measures_skip_interactive_questions():
    """Vérifie qu'un lot sans QCM est mesuré sans erreur ni fausse alerte."""

    vQuality = assess_questions([NUMERIC, ORDER, PAIRS, COMPLETION])

    assert vQuality["summary"] == "4 question(s) interactive(s), sans choix à mesurer"
    assert vQuality["warnings"] == []
