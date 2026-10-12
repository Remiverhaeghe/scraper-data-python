"""Tests de la page de révision"""

import json

import gui.quiz_page as quiz_page
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


QUESTIONS_JSON = json.dumps(
    {
        "theme": "Kafka",
        "questions": [
            {
                "id": "kafka-topic",
                "level": "débutant",
                "question": "Qu'est-ce qu'un topic ?",
                "choices": ["Un flux de messages", "Une table"],
                "answer": 0,
                "explanation": "Un topic regroupe des messages.",
            }
        ],
    }
)


def test_questions_are_generated_imported_and_flagged(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la demande ChatGPT, l'import collé et le signalement d'une question."""

    vPage = create_page(tmp_path / "scraper.db")
    vOpened = []
    monkeypatch.setattr(quiz_page.QDesktopServices, "openUrl", vOpened.append)

    vPage.theme_combo.setCurrentText("")
    vPage.copy_generation_prompt()

    assert vPage.import_message.text() == "Choisissez ou saisissez un thème."

    vPage.theme_combo.setCurrentText("Kafka")
    vPage.copy_generation_prompt()

    assert "« Kafka »" in quiz_page.QApplication.clipboard().text()
    assert len(vOpened) == 1

    vPage.import_edit.setPlainText(QUESTIONS_JSON)
    vPage.import_pasted_questions()

    assert vPage.import_message.text() == "1 question(s) ajoutée(s) : Kafka."
    assert vPage.import_edit.toPlainText() == ""
    assert vPage.theme_combo.findText("Kafka") >= 0

    monkeypatch.setattr(
        quiz_page.QMessageBox,
        "question",
        lambda *pArgs: quiz_page.QMessageBox.StandardButton.Yes,
    )
    vPage.start("kafka", "discover")
    vPage.flag_button.click()

    assert vPage.question is None
    assert vPage.flag_button.isHidden()


def test_questions_file_import_and_errors(qt_application, tmp_path, monkeypatch):
    """Vérifie l'import d'un fichier et le message d'un texte illisible."""

    vPage = create_page(tmp_path / "scraper.db")
    vFile = tmp_path / "kafka.json"
    vFile.write_text(QUESTIONS_JSON, encoding="utf-8")

    vPage.import_pasted_questions()

    assert vPage.import_message.text().startswith("Aucune question")

    monkeypatch.setattr(
        quiz_page.QFileDialog, "getOpenFileName", lambda *pArgs: (str(vFile), "")
    )
    vPage.choose_questions_file()

    assert vPage.import_message.text() == "1 question(s) ajoutée(s) : Kafka."

    def fail():
        raise OSError("disque")

    vPage.run_import(fail)

    assert vPage.import_message.text() == "L'import a échoué. Voir les journaux."
