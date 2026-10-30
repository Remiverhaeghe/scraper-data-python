"""Tests de la page de révision"""

import json
import random
from datetime import datetime

import pandas as pd

import pytest

from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

import gui.quiz_import_panel as quiz_import_panel
import gui.quiz_page as quiz_page
import job.quiz_packs as quiz_packs
from gui.quiz_page import QuizPage
from job.quiz_generation import MIN_QUALITY_SAMPLE
from job.quiz_import import import_questions, import_questions_file
from job.quiz_types import prepare_question
from storage.database import initialize_database
from storage.job_offers import save_offers
from job.self_assessment import save_skill_levels
from tests.job.test_quiz_generation import build_lot_text, build_question
from tests.job.test_quiz_import import build_pack
from tests.job.test_quiz_types import COMPLETION, NUMERIC, ORDER, PAIRS
from tools.quiz_lot import build_pack as build_lot_pack


def create_page(pDatabaseFile):
    """Crée la page de révision sur une base vide."""

    initialize_database(pDatabaseFile)

    rPage = QuizPage(pDatabaseFile)
    rPage.refresh()

    return rPage


def test_question_answer_and_review(qt_application, tmp_path):
    """Vérifie une question, sa correction, puis la question ratée proposée à revoir."""

    vPage = create_page(tmp_path / "scraper.db")

    assert len(vPage.themes) >= 6
    assert vPage.category_buttons[(None, None)].isChecked()

    vPage.start("sql", "discover")
    vPage.validate()

    assert vPage.verdict_label.text() == "Complétez votre réponse."

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
    monkeypatch.setattr(quiz_import_panel.QDesktopServices, "openUrl", vOpened.append)

    vPage.import_panel.theme_combo.setCurrentText("")
    vPage.import_panel.copy_generation_prompt()

    assert (
        vPage.import_panel.import_message.text() == "Choisissez ou saisissez un thème."
    )

    vPage.import_panel.theme_combo.setCurrentText("Kafka")
    vPage.import_panel.copy_generation_prompt()

    assert "Thème : Kafka. Lot n° 1.\n100 questions" in (
        quiz_import_panel.QApplication.clipboard().text()
    )
    assert len(vOpened) == 1

    vPage.import_panel.import_edit.setPlainText(QUESTIONS_JSON)
    vPage.import_panel.import_pasted_questions()

    assert (
        vPage.import_panel.import_message.text() == "1 question(s) ajoutée(s) : Kafka."
    )
    assert vPage.import_panel.import_edit.toPlainText() == ""
    assert vPage.import_panel.theme_combo.findText("Kafka") >= 0

    monkeypatch.setattr(
        quiz_page.QMessageBox,
        "question",
        lambda *pArgs: quiz_page.QMessageBox.StandardButton.Yes,
    )
    vPage.start("kafka", "discover")
    vPage.flag_button.click()

    assert vPage.question is None
    assert vPage.flag_button.isHidden()
    assert not vPage.flagged_card.isHidden()
    assert vPage.flagged_card.tree.topLevelItemCount() == 1
    assert not vPage.flagged_card.restore_button.isEnabled()

    vPage.flagged_card.tree.topLevelItem(0).setSelected(True)
    vPage.flagged_card.restore_button.click()

    assert vPage.flagged_card.isHidden()
    assert vPage.flagged_card.message_label.text() == (
        "1 question(s) remise(s) dans les tirages."
    )


def test_questions_file_import_and_errors(qt_application, tmp_path, monkeypatch):
    """Vérifie l'import d'un fichier et le message d'un texte illisible."""

    vPage = create_page(tmp_path / "scraper.db")
    vFile = tmp_path / "kafka.json"
    vFile.write_text(QUESTIONS_JSON, encoding="utf-8")

    vPage.import_panel.import_pasted_questions()

    assert vPage.import_panel.import_message.text().startswith("Aucune question")

    monkeypatch.setattr(
        quiz_import_panel.QFileDialog,
        "getOpenFileName",
        lambda *pArgs: (str(vFile), ""),
    )
    vPage.import_panel.choose_questions_file()

    assert (
        vPage.import_panel.import_message.text() == "1 question(s) ajoutée(s) : Kafka."
    )

    def fail():
        raise OSError("disque")

    vPage.import_panel.run_import(fail)

    assert (
        vPage.import_panel.import_message.text()
        == "L'import a échoué. Voir les journaux."
    )


def test_pack_question_shows_visual_references_and_guide(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie le schéma et les liens après la réponse, et l'ouverture d'un guide."""

    vPage = create_page(tmp_path / "scraper.db")
    vPack = tmp_path / "pack.zip"
    vPack.write_bytes(build_pack())
    vOpened = []

    monkeypatch.setattr(
        quiz_import_panel.QFileDialog,
        "getOpenFileName",
        lambda *pArgs: (str(vPack), ""),
    )
    monkeypatch.setattr(
        quiz_page,
        "show_text_dialog",
        lambda *pArgs, **pKwargs: vOpened.append(pKwargs),
    )
    vPage.import_panel.choose_questions_file()

    assert not vPage.guides_card.isHidden()

    vPage.start("ram-jvm", "discover")

    while vPage.question["id"] != "ram-jvm-001":
        vPage.start("ram-jvm", "discover")

    next(
        vButton
        for vButton in vPage.choices_group.buttons()
        if vPage.choices_group.id(vButton) == 0
    ).setChecked(True)
    vPage.validate()

    assert not vPage.visual_widget.isHidden()
    assert vPage.visual_widget.height() == quiz_page.VISUAL_HEIGHT
    assert "docs.oracle.com" in vPage.references_label.text()

    vPage.show_guide("ram-jvm-analyse")
    vPage.show_guide("absent")

    assert len(vOpened) == 1
    assert "<li>Heap</li>" in vOpened[0]["pHtml"]


def test_questions_are_exported(qt_application, tmp_path, monkeypatch):
    """Vérifie l'export des questions importées et le message sans question."""

    vPage = create_page(tmp_path / "scraper.db")
    vExport = tmp_path / "export.zip"

    monkeypatch.setattr(
        quiz_import_panel.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vExport), ""),
    )
    vPage.import_panel.choose_export_file()

    assert (
        vPage.import_panel.import_message.text()
        == "Aucune question importée à exporter."
    )

    vPage.import_panel.import_edit.setPlainText(QUESTIONS_JSON)
    vPage.import_panel.import_pasted_questions()
    vPage.import_panel.choose_export_file()

    assert (
        vPage.import_panel.import_message.text()
        == "1 question(s) exportée(s) : export.zip"
    )
    assert vExport.exists()

    vPage.import_panel.export_questions(str(tmp_path / "absent" / "export.zip"))

    assert (
        vPage.import_panel.import_message.text()
        == "L'export a échoué. Voir les journaux."
    )


def test_domain_filter_zero_offers_and_scroll(qt_application, tmp_path):
    """Vérifie le filtre par domaine, la mention sans offre et la remontée en haut."""

    vPage = create_page(tmp_path / "scraper.db")
    vScroll = vPage.findChild(quiz_page.QScrollArea)

    assert vPage.category_buttons[(None, None)].text().startswith("Tous les thèmes")

    vPage.select_domain("Informatique")

    assert vPage.domain == "Informatique"

    vLabels = [
        vLabel.text()
        for vLabel in vPage.findChildren(quiz_page.QLabel)
        if vLabel.isVisibleTo(vPage)
    ]

    assert any(vText.startswith("Développement · ") for vText in vLabels)
    assert any("questions acquises" in vText for vText in vLabels)
    assert "Pas encore dans vos offres" in vLabels

    vScroll.verticalScrollBar().setMaximum(1000)
    vScroll.verticalScrollBar().setValue(500)
    vPage.start("sql", "discover")

    assert vScroll.verticalScrollBar().value() == 0


def test_exam_is_run_resumed_and_closed(qt_application, tmp_path, qcm_only_quiz):
    """Vérifie l'examen sur le bureau : questions, reprise, résultat et fermeture."""

    vPage = create_page(tmp_path / "scraper.db")
    vExamButton = vPage.exam_button

    assert vExamButton.text().startswith("Mode examen (20 questions)")

    vExamButton.click()

    assert vPage.meta_label.text().startswith("Examen · question 1 / 20")
    assert not vPage.stop_exam_button.isHidden()
    assert vPage.flag_button.isHidden()
    assert vPage.exam_timer.isActive()
    assert vPage.timer_label.text().startswith("Temps restant : ")

    vPage.refresh()
    vResume = vPage.exam_button

    assert vResume.text() == "Reprendre l'examen (1 / 20)"

    vResume.click()

    for _ in range(20):
        next(
            vButton
            for vButton in vPage.choices_group.buttons()
            if vPage.choices_group.id(vButton) == vPage.question["answer"]
        ).setChecked(True)
        vPage.validate()
        vPage.next_button.click()

    assert vPage.meta_label.text() == "Examen terminé"
    assert vPage.question_label.text().startswith("Note : 20 / 20 (100 %)")
    assert vPage.stop_exam_button.text() == "Fermer l'examen"
    assert not vPage.exam_timer.isActive()
    assert vPage.timer_label.isHidden()

    vPage.stop_exam_button.click()

    assert vPage.question_card.isHidden()
    assert quiz_page.load_exam(tmp_path / "scraper.db") is None


def test_exam_reports_empty_domain(qt_application, tmp_path):
    """Vérifie le message d'un examen demandé sur un domaine sans question."""

    vPage = create_page(tmp_path / "scraper.db")
    vPage.domain = "Autres"
    vPage.start_exam()

    assert vPage.message_label.text() == "Aucune question dans ce domaine."


def test_category_list_filters_and_toggles(qt_application, tmp_path):
    """Vérifie la liste des catégories : sous-domaines, filtre, second clic et titre."""

    vPage = create_page(tmp_path / "scraper.db")

    assert (
        vPage.category_buttons[("Informatique", "Données")]
        .text()
        .startswith("Données (")
    )

    vPage.category_buttons[("Informatique", "Données")].click()

    assert (vPage.domain, vPage.subdomain) == ("Informatique", "Données")
    assert vPage.filter_label.text() == "Informatique › Données"
    assert vPage.category_buttons[("Informatique", "Données")].isChecked()

    vTitles = {
        vLabel.text()
        for vLabel in vPage.findChildren(quiz_page.QLabel)
        if vLabel.isVisibleTo(vPage)
    }

    assert "SQL" in vTitles
    assert "Java" not in vTitles
    assert "Données · 1" in vTitles

    # Second clic sur la catégorie active : retour à l'ensemble des thèmes
    vPage.category_buttons[("Informatique", "Données")].click()

    assert (vPage.domain, vPage.subdomain) == (None, None)
    assert vPage.filter_label.text() == "Tous les thèmes"


@pytest.mark.parametrize("pConfirmed", [False, True])
def test_imported_questions_can_be_cleared(
    qt_application, tmp_path, monkeypatch, pConfirmed
):
    """Vérifie l'effacement des questions importées, seulement après confirmation."""

    vPage = create_page(tmp_path / "scraper.db")
    vPage.import_panel.import_edit.setPlainText(QUESTIONS_JSON)
    vPage.import_panel.import_pasted_questions()

    def fake_exec(pDialog):
        vButtons = {vButton.text(): vButton for vButton in pDialog.buttons()}
        pDialog.clickedButton = lambda: vButtons[
            "Supprimer" if pConfirmed else "Annuler"
        ]

    monkeypatch.setattr(quiz_page.QMessageBox, "exec", fake_exec)
    vPage.import_panel.confirm_clear_questions()

    vKeys = {vTheme["key"] for vTheme in vPage.themes}

    assert ("kafka" in vKeys) is not pConfirmed

    if pConfirmed:
        assert vPage.import_panel.import_message.text().startswith(
            "1 question(s) importée(s) effacée(s)"
        )

    def fail(*pArgs):
        raise OSError("disque plein")

    monkeypatch.setattr(quiz_import_panel, "clear_imported_questions", fail)
    vPage.import_panel.clear_questions()

    assert vPage.import_panel.import_message.text().startswith("L'effacement a échoué")


def test_biased_lot_offers_a_correction(qt_application, tmp_path, monkeypatch):
    """Vérifie le bilan orange d'un lot biaisé et la demande de correction copiée."""

    vPage = create_page(tmp_path / "scraper.db")
    vOpened = []
    monkeypatch.setattr(quiz_import_panel.QDesktopServices, "openUrl", vOpened.append)

    vPage.import_panel.import_edit.setPlainText(
        build_lot_text(
            [
                build_question(vIndex, pAnswer=1, pLongest=True)
                for vIndex in range(MIN_QUALITY_SAMPLE)
            ]
        )
    )
    vPage.import_panel.import_pasted_questions()

    assert "alerte(s) de qualité" in vPage.import_panel.import_message.text()
    assert not vPage.import_panel.correction_button.isHidden()

    vPage.import_panel.copy_correction_prompt()

    assert "Questions concernées : grafcet-l1-000" in (
        quiz_import_panel.QApplication.clipboard().text()
    )
    assert len(vOpened) == 1
    assert vPage.import_panel.import_message.text().startswith(
        "Demande de correction copiée"
    )


def test_validated_packs_are_imported_in_one_click(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie le bouton des lots validés : nombre affiché puis import groupé."""

    vFolder = tmp_path / "packs"
    vFolder.mkdir()
    monkeypatch.setattr(quiz_packs, "QUIZ_PACKS_DIRECTORY", str(vFolder))

    vPage = create_page(tmp_path / "scraper.db")

    assert vPage.import_panel.packs_button.isHidden()

    vName, vContent = build_lot_pack("grafcet")
    (vFolder / vName).write_bytes(vContent)
    vPage.refresh()

    assert vPage.import_panel.packs_button.text() == "Importer les lots validés (1)"
    assert not vPage.import_panel.packs_button.isHidden()

    vPage.import_panel.import_packs()

    assert vPage.import_panel.import_message.text().startswith(
        "100 question(s) ajoutée(s)"
    )


def test_priority_card_prepares_a_full_lot(qt_application, tmp_path, monkeypatch):
    """Vérifie la carte des priorités : message sans offre, puis demande préparée."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)

    assert vPage.import_panel.priority_message.text().startswith("Aucun thème")

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Dev",
                    "skills": ["SCADA"],
                }
            ]
        ),
        datetime(2026, 10, 15),
    )
    vPage.refresh()
    monkeypatch.setattr(quiz_import_panel.QDesktopServices, "openUrl", lambda _: None)

    assert vPage.import_panel.priority_message.text() == ""
    assert vPage.import_panel.priority_layout.count() == 3

    vPage.import_panel.prepare_priority("Supervision, SCADA et IHM")

    assert (
        "100 questions : 25 débutant"
        in quiz_import_panel.QApplication.clipboard().text()
    )


def test_typed_questions_are_answered_on_the_desktop(qt_application, tmp_path):
    """Vérifie les zones de réponse d'un calcul, d'un ordre, d'une association et d'un code."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    import_questions(
        vDatabaseFile,
        "",
        json.dumps(
            {"theme": "Électricité", "questions": [NUMERIC, ORDER, PAIRS, COMPLETION]}
        ),
        datetime.now(),
    )
    vPage.mode = "discover"

    def show(pQuestion):
        vPage.display_question(
            {**prepare_question(pQuestion, random.Random(1)), "theme_key": "x"},
            "Électricité",
            "",
        )

    show(NUMERIC)
    vPage.validate()

    assert vPage.verdict_label.text() == "Complétez votre réponse."

    vPage.answer_widgets[0].setText("2,3 V")
    vPage.validate()

    assert vPage.verdict_label.text().startswith("Unité attendue : A")

    vPage.answer_widgets[0].setText("2,3 mA")
    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."
    assert not vPage.answer_widgets[0].isEnabled()

    show(ORDER)
    vList = vPage.answer_widgets[0]
    vItems = [vList.takeItem(0) for _ in range(vList.count())]

    for vItem in sorted(
        vItems, key=lambda pItem: pItem.data(quiz_page.Qt.ItemDataRole.UserRole)
    ):
        vList.addItem(vItem)

    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."

    show(PAIRS)

    for vCombo in vPage.answer_widgets:
        vCombo.setCurrentIndex(1)

    vPage.validate()

    assert vPage.verdict_label.text().startswith("Réponse incorrecte. Votre réponse :")

    show(COMPLETION)
    vPage.answer_widgets[0].setText("length")
    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."


def test_symbol_is_shown_with_the_question(qt_application, tmp_path):
    """Vérifie qu'un symbole à reconnaître s'affiche avant la réponse, un schéma après."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    import_questions_file(
        vDatabaseFile, "", *build_lot_pack("electricite"), datetime.now()
    )
    vQuestions = {
        vQuestion["id"][-3:]: vQuestion
        for vQuestion in quiz_page.load_active_quiz(vDatabaseFile)["electricite"][
            "questions"
        ]
    }
    vPage.mode = "discover"

    for vNumber, vOnQuestion in (("024", True), ("088", False)):
        vPage.display_question(
            {
                **prepare_question(vQuestions[vNumber], random.Random(1)),
                "theme_key": "electricite",
            },
            "Électricité",
            "",
        )

        assert vPage.question_visual_widget.isHidden() is not vOnQuestion

    vPage.answer_widgets[0].setText("192 V")
    vPage.validate()

    assert not vPage.visual_widget.isHidden()


def test_zone_is_answered_by_clicking_the_drawing(qt_application, tmp_path):
    """Vérifie une zone : clic converti en coordonnées du dessin, marque et correction."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    import_questions_file(
        vDatabaseFile, "", *build_lot_pack("electricite"), datetime.now()
    )
    vQuestion = next(
        vItem
        for vItem in quiz_page.load_active_quiz(vDatabaseFile)["electricite"][
            "questions"
        ]
        if vItem["id"].endswith("-021")
    )
    vPage.mode = "discover"
    vPage.display_question(
        {**prepare_question(vQuestion, random.Random(1)), "theme_key": "electricite"},
        "Électricité",
        "",
    )
    vWidget = vPage.question_visual_widget

    assert not vWidget.isHidden() and vWidget.clickable

    vPage.validate()

    assert vPage.verdict_label.text() == "Complétez votre réponse."

    # Le dessin fait 760 × 230 : le centre du relais thermique est vers (390, 115).
    vScale = vWidget.width() / 760
    QTest.mouseClick(
        vWidget,
        quiz_page.Qt.MouseButton.LeftButton,
        pos=QPoint(round(390 * vScale), round(115 * vScale)),
    )

    assert vPage.zone_point[0] == pytest.approx(390, abs=3)
    assert vWidget.point is not None

    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."
    assert not vWidget.clickable and vWidget.point is not None


def test_schema_is_built_and_graded_on_the_desktop(qt_application, tmp_path):
    """Vérifie un schéma à construire : éditeur, réponse incomplète, correction et schéma attendu."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)
    import_questions_file(
        vDatabaseFile, "", *build_lot_pack("sigles-informatique"), datetime.now()
    )
    vQuestion = next(
        vItem
        for vItem in quiz_page.load_active_quiz(vDatabaseFile)["sigles-informatique"][
            "questions"
        ]
        if vItem["id"].endswith("-055")
    )
    vPage.mode = "discover"
    vPage.display_question(
        {**prepare_question(vQuestion, random.Random(1)), "theme_key": "x"},
        "Sigles",
        "",
    )
    vEditor = vPage.answer_widgets[0]

    vPage.validate()

    assert vPage.verdict_label.text() == "Complétez votre réponse."

    vChain = ["poste", "switch", "pare_feu", "routeur", "internet"]

    for vType in vChain:
        vEditor.add_component(vType)

    for vFirst, vSecond in zip(vChain, vChain[1:]):
        vEditor.select_port(vEditor.components[vFirst].ports["bas"])
        vEditor.select_port(vEditor.components[vSecond].ports["haut"])

    vPage.validate()

    assert vPage.verdict_label.text() == "Bonne réponse."
    assert not vEditor.isEnabled()
    assert not vPage.visual_widget.isHidden()
    assert vPage.visual_widget.toolTip() == "Votre schéma et schéma attendu"


def test_show_svg_reduces_a_wide_drawing(qt_application):
    """Vérifie qu'un schéma trop large est réduit au lieu d'élargir la page."""

    vWidget = quiz_page.QSvgWidget()
    vSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="200"></svg>'

    quiz_page.show_svg(vWidget, vSvg, "Schéma", 280, pMaxWidth=500)

    assert (vWidget.width(), vWidget.height()) == (500, 100)

    quiz_page.show_svg(vWidget, vSvg, "Schéma", 100, pMaxWidth=800)

    assert (vWidget.width(), vWidget.height()) == (500, 100)


def test_empty_rubric_offers_catalog_themes(qt_application, tmp_path, monkeypatch):
    """Vérifie qu'une rubrique sans question propose ses thèmes du catalogue."""

    vPage = create_page(tmp_path / "scraper.db")
    vPrepared = []
    monkeypatch.setattr(vPage.import_panel, "prepare_priority", vPrepared.append)

    assert (
        vPage.category_buttons[("Industrie", "Électricité et énergie")]
        .text()
        .endswith("(0)")
    )

    vPage.category_buttons[("Industrie", "Électricité et énergie")].click()

    vButtons = [
        vButton
        for vButton in vPage.findChildren(QPushButton)
        if vButton.text() == "Préparer" and vButton.isVisibleTo(vPage)
    ]

    assert vButtons
    assert vPage.filter_label.text() == "Industrie › Électricité et énergie"

    vButtons[0].click()

    assert len(vPrepared) == 1


def test_priority_banner_prepares_empty_themes(qt_application, tmp_path, monkeypatch):
    """Vérifie le bandeau des thèmes vides demandés et la demande préparée au clic."""

    vDatabaseFile = tmp_path / "scraper.db"
    vPage = create_page(vDatabaseFile)

    assert vPage.priority_banner.isHidden()

    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Automaticien",
                    "skills": ["Grafcet"],
                }
            ]
        ),
        datetime.now(),
    )
    vPrepared = []
    monkeypatch.setattr(vPage.import_panel, "prepare_priority", vPrepared.append)
    vPage.priority_banner.prepare_requested.disconnect()
    vPage.priority_banner.prepare_requested.connect(vPage.import_panel.prepare_priority)
    vPage.refresh()

    vButton = vPage.priority_banner.buttons_layout.itemAt(0).widget()

    assert not vPage.priority_banner.isHidden()
    assert vButton.text().startswith("Grafcet et logique séquentielle · 1 offre(s)")

    vButton.click()

    assert vPrepared == ["Grafcet et logique séquentielle"]


def test_priority_banner_offers_weak_themes(qt_application, tmp_path):
    """Vérifie les thèmes à renforcer d'après l'auto-évaluation, ouverts d'un clic."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_skill_levels(vDatabaseFile, {"Android": 2})

    vPage = QuizPage(vDatabaseFile)
    vPage.refresh()

    assert not vPage.priority_banner.isHidden()
    assert vPage.priority_banner.empty_title.isHidden()

    vButton = vPage.priority_banner.weak_layout.itemAt(0).widget()

    assert vButton.text() == "Entretien Android · Android 2/10"

    vButton.click()

    assert vPage.theme_key == "entretien_android"
