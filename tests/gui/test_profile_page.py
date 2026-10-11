"""Tests de la page du profil et de la préparation de candidature"""

import gui.dialogs as dialogs
import gui.offer_detail as offer_detail
from gui.profile_page import ProfilePage
from job.profile import build_profile, load_profile, save_profile
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


def test_preparation_needs_a_profile_then_opens(qt_application, tmp_path, monkeypatch):
    """Vérifie l'invitation à remplir le profil, puis l'ouverture de la préparation."""

    vDatabaseFile = tmp_path / "scraper.db"
    vShown = []
    vInformed = []

    initialize_database(vDatabaseFile)
    monkeypatch.setattr(
        offer_detail.QMessageBox, "information", lambda *pArgs: vInformed.append(True)
    )
    monkeypatch.setattr(
        offer_detail,
        "show_preparation",
        lambda pParent, pTitle, pPreparation: vShown.append(pPreparation),
    )

    vPanel = offer_detail.OfferDetailPanel(vDatabaseFile)
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
            "match": {"covered": ["<Java>"], "missing": [], "score": 100},
            "cv": {"name": "CV backend", "matching": 1},
            "interview": {
                "strengths": [{"skill": "<Java>", "examples": ["Projet A"]}],
                "gaps": [],
                "questions": ["Question ?"],
            },
            "letter": "",
        }
    )

    assert "&lt;Java&gt;" in vHtml
    assert "<Java>" not in vHtml
    assert "CV backend" in vHtml
    assert "Projet A" in vHtml
