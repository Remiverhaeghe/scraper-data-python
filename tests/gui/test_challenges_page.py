"""Tests de la page des défis"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

import gui.challenges_page as challenges_page
import gui.puzzles_card as puzzles_card
from gui.challenges_page import ChallengesPage, format_stars
from job.challenges import CHALLENGES, get_expected_answers, get_seed
from job.code_puzzles import SERIES_LENGTH
from storage.database import initialize_database


def create_page(pDatabaseFile):
    """Crée la page des défis sur une base vide."""

    initialize_database(pDatabaseFile)

    rPage = ChallengesPage(pDatabaseFile)
    rPage.refresh()

    return rPage


def test_format_stars():
    """Vérifie l'affichage des étoiles d'un défi."""

    assert format_stars(0) == "☆☆"
    assert format_stars(1) == "★☆"
    assert format_stars(2) == "★★"


def test_challenge_is_opened_and_solved(qt_application, tmp_path):
    """Vérifie l'ouverture d'un défi, un indice, une erreur puis une réussite."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)

    assert len(vPage.challenge_buttons) == len(CHALLENGES)
    assert vPage.detail_card.isHidden()

    vPage.open_challenge("tampon-production")

    assert not vPage.detail_card.isHidden()
    assert "Partie 1" in vPage.statement_label.text()
    assert "Partie 2" not in vPage.statement_label.text()

    vPage.show_next_hint()

    assert vPage.hints_label.text().startswith("Indice 1 :")

    vPage.answer_edit.setText("-1")
    vPage.submit()

    assert vPage.answer_message.text().startswith("Ce n'est pas la bonne réponse.")

    vPage.answer_edit.setText("")
    vPage.submit()

    assert vPage.answer_message.text() == "Saisissez une réponse."

    vPage.answer_edit.setText("1")
    vPage.submit()

    assert vPage.answer_message.text().startswith("Patientez encore")


def test_input_is_copied_and_saved(qt_application, tmp_path, monkeypatch):
    """Vérifie la copie et l'enregistrement des données personnelles."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    vPage.open_challenge("engrenages")

    vPage.copy_input()

    assert challenges_page.QApplication.clipboard().text().count("\n") > 10

    vTarget = tmp_path / "engrenages.txt"
    monkeypatch.setattr(
        challenges_page.QFileDialog,
        "getSaveFileName",
        lambda *pArgs, **pKwargs: (str(vTarget), ""),
    )
    vPage.choose_input_file()

    assert vTarget.read_text(encoding="utf-8") == (
        challenges_page.QApplication.clipboard().text()
    )

    vPage.save_input(tmp_path / "absent" / "x.txt")

    assert vPage.answer_message.text() == "Les données n'ont pas pu être enregistrées."


def test_full_solution_shows_the_note(qt_application, tmp_path):
    """Vérifie qu'un défi terminé verrouille la réponse et montre la solution."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    vPage.open_challenge("pieces-bonnes")
    vAnswers = get_expected_answers(
        "pieces-bonnes", get_seed(vDatabaseFile, "pieces-bonnes", datetime.now())
    )

    for vAnswer in vAnswers:
        vPage.answer_edit.setText(vAnswer)
        vPage.submit()

    assert vPage.answer_message.text().startswith("Bonne réponse : défi terminé")
    assert not vPage.answer_edit.isEnabled()
    assert "Solution commentée" in vPage.note_label.text()
    assert vPage.challenge_buttons["pieces-bonnes"].badge_label.text() == "★★"
    assert vPage.challenge_buttons["pieces-bonnes"].done

    vPage.submit()

    assert vPage.answer_message.text().startswith("Bonne réponse : défi terminé")


def test_code_puzzles_series_is_played(qt_application, tmp_path, monkeypatch):
    """Vérifie une série de puzzles : réponse vide refusée, réponses justes, bilan."""

    vPage = create_page(tmp_path / "scraper.db")
    vCard = vPage.puzzles

    vCard.start()

    # Une remise en ordre a toujours une réponse : le cas vide est simulé.
    with monkeypatch.context() as vPatch:
        vPatch.setattr(puzzles_card, "read_response", lambda *pArgs: None)
        vCard.submit()

    assert vCard.message_label.text() == "Répondez avant de valider."

    for _ in range(SERIES_LENGTH):
        vPuzzle = vCard.puzzle

        if vPuzzle["type"] == "ordre":
            vList = vCard.widgets[0]
            vItems = sorted(
                (vList.takeItem(0) for _ in range(vList.count())),
                key=lambda pItem: pItem.data(Qt.ItemDataRole.UserRole),
            )

            for vItem in vItems:
                vList.addItem(vItem)
        elif vPuzzle["type"] == "saisie":
            vCard.widgets[0].setText(vPuzzle["accepted"][0])
        else:
            vCard.group.button(vPuzzle["line"] - 1).setChecked(True)

        vCard.submit()
        vTexts = [vLabel.text() for vLabel in vCard.card.findChildren(QLabel)]

        assert any(vText.startswith("Bonne réponse") for vText in vTexts)

        if vCard.puzzle is not None:
            vCard.refresh()

    vTexts = [vLabel.text() for vLabel in vCard.card.findChildren(QLabel)]

    assert "Bilan de la série : 10 sur 10" in vTexts
    assert "réponses justes d'affilée : 10" in vCard.status_label.text()
