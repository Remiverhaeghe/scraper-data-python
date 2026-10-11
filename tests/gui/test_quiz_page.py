"""Tests de la page de révision"""

from gui.quiz_page import QuizPage
from storage.database import initialize_database


def create_page(pDatabaseFile):
    """Crée la page de révision sur une base vide."""

    initialize_database(pDatabaseFile)

    rPage = QuizPage(pDatabaseFile)
    rPage.refresh()

    return rPage


def test_question_answer_and_review(qt_application, tmp_path):
    """Vérifie une question, sa correction, puis la question ratée proposée à revoir."""

    vPage = create_page(tmp_path / "scraper.db")

    assert vPage.themes_grid.count() >= 6

    vPage.start("sql", "discover")
    vPage.validate()

    assert vPage.verdict_label.text() == "Choisissez une réponse."

    vWrong = next(
        vButton
        for vButton in vPage.choices_group.buttons()
        if vPage.choices_group.id(vButton) != vPage.question["answer"]
    )
    vWrong.setChecked(True)
    vQuestionId = vPage.question["id"]
    vPage.validate()

    assert vPage.verdict_label.text().startswith("Réponse incorrecte.")
    assert vPage.explanation_label.text() == vPage.question["explanation"]
    assert not vPage.next_button.isHidden()

    vPage.start("sql", "review")

    assert vPage.question["id"] == vQuestionId

    vPage.choices_group.button(vPage.question["answer"]).setChecked(True)
    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."

    vPage.start("sql", "review")

    assert vPage.question is None
    assert vPage.validate_button.isHidden()
