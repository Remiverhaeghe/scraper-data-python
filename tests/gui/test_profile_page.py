"""Tests de la page du profil et de la préparation de candidature"""

import gui.dialogs as dialogs
import gui.offer_assistant as offer_assistant
import gui.profile_page as profile_page
from gui.profile_page import ProfilePage
from gui.theme import COLORS
from job.profile import build_profile, load_profile, save_profile
from job.star_answers import load_star_answers, save_star_answer
from storage.database import initialize_database


def test_profile_is_saved_and_reloaded(qt_application, tmp_path):
    """Vérifie l'enregistrement du profil saisi puis son rechargement."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vPage = ProfilePage(vDatabaseFile)
    vPage.refresh()
    vPage.skills_edit.setText("Java, SQL")
    vPage.experiences_edit.setPlainText("Développeur | Java | Livré une API")
    vPage.save()

    assert vPage.message_label.text().startswith("Profil enregistré : 2 compétence(s)")
    assert COLORS["success"] in vPage.message_label.styleSheet()
    assert load_profile(vDatabaseFile)["experiences"][0]["title"] == "Développeur"

    vReopened = ProfilePage(vDatabaseFile)
    vReopened.refresh()

    assert vReopened.skills_edit.text() == "Java, SQL"


def test_profile_reports_invalid_input(qt_application, tmp_path):
    """Vérifie le message affiché pour une saisie refusée."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    vPage = ProfilePage(vDatabaseFile)
    vPage.skills_edit.setText("x" * 30000)
    vPage.save()

    assert "trop long" in vPage.message_label.text()
    assert COLORS["warning"] in vPage.message_label.styleSheet()


def test_preparation_needs_a_profile_then_opens(qt_application, tmp_path, monkeypatch):
    """Vérifie l'invitation à remplir le profil, puis l'ouverture de la préparation."""

    vDatabaseFile = tmp_path / "scraper.db"
    vShown = []
    vInformed = []

    initialize_database(vDatabaseFile)
    monkeypatch.setattr(
        offer_assistant.QMessageBox,
        "information",
        lambda *pArgs: vInformed.append(True),
    )
    monkeypatch.setattr(
        offer_assistant,
        "show_preparation",
        lambda pParent, pTitle, pPreparation: vShown.append(pPreparation),
    )

    vPanel = offer_assistant.OfferAssistantPanel(vDatabaseFile)
    vPanel.offer = {"title": "Développeur Java", "description": "Java et Kafka"}
    vPanel.open_preparation()

    assert vInformed == [True]

    save_profile(vDatabaseFile, build_profile("", "", "Java", "", ""))
    vPanel.open_preparation()

    assert vShown[0]["match"]["covered"] == ["Java"]


def test_describe_preparation_escapes_and_lists(qt_application):
    """Vérifie la mise en forme HTML de la préparation, textes échappés."""

    vHtml = dialogs.describe_preparation(
        {
            "match": {
                "covered": ["<Java>"],
                "missing": [],
                "score": 100,
                "details": [{"skill": "<Java>", "weight": 2, "coverage": 1.0}],
            },
            "cv": {"name": "CV backend", "matching": 1},
            "interview": {
                "strengths": [{"skill": "<Java>", "examples": ["Projet A"]}],
                "gaps": [],
                "answers": [{"question": "Pourquoi <Acme> ?", "hint": "Activité"}],
                "questions": ["Question ?"],
            },
            "letter": "",
        }
    )

    assert "&lt;Java&gt;" in vHtml
    assert "<Java>" not in vHtml
    assert "CV backend" in vHtml
    assert "Projet A" in vHtml
    assert "Pourquoi &lt;Acme&gt; ?" in vHtml
    assert "&lt;Java&gt; · exigée · maîtrisée" in vHtml


def test_cv_import_fills_profile_and_copies_prompt(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie le pré-remplissage depuis un CV et la copie de la demande ChatGPT."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vCv = tmp_path / "cv.txt"
    vCv.write_text("Rémi Verhaeghe\nDéveloppeur Java\nJava, SQL", encoding="utf-8")
    vOpened = []

    monkeypatch.setattr(
        profile_page.QFileDialog, "getOpenFileName", lambda *pArgs: (str(vCv), "")
    )
    monkeypatch.setattr(profile_page.QDesktopServices, "openUrl", vOpened.append)

    vPage = ProfilePage(vDatabaseFile)
    vPage.skills_edit.setText("Kafka")
    vPage.import_button.click()

    assert vPage.name_edit.text() == "Rémi Verhaeghe"
    assert vPage.skills_edit.text() == "Kafka, Java, SQL"
    assert vPage.message_label.text().startswith("CV importé : 2 compétence(s)")
    assert not vPage.prompt_button.isHidden()

    vPage.prompt_button.click()

    assert "--- Mon CV ---" in profile_page.QApplication.clipboard().text()
    assert len(vOpened) == 1


def test_cv_import_reports_refused_file(qt_application, tmp_path):
    """Vérifie le message d'un CV refusé ou introuvable."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = ProfilePage(vDatabaseFile)
    vCv = tmp_path / "cv.odt"
    vCv.write_bytes(b"x")

    vPage.import_cv(str(vCv))

    assert "formats acceptés" in vPage.message_label.text()

    vPage.import_cv(str(tmp_path / "absent.pdf"))

    assert vPage.message_label.text() == "Le CV n'a pas pu être ouvert."


def test_star_answer_is_prefilled_and_saved(qt_application, tmp_path):
    """Vérifie le pré-remplissage depuis une expérience et l'enregistrement."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_profile(
        vDatabaseFile,
        build_profile("", "", "Java", "Développeur | Java | Livré la V2", ""),
    )

    vPage = ProfilePage(vDatabaseFile)
    vPage.refresh()
    vPanel = vPage.star_panel

    vPanel.experience_combo.setCurrentIndex(1)
    vPanel.field_edits["action"].setPlainText("Découpé le chantier")
    vPanel.prefill()

    assert vPanel.field_edits["result"].toPlainText() == "Livré la V2"
    assert vPanel.field_edits["action"].toPlainText() == "Découpé le chantier"

    vPanel.save()

    assert load_star_answers(vDatabaseFile)["reussite"]["experience"] == "Développeur"
    assert vPanel.question_combo.currentText().endswith("(préparée)")
    assert vPanel.message_label.text() == "1 réponse(s) préparée(s) sur 7."


def test_interview_drill_reveals_and_grades(qt_application, tmp_path):
    """Vérifie la réponse révélée puis l'auto-évaluation qui passe à la suite."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_star_answer(vDatabaseFile, "echec", "", {"result": "Leçon retenue"})

    vPage = ProfilePage(vDatabaseFile)
    vPage.refresh()
    vDrill = vPage.drill_panel

    assert vDrill.question_label.text().startswith("Racontez un échec")
    assert not vDrill.known_button.isEnabled()

    vDrill.reveal()

    assert vDrill.answer_label.text() == "Résultat : Leçon retenue"

    vDrill.known_button.click()

    assert vDrill.question_label.text().startswith("Aucune question à revoir")
