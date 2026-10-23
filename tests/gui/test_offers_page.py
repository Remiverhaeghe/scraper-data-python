"""Tests de la page des offres et du panneau de suivi"""

from datetime import datetime

import pandas as pd
import pytest
from PySide6.QtCore import QSettings

import gui.offer_assistant as offer_assistant
import gui.offer_attachments as offer_attachments
import gui.offer_detail as offer_detail
import gui.offers_page as offers_page_module
from gui.offer_form import ManualOfferDialog
from job.companies import load_company_rules
from job.manual_offers import add_manual_offer
from job.profile import build_profile, load_profile, save_profile
from gui.offer_application import describe_application
from gui.offer_detail import summarize_values
from gui.offers_model import format_cell, get_cell_color
from gui.theme import COLORS
from gui.offers_page import OffersPage
from storage.database import initialize_database
from storage.job_applications import get_application, save_application
from storage.job_offers import get_offer, save_offers, set_availability

NOW = datetime(2026, 10, 11, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec trois offres Lever, dont une ignorée."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    vItems = pd.DataFrame(
        [
            {
                "source": "lever",
                "source_id": "1",
                "title": "Développeur Java",
                "contract": "CDI",
                "url": "https://example.com/1",
            },
            {
                "source": "lever",
                "source_id": "2",
                "title": "Data Engineer",
                "contract": "CDD",
            },
            {"source": "lever", "source_id": "3", "title": "Offre ignorée"},
        ]
    )

    save_offers(rDatabaseFile, vItems, datetime.now())
    save_application(rDatabaseFile, "lever", "3", "IGNORED")

    return rDatabaseFile


@pytest.fixture
def offers_page(qt_application, database_file):
    """Crée la page des offres chargée depuis la base de test."""

    rPage = OffersPage(database_file)
    rPage.refresh()

    return rPage


def get_titles(pPage):
    """Retourne les titres affichés, dans l'ordre du modèle."""

    rTitles = sorted(vOffer["title"] for vOffer in pPage.model.offers)

    return rTitles


def test_page_lists_active_offers(offers_page):
    """Vérifie que les offres ignorées sont masquées par défaut."""

    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]
    assert offers_page.count_label.text().startswith("2 offre(s)")


def test_page_applies_filters(offers_page):
    """Vérifie que les filtres de la page sont transmis à la requête."""

    offers_page.filters_bar.contract_combo.setCurrentIndex(
        offers_page.filters_bar.contract_combo.findData("CDI")
    )

    assert get_titles(offers_page) == ["Développeur Java"]

    offers_page.filters_bar.status_combo.setCurrentIndex(
        offers_page.filters_bar.status_combo.findData("IGNORED")
    )
    offers_page.filters_bar.contract_combo.setCurrentIndex(0)

    assert get_titles(offers_page) == ["Offre ignorée"]


def test_selection_displays_offer(offers_page):
    """Vérifie que la sélection d'une ligne remplit le panneau de détail."""

    offers_page.select_offer(("lever", "1"))

    assert offers_page.detail_panel.title_label.text() == "Développeur Java"
    assert offers_page.detail_panel.open_button.isEnabled()


def test_saving_application_keeps_selection(offers_page, database_file):
    """Vérifie l'enregistrement du suivi puis le maintien de la sélection."""

    offers_page.select_offer(("lever", "1"))

    vPanel = offers_page.detail_panel
    vPanel.application.status_combo.setCurrentIndex(
        vPanel.application.status_combo.findData("APPLIED")
    )
    vPanel.application.notes_edit.setPlainText("Contact : RH")
    vPanel.application.save()

    vApplication = get_application(database_file, "lever", "1")

    assert vApplication["status"] == "APPLIED"
    assert vApplication["notes"] == "Contact : RH"
    assert vApplication["follow_up_date"] is not None
    assert vPanel.offer["source_id"] == "1"
    assert vPanel.application.follow_up_button.isVisibleTo(vPanel)


def test_removing_status_deletes_application(offers_page, database_file):
    """Vérifie que « Aucun suivi » supprime le suivi existant."""

    save_application(database_file, "lever", "2", "INTERESTED")

    offers_page.select_offer(("lever", "2"))
    offers_page.detail_panel.application.status_combo.setCurrentIndex(0)
    offers_page.detail_panel.application.save()

    assert get_application(database_file, "lever", "2") is None


def test_describe_application():
    """Vérifie le résumé des dates de candidature et de relance."""

    vApplication = {
        "applied_at": "2026-10-01T09:00:00",
        "follow_up_count": 2,
        "last_follow_up_at": "2026-10-08T10:00:00",
    }

    assert describe_application(vApplication) == (
        "Candidature envoyée le 01/10/2026. 2 relance(s), la dernière le 08/10/2026."
    )
    assert describe_application(None) == ""


def test_empty_result_shows_empty_state(offers_page):
    """Vérifie l'état vide lorsqu'aucune offre ne correspond aux filtres."""

    offers_page.filters_bar.search_edit.setText("introuvable")
    offers_page.refresh()

    assert offers_page.detail_panel.stack.currentIndex() == 0
    assert offers_page.detail_panel.offer is None


def test_first_offer_is_selected_by_default(offers_page):
    """Vérifie qu'une offre est affichée sans action de l'utilisateur."""

    assert offers_page.detail_panel.stack.currentIndex() == 1
    assert offers_page.detail_panel.offer is not None


def test_apply_preset_resets_other_filters(offers_page):
    """Vérifie qu'un préréglage repart de filtres vierges."""

    offers_page.filters_bar.contract_combo.setCurrentIndex(
        offers_page.filters_bar.contract_combo.findData("CDD")
    )

    offers_page.apply_preset("new_offers")

    assert offers_page.filters_bar.contract_combo.currentData() is None
    assert offers_page.filters_bar.new_check.isChecked()
    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]


def test_export_uses_current_filters(offers_page, tmp_path):
    """Vérifie que l'export reprend les filtres affichés."""

    offers_page.filters_bar.contract_combo.setCurrentIndex(
        offers_page.filters_bar.contract_combo.findData("CDI")
    )

    assert offers_page.export_to(tmp_path / "offres.json") == 1


def test_empty_information_is_hidden(offers_page):
    """Vérifie qu'une information absente n'est pas affichée."""

    offers_page.select_offer(("lever", "1"))

    vRows = offers_page.detail_panel.info_rows

    assert not vRows["salary"][0].isVisibleTo(offers_page.detail_panel)
    assert vRows["contract"][0].isVisibleTo(offers_page.detail_panel)
    assert vRows["contract"][1].text() == "CDI"


def test_search_results_are_shown_alone(offers_page):
    """Vérifie l'affichage des seuls résultats d'une recherche, puis le retour."""

    offers_page.apply_preset("offers", [("lever", "2")], "Résultats de la recherche")

    assert get_titles(offers_page) == ["Data Engineer"]
    assert offers_page.results_banner.isVisibleTo(offers_page)

    offers_page.apply_preset("offers")

    assert get_titles(offers_page) == ["Data Engineer", "Développeur Java"]
    assert not offers_page.results_banner.isVisibleTo(offers_page)


def test_salary_and_publication_filters(offers_page):
    """Vérifie que les nouveaux filtres sont transmis à la requête."""

    offers_page.filters_bar.max_salary_spin.setValue(2500)
    offers_page.filters_bar.salary_check.setChecked(True)
    offers_page.filters_bar.published_combo.setCurrentIndex(2)

    vFilters = offers_page.build_filters(datetime.now(), 3)

    assert vFilters["pMaxNetSalary"] == 2500
    assert vFilters["pHasSalary"] is True
    assert vFilters["pPublishedSince"] is not None


@pytest.mark.parametrize(
    "pValues, pExpected",
    [
        (None, ""),
        (["Java", "SQL"], "Java, SQL"),
        (["A", "B", "C", "D", "E", "F"], "A, B, C, D +2"),
    ],
)
def test_summarize_values(pValues, pExpected):
    """Vérifie qu'une longue liste est abrégée pour tenir dans le panneau."""

    assert summarize_values(pValues) == pExpected


def test_expired_offers_are_hidden_then_shown_greyed(offers_page, database_file):
    """Vérifie le masquage par défaut puis l'affichage grisé des offres retirées."""

    set_availability(database_file, "lever", "2", "expired", datetime.now())
    offers_page.refresh()

    assert get_titles(offers_page) == ["Développeur Java"]

    offers_page.filters_bar.availability_combo.setCurrentIndex(
        offers_page.filters_bar.availability_combo.findData("expired")
    )

    assert get_titles(offers_page) == ["Data Engineer"]
    assert (
        get_cell_color(offers_page.model.offers[0], "contract").name()
        == COLORS["muted"].lower()
    )


@pytest.mark.parametrize(
    "pResult, pText, pSaved",
    [
        ("expired", "retirée", "expired"),
        (None, "n'a pas permis de conclure", None),
    ],
)
def test_detail_checks_availability(
    offers_page, database_file, monkeypatch, pResult, pText, pSaved
):
    """Vérifie la vérification du lien depuis le détail et l'enregistrement."""

    monkeypatch.setattr(offer_assistant, "check_offer_link", lambda pUrl: pResult)

    offers_page.select_offer(("lever", "1"))
    offers_page.detail_panel.assistant.check_availability()

    assert pText in offers_page.detail_panel.assistant.availability_label.text()
    assert (
        "font-weight: 600"
        in offers_page.detail_panel.assistant.availability_label.styleSheet()
    )
    assert get_offer(database_file, "lever", "1")["availability"] == pSaved


def test_duplicates_are_grouped_then_separated(offers_page, database_file):
    """Vérifie le regroupement des annonces, leur comparaison et la séparation."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {
                    "source": "adzuna",
                    "source_id": "a",
                    "title": "QA",
                    "contract": "CDI",
                    "fingerprint": "qa|acme|lille",
                },
                {
                    "source": "jooble",
                    "source_id": "b",
                    "title": "QA",
                    "contract": "CDD",
                    "fingerprint": "qa|acme|lille",
                },
            ]
        ),
        datetime.now(),
    )
    offers_page.filters_bar.multiple_check.setChecked(True)

    vOffer = offers_page.model.offers[0]

    assert len(offers_page.model.offers) == 1
    assert format_cell(vOffer, "source_label") == "Adzuna, Jooble"
    assert vOffer["needs_review"]

    offers_page.select_offer(("adzuna", "a"))

    assert offers_page.detail_panel.duplicates_group.isVisibleTo(offers_page)
    assert "Différences à valider" in offers_page.detail_panel.duplicates_label.text()

    offers_page.detail_panel.decide_duplicates("separate")
    offers_page.filters_bar.multiple_check.setChecked(False)

    assert get_titles(offers_page).count("QA") == 2


def test_manual_offer_dialog_requires_fields(qt_application, database_file):
    """Vérifie que la saisie incomplète reste ouverte, puis que l'offre est créée."""

    vDialog = ManualOfferDialog(database_file)

    vDialog.save()

    assert vDialog.error_label.text().startswith("Offre non créée : titre manquant")
    assert vDialog.source_id is None

    vDialog.title_edit.setText("Architecte cloud")
    vDialog.company_edit.setText("Nimbus")
    vDialog.url_edit.setText("https://nimbus.example/offre")
    vDialog.save()

    assert get_offer(database_file, "manual", vDialog.source_id)["title"] == (
        "Architecte cloud"
    )


def test_import_from_file_shows_report(offers_page, tmp_path, monkeypatch):
    """Vérifie l'import d'un fichier et le bilan affiché, lignes refusées comprises."""

    vPath = tmp_path / "offres.json"
    vPath.write_text(
        '[{"title": "Analyste", "company": "Data SA", "url": "https://d.example"},'
        ' {"title": "Sans entreprise", "url": "https://d.example/2"}]',
        encoding="utf-8",
    )
    vShown = {}

    monkeypatch.setattr(
        offers_page_module.QMessageBox,
        "exec",
        lambda pBox: vShown.update(text=pBox.text(), details=pBox.detailedText()),
    )

    offers_page.import_from(str(vPath))

    assert "Analyste" in get_titles(offers_page)
    assert vShown["text"].startswith("1 offre(s) importée(s) sur 2")
    assert vShown["details"] == "Ligne 2 : entreprise manquante"


def test_company_warning_and_exclusion(offers_page, database_file, monkeypatch):
    """Vérifie l'avertissement orange puis l'exclusion de l'entreprise depuis la fiche."""

    vFields = {"company": "Acme", "url": "https://acme.example"}
    vFirstId = add_manual_offer(database_file, {**vFields, "title": "Java"}, NOW)
    vSecondId = add_manual_offer(database_file, {**vFields, "title": "Python"}, NOW)
    save_application(database_file, "manual", vFirstId, "APPLIED")

    offers_page.refresh()
    offers_page.select_offer(("manual", vSecondId))

    vPanel = offers_page.detail_panel

    assert not vPanel.company_warning.isHidden()
    assert vPanel.company_warning.text().startswith(
        "Déjà 1 candidature(s) dans cette entreprise : Java"
    )

    monkeypatch.setattr(
        offer_detail.QMessageBox,
        "question",
        lambda *pArgs: offer_detail.QMessageBox.StandardButton.Yes,
    )
    vPanel.company_buttons["excluded"].click()

    assert "Python" not in get_titles(offers_page)
    assert load_company_rules(database_file)["excluded"] == ["Acme"]


def test_attachments_are_added_and_deleted(
    offers_page, database_file, tmp_path, monkeypatch
):
    """Vérifie l'ajout d'une pièce jointe, le refus d'un type inconnu et la suppression."""

    vPanel = offers_page.detail_panel
    vCv = tmp_path / "CV.pdf"
    vCv.write_bytes(b"%PDF")
    vRefused = tmp_path / "outil.exe"
    vRefused.write_bytes(b"MZ")
    vWarnings = []

    monkeypatch.setattr(
        offer_attachments.QMessageBox,
        "warning",
        lambda pParent, pTitle, pText: vWarnings.append(pText),
    )
    monkeypatch.setattr(
        offer_attachments.QMessageBox,
        "question",
        lambda *pArgs: offer_attachments.QMessageBox.StandardButton.Yes,
    )

    vPanel.application.attachments.attach_file(str(vCv))
    vPanel.application.attachments.attach_file(str(vRefused))

    assert vPanel.application.attachments.attachments_list.count() == 1
    assert (
        vPanel.application.attachments.attachments_list.item(0)
        .text()
        .startswith("CV.pdf · ")
    )
    assert vWarnings[0].startswith("Type de fichier non accepté")

    vPanel.application.attachments.attachments_list.setCurrentRow(0)
    vPanel.application.attachments.delete_attachment()

    assert vPanel.application.attachments.attachments_list.count() == 0


def test_add_offer_selects_created_offer(offers_page, monkeypatch):
    """Vérifie que l'offre saisie est affichée et sélectionnée après sa création."""

    def accept(pDialog):
        """Remplit puis valide la fenêtre comme le ferait l'utilisateur."""
        pDialog.title_edit.setText("Architecte cloud")
        pDialog.company_edit.setText("Nimbus")
        pDialog.description_edit.setPlainText("Kubernetes et Terraform")
        pDialog.save()

        return pDialog.result()

    monkeypatch.setattr(offers_page_module.ManualOfferDialog, "exec", accept)

    offers_page.add_offer()

    assert offers_page.detail_panel.offer["title"] == "Architecte cloud"


def test_import_errors_are_reported(offers_page, tmp_path, monkeypatch):
    """Vérifie les messages d'un fichier refusé ou illisible, et le choix annulé."""

    vWarnings = []

    monkeypatch.setattr(
        offers_page_module.QMessageBox,
        "warning",
        lambda pParent, pTitle, pText: vWarnings.append(pText),
    )
    monkeypatch.setattr(
        offers_page_module.QFileDialog,
        "getOpenFileName",
        lambda *pArgs: (str(tmp_path / "offres.txt"), ""),
    )

    offers_page.choose_import_file()

    monkeypatch.setattr(
        offers_page_module,
        "import_offers_file",
        lambda *pArgs: (_ for _ in ()).throw(OSError("disque")),
    )
    offers_page.import_from(str(tmp_path / "offres.csv"))

    assert vWarnings == [
        "Format non pris en charge : .txt.",
        "Le fichier n'a pas pu être importé.",
    ]


def test_attachment_dialogs(offers_page, tmp_path, monkeypatch):
    """Vérifie le choix d'un fichier à joindre et l'ouverture d'une pièce jointe."""

    vPanel = offers_page.detail_panel
    vCv = tmp_path / "CV.pdf"
    vCv.write_bytes(b"%PDF")
    vOpened = []

    monkeypatch.setattr(
        offer_attachments.QFileDialog, "getOpenFileName", lambda *pArgs: (str(vCv), "")
    )
    monkeypatch.setattr(
        offer_attachments.QDesktopServices, "openUrl", lambda pUrl: vOpened.append(pUrl)
    )

    vPanel.application.attachments.add_attachment()
    vPanel.application.attachments.open_attachment(
        vPanel.application.attachments.attachments_list.item(0)
    )

    assert vOpened[0].toLocalFile().endswith(".pdf")


def test_company_preferred_from_detail(offers_page, database_file):
    """Vérifie qu'une entreprise privilégiée est marquée d'une étoile dans la liste."""

    vSourceId = add_manual_offer(
        database_file,
        {"title": "Go", "company": "Globex", "url": "https://g.example"},
        NOW,
    )
    offers_page.refresh()
    offers_page.select_offer(("manual", vSourceId))

    offers_page.detail_panel.company_buttons["preferred"].click()

    vRow = next(
        vIndex
        for vIndex, vOffer in enumerate(offers_page.model.offers)
        if vOffer["source_id"] == vSourceId
    )

    assert format_cell(offers_page.model.offers[vRow], "company") == "★ Globex"
    assert offers_page.detail_panel.company_buttons["preferred"].isHidden()


def test_chatgpt_prompt_and_company_info(offers_page, database_file, monkeypatch):
    """Vérifie la demande copiée pour ChatGPT et les infos d'entreprise reprises."""

    vSourceId = add_manual_offer(
        database_file,
        {"title": "Go", "company": "Globex", "url": "https://g.example"},
        NOW,
    )
    offers_page.refresh()
    offers_page.select_offer(("manual", vSourceId))

    vPanel = offers_page.detail_panel
    vOpened = []
    vDialogs = []

    monkeypatch.setattr(
        offer_assistant.QDesktopServices, "openUrl", lambda pUrl: vOpened.append(pUrl)
    )
    monkeypatch.setattr(
        offer_assistant,
        "lookup_company",
        lambda pName, _pHome: [
            {
                "name": "GLOBEX",
                "siren": "123456789",
                "activity": "Information et communication",
                "activity_code": "62.01Z",
                "employees": None,
                "category": "PME",
                "created": "2010",
                "city": "LILLE",
                "revenue": None,
                "active": True,
                "url": "https://annuaire.example/123456789",
            }
        ],
    )
    monkeypatch.setattr(
        offer_assistant,
        "show_text_dialog",
        lambda pParent, pTitle, pHtml: vDialogs.append(pHtml),
    )

    vPanel.assistant.show_company_info()
    vPanel.assistant.copy_prompt("company")

    assert "https://annuaire.example/123456789" in vDialogs[0]
    assert vOpened[0].toString() == "https://chatgpt.com/"
    assert "Informations publiques déjà trouvées : GLOBEX" in (
        offer_assistant.QApplication.clipboard().text()
    )
    assert vPanel.assistant.assistant_label.text().startswith(
        "Demande « Comprendre l'entreprise » copiée"
    )


def test_interview_score_and_france_filter(offers_page, database_file):
    """Vérifie la date d'entretien enregistrée, le score affiché et le filtre France."""

    save_profile(database_file, build_profile("", "", "Java, Spring", "", ""))
    vSourceId = add_manual_offer(
        database_file,
        {
            "title": "Développeur Java",
            "company": "Acme",
            "location": "Lille",
            "description": "Java, Spring et Kafka",
        },
        NOW,
    )
    offers_page.refresh()
    offers_page.select_offer(("manual", vSourceId))

    vPanel = offers_page.detail_panel
    vOffer = vPanel.offer

    assert format_cell(vOffer, "match_score") == "67 %"
    assert vOffer["country"] == "France"

    vPanel.application.status_combo.setCurrentIndex(
        vPanel.application.status_combo.findData("INTERVIEW")
    )
    vPanel.application.interview_check.setChecked(True)
    vPanel.application.save()

    assert get_application(database_file, "manual", vSourceId)["interview_at"]

    offers_page.filters_bar.france_check.setChecked(True)

    assert get_titles(offers_page) == ["Développeur Java"]

    # Filtre France gardé : seule l'offre ajoutée, à 50 % du profil, reste.
    offers_page.filters_bar.match_combo.setCurrentIndex(
        offers_page.filters_bar.match_combo.findData(70)
    )

    assert get_titles(offers_page) == []

    offers_page.filters_bar.match_combo.setCurrentIndex(
        offers_page.filters_bar.match_combo.findData(50)
    )

    assert get_titles(offers_page) == ["Développeur Java"]


class SynchronousThread:
    """Remplace threading.Thread : la cible s'exécute tout de suite, sans fil."""

    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        """Exécute la cible dans le fil courant."""
        self.target(*self.args)


def test_detail_offers_translation_and_limits_company_info(
    offers_page, database_file, monkeypatch
):
    """Vérifie la traduction d'une annonce étrangère et l'annuaire grisé hors France."""

    save_offers(
        database_file,
        pd.DataFrame(
            [
                {
                    "source": "arbeitnow",
                    "source_id": "de",
                    "title": "Entwickler",
                    "company": "GmbH",
                    "location": "Düsseldorf, Allemagne",
                    "country": "Allemagne",
                    "description": "Wir suchen neue Mitarbeiter für unser Team in Düsseldorf",
                }
            ]
        ),
        datetime.now(),
    )
    vOpened = []
    monkeypatch.setattr(offer_detail.QDesktopServices, "openUrl", vOpened.append)
    # Sans modèle de traduction installé, la description s'ouvre dans le navigateur.
    monkeypatch.setattr(offer_detail, "can_translate", lambda _pText: False)

    offers_page.refresh()
    offers_page.select_offer(("arbeitnow", "de"))
    vPanel = offers_page.detail_panel

    assert not vPanel.translate_button.isHidden()
    assert not vPanel.assistant.company_info_button.isEnabled()

    vPanel.translate_button.click()

    assert "translate.google.com" in vOpened[0].toString()

    # Avec un modèle, le texte est remplacé sur place, puis rétabli.
    monkeypatch.setattr(offer_detail, "can_translate", lambda _pText: True)
    monkeypatch.setattr(
        offer_detail,
        "translate_with_cache",
        lambda _pDatabaseFile, _pText: "Nous recherchons",
    )
    monkeypatch.setattr(offer_detail.threading, "Thread", SynchronousThread)

    vPanel.translate_button.click()

    assert vPanel.description.toPlainText() == "Nous recherchons"
    assert vPanel.translate_button.text() == "Texte d'origine"

    vPanel.translate_button.click()

    assert vPanel.description.toPlainText().startswith("Wir suchen")
    assert len(vOpened) == 1


def test_detail_can_be_hidden_at_once(offers_page):
    """Vérifie que toute la fiche se masque d'un clic et le reste à la réouverture."""

    QSettings().remove(offers_page_module.DETAIL_HIDDEN_KEY)
    offers_page.set_detail_visible(True)

    offers_page.detail_button.click()

    assert offers_page.detail_panel.isHidden()
    assert offers_page.detail_button.text() == "Afficher la fiche"
    assert QSettings().value(offers_page_module.DETAIL_HIDDEN_KEY, type=bool)

    offers_page.detail_button.click()

    assert not offers_page.detail_panel.isHidden()

    QSettings().remove(offers_page_module.DETAIL_HIDDEN_KEY)


def test_column_width_is_kept_for_the_next_opening(database_file):
    """Vérifie que la largeur d'une colonne élargie est rétablie à la réouverture."""

    for vKey in (
        offers_page_module.COLUMNS_STATE_KEY,
        offers_page_module.SPLITTER_STATE_KEY,
    ):
        QSettings().remove(vKey)

    vPage = OffersPage(database_file)
    vPage.table.setColumnWidth(1, 333)

    vReopened = OffersPage(database_file)

    assert vReopened.table.columnWidth(1) == 333

    for vKey in (
        offers_page_module.COLUMNS_STATE_KEY,
        offers_page_module.SPLITTER_STATE_KEY,
    ):
        QSettings().remove(vKey)


def test_tailored_cv_is_saved_where_chosen(
    offers_page, database_file, tmp_path, monkeypatch
):
    """Vérifie l'enregistrement du CV adapté au chemin choisi, puis son ouverture."""

    save_profile(
        database_file,
        {**load_profile(database_file), "name": "Camille", "skills": ["Java"]},
    )
    offers_page.select_offer(("lever", "1"))
    vTarget = tmp_path / "cv.docx"
    vOpened = []
    monkeypatch.setattr(
        offer_assistant.QFileDialog,
        "getSaveFileName",
        lambda *pArgs: (str(vTarget), ""),
    )
    monkeypatch.setattr(
        offer_assistant.QDesktopServices, "openUrl", lambda pUrl: vOpened.append(pUrl)
    )

    offers_page.detail_panel.assistant.export_cv()

    assert vTarget.read_bytes()[:2] == b"PK"
    assert len(vOpened) == 1


def test_keyboard_status_moves_to_the_next_offer(offers_page, database_file):
    """Vérifie le statut donné au clavier, puis l'offre suivante choisie."""

    offers_page.select_offer(("lever", "1"))
    offers_page.set_current_status("IGNORED")

    assert get_application(database_file, "lever", "1")["status"] == "IGNORED"
    assert offers_page.detail_panel.offer["source_id"] == "2"

    offers_page.set_current_status("INTERESTED")

    assert get_application(database_file, "lever", "2")["status"] == "INTERESTED"
    assert "Raccourcis" in offers_page.table.toolTip()
