"""Tests des questions pièges selon le type d'employeur"""

from job.tricky_questions import (
    TRICKY_QUESTIONS,
    build_tricky_questions,
    get_employer_kind,
)


def test_employer_kind_follows_agencies_and_consulting_firms():
    """Vérifie le type : agence de la liste, ESN connue, sinon client final."""

    assert get_employer_kind({"company": "Proman"}, ["proman"]) == "agency"
    assert get_employer_kind({"company": "Capgemini"}) == "consulting"
    assert get_employer_kind({"company": "Decathlon"}) == "final"


def test_tricky_questions_match_the_employer():
    """Vérifie les questions d'une ESN, chacune avec son conseil."""

    vTricky = build_tricky_questions({"company": "Capgemini"})

    assert vTricky["employer"] == "Société de conseil (ESN)"
    assert vTricky["questions"][1]["question"] == "Que feriez-vous en intercontrat ?"
    assert all(vItem["hint"] for vItem in vTricky["questions"])
    assert all(len(vQuestions) == 5 for vQuestions in TRICKY_QUESTIONS.values())
