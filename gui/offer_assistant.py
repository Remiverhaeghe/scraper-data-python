"""Aide à la candidature d'une offre : préparation, examen blanc, ChatGPT et lien"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.dialogs import show_preparation, show_text_dialog
from gui.theme import COLORS
from gui.widgets import create_button
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.company_info import lookup_company, summarize_company
from job.cv_export import build_file_name, build_tailored_cv, write_docx
from job.geocoding import load_home
from job.interview_revision import build_offer_revision
from job.interview_journal import collect_asked_questions
from job.offer_comparison import (
    build_comparison,
    load_comparison_keys,
    toggle_comparison,
)
from job.preparation import prepare_application
from job.presentation import (
    AVAILABILITY_HELP,
    AVAILABILITY_LABELS,
    AVAILABILITY_MESSAGES,
    AVAILABILITY_TONES,
    can_lookup_company,
    format_date,
    get_score_tone,
    safe_url,
)
from job.profile import is_profile_empty, load_profile
from job.quiz import load_active_quiz
from job.quiz_exam import (
    build_exam_history,
    describe_exam_results,
    load_exam_results,
)
from job.star_answers import load_star_answers
from storage.job_offers import set_availability
from utils.link_checker import check_offer_link
from utils.logger import get_logger

logger = get_logger(__name__)

# Hauteur du graphique des notes, dans la colonne étroite de l'assistant
EXAM_CHART_HEIGHT = 130


def describe_availability(pOffer):
    """Résume la disponibilité connue d'une offre, sous le bouton de vérification."""

    rText = ""

    if pOffer.get("availability_checked_at"):
        rText = (
            f"Vérifiée le {format_date(pOffer['availability_checked_at'])} : "
            f"{AVAILABILITY_LABELS[pOffer['availability']]}"
        )
    elif pOffer.get("is_expired"):
        rText = "Probablement expirée : plus vue dans les recherches récentes."

    return rText


def describe_companies_html(pCompanies):
    """Présente les entreprises trouvées, avec le lien vers leur fiche officielle."""

    vItems = []

    for vCompany in pCompanies:
        # Textes reçus d'un service extérieur : échappés avant d'être affichés en HTML.
        vLink = (
            f"<br><a href='{escape(vCompany['url'])}'>Fiche sur l'Annuaire des "
            "entreprises</a>"
            if vCompany["url"]
            else ""
        )
        vItems.append(
            f"<li><b>{escape(vCompany['name'])}</b><br>"
            f"{escape(summarize_company(vCompany).split(' : ', 1)[-1])}{vLink}</li>"
        )

    rHtml = (
        "<p>Plusieurs sociétés portent souvent le même nom (groupe, filiales) : "
        "vérifiez la bonne avant l'entretien.</p>"
        f"<ul>{''.join(vItems)}</ul>"
    )

    return rHtml


class OfferAssistantPanel(QWidget):
    """Actions d'aide sur l'offre affichée, à base de règles et sans service payant."""

    exam_requested = Signal(dict)

    def __init__(self, pDatabaseFile):
        """Construit les boutons d'aide, inactifs tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None
        self.company_summary = None

        self.prepare_button = create_button(
            "Préparer ma candidature", "sparkles", pIconColor=COLORS["primary"]
        )
        self.prepare_button.clicked.connect(self.open_preparation)

        self.cv_button = create_button(
            "CV adapté (.docx)", "download", pIconColor=COLORS["primary"]
        )
        self.cv_button.setToolTip(
            "Votre profil réordonné pour l'offre : compétences demandées en tête, "
            "expériences les plus proches d'abord"
        )
        self.cv_button.clicked.connect(self.export_cv)

        # Examen blanc sur les thèmes de révision dont l'offre demande les compétences
        self.exam_button = create_button(
            "Examen blanc pour l'entretien", "timer", pIconColor=COLORS["primary"]
        )
        self.exam_button.setToolTip(
            "Questions tirées dans les thèmes de révision demandés par l'offre"
        )
        self.exam_button.clicked.connect(self.request_exam)

        # Demandes à coller dans ChatGPT : aucune API payante n'est appelée.
        self.chatgpt_button = create_button(
            "Préparer avec ChatGPT", "bot", pIconColor=COLORS["primary"]
        )
        self.chatgpt_button.setToolTip(
            "Copie une demande complète et ouvre ChatGPT : collez-la avec Ctrl+V"
        )

        vMenu = QMenu(self.chatgpt_button)

        for vKind, vLabel in PROMPT_KINDS.items():
            vMenu.addAction(vLabel, lambda pKind=vKind: self.copy_prompt(pKind))

        self.chatgpt_button.setMenu(vMenu)

        self.company_info_button = create_button(
            "Infos sur l'entreprise (France)", "globe", pIconColor=COLORS["primary"]
        )
        self.company_info_button.setToolTip(
            "Activité, taille et siège, depuis l'annuaire public des entreprises"
        )
        self.company_info_button.clicked.connect(self.show_company_info)

        self.exam_results_label = QLabel()
        self.exam_results_label.setObjectName("cardSubtitle")
        self.exam_results_label.setWordWrap(True)
        self.exam_results_label.hide()

        # Courbe des notes successives, à partir de deux examens
        self.exam_chart = BarChart()
        self.exam_chart.setFixedHeight(EXAM_CHART_HEIGHT)
        self.exam_chart.hide()

        self.assistant_label = QLabel()
        self.assistant_label.setObjectName("cardSubtitle")
        self.assistant_label.setWordWrap(True)

        self.availability_button = create_button(
            "Vérifier la disponibilité", "circle-check", pIconColor=COLORS["primary"]
        )
        self.availability_button.setToolTip(AVAILABILITY_HELP)
        self.availability_button.clicked.connect(self.check_availability)

        self.availability_label = QLabel()
        self.availability_label.setObjectName("cardSubtitle")
        self.availability_label.setWordWrap(True)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(4)
        vLayout.addWidget(self.prepare_button)
        vLayout.addWidget(self.cv_button)
        vLayout.addWidget(self.exam_button)
        vLayout.addWidget(self.exam_results_label)
        vLayout.addWidget(self.exam_chart)
        vLayout.addWidget(self.chatgpt_button)
        vLayout.addWidget(self.company_info_button)
        vLayout.addWidget(self.assistant_label)
        vLayout.addWidget(self.availability_button)
        vLayout.addWidget(self.availability_label)

        self.compare_button = create_button(
            "Ajouter à la comparaison", "list-checks", pIconColor=COLORS["primary"]
        )
        self.compare_button.setToolTip("Trois offres au plus, comparées côte à côte")
        self.compare_button.clicked.connect(self.toggle_comparison)

        self.show_comparison_button = create_button("Voir la comparaison")
        self.show_comparison_button.clicked.connect(self.show_comparison)

        vLayout.addWidget(self.compare_button)
        vLayout.addWidget(self.show_comparison_button)

    def set_offer(self, pOffer):
        """Prépare les actions pour une offre : entreprise, lien et disponibilité."""
        self.offer = pOffer
        self.company_summary = None
        self.assistant_label.clear()

        vOffer = pOffer or {}
        vHasCompany = bool(vOffer.get("company"))
        vLookup = can_lookup_company(vOffer)

        self.company_info_button.setEnabled(vLookup)
        self.company_info_button.setToolTip(
            "L'annuaire public ne couvre que les entreprises françaises"
            if vHasCompany and not vLookup
            else "Activité, taille et siège, depuis l'annuaire public des entreprises"
        )
        self.availability_button.setEnabled(safe_url(vOffer.get("url")) != "#")
        self.show_exam_results(vOffer)
        self.refresh_comparison()
        self.show_availability(
            describe_availability(vOffer),
            (
                vOffer.get("availability")
                if vOffer.get("availability_checked_at")
                else None
            ),
        )

    def export_cv(self):
        """Enregistre le CV réordonné pour l'offre à l'endroit choisi."""
        if self.offer is None:
            return

        vProfile = load_profile(self.database_file)

        if is_profile_empty(vProfile):
            QMessageBox.information(
                self,
                "CV adapté",
                "Renseignez d'abord vos compétences et expériences dans la page Profil.",
            )
            return

        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le CV adapté",
            str(Path.home() / build_file_name(self.offer)),
            "Document Word (*.docx)",
        )

        if not vPath:
            return

        try:
            Path(vPath).write_bytes(write_docx(build_tailored_cv(vProfile, self.offer)))

        except OSError as vException:
            logger.warning("CV adapté non enregistré : %s", vException)
            QMessageBox.warning(
                self, "CV adapté", f"Enregistrement impossible : {vException}"
            )
            return

        # Le chemin peut contenir le nom de l'utilisateur : seul le fait est journalisé.
        logger.info(
            "CV adapté enregistré pour %s/%s",
            self.offer["source"],
            self.offer["source_id"],
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(vPath))

    def open_preparation(self):
        """Ouvre la préparation de candidature, ou invite à remplir le profil."""
        if self.offer is None:
            return

        vProfile = load_profile(self.database_file)

        if is_profile_empty(vProfile):
            QMessageBox.information(
                self,
                "Préparer ma candidature",
                "Renseignez d'abord vos compétences et expériences dans la page Profil.",
            )
        else:
            show_preparation(
                self,
                self.offer.get("title") or "offre",
                prepare_application(
                    vProfile,
                    self.offer,
                    load_star_answers(self.database_file),
                    collect_asked_questions(self.database_file),
                ),
            )

    def refresh_comparison(self):
        """Met à jour les boutons de comparaison selon l'offre affichée."""
        try:
            vKeys = load_comparison_keys(self.database_file)

        except Exception:
            logger.exception("Impossible de lire la comparaison des offres")

            vKeys = []

        vInComparison = (
            self.offer is not None
            and (
                self.offer["source"],
                str(self.offer["source_id"]),
            )
            in vKeys
        )

        self.compare_button.setEnabled(self.offer is not None)
        self.compare_button.setText(
            "Retirer de la comparaison" if vInComparison else "Ajouter à la comparaison"
        )
        self.show_comparison_button.setText(f"Voir la comparaison ({len(vKeys)})")
        self.show_comparison_button.setEnabled(bool(vKeys))

    def toggle_comparison(self):
        """Ajoute l'offre affichée à la comparaison, ou l'en retire."""
        if self.offer is None:
            return

        toggle_comparison(
            self.database_file, self.offer["source"], self.offer["source_id"]
        )
        self.refresh_comparison()

    def show_comparison(self):
        """Affiche les offres comparées dans un tableau, une colonne par offre."""
        vComparison = build_comparison(self.database_file, datetime.now())

        vHeader = "".join(
            f"<th>{escape(vOffer.get('title') or 'Offre sans titre')}</th>"
            for vOffer in vComparison["offers"]
        )
        vRows = "".join(
            f"<tr><th align='left'>{escape(vLabel)}</th>"
            + "".join(f"<td>{escape(str(vValue))}</td>" for vValue in vValues)
            + "</tr>"
            for vLabel, vValues in vComparison["rows"]
        )

        show_text_dialog(
            self,
            "Comparaison des offres",
            pHtml=(
                "<table border='1' cellpadding='6' cellspacing='0'>"
                f"<tr><th></th>{vHeader}</tr>{vRows}</table>"
            ),
        )

    def show_exam_results(self, pOffer):
        """Rappelle les notes des examens blancs déjà passés sur l'offre."""
        vResults = []

        if pOffer.get("source"):
            try:
                vResults = load_exam_results(
                    self.database_file,
                    (pOffer["source"], str(pOffer.get("source_id"))),
                )

            except Exception:
                logger.exception("Impossible de lire les notes des examens blancs")

        vText = describe_exam_results(vResults)
        vHistory = build_exam_history(vResults)

        self.exam_results_label.setText(vText)
        self.exam_results_label.setVisible(bool(vText))
        self.exam_chart.set_series(
            [vPoint["label"] for vPoint in vHistory],
            [
                (
                    "Note",
                    [
                        COLORS[get_score_tone(vPoint["score"], "danger")]
                        for vPoint in vHistory
                    ],
                    [vPoint["score"] for vPoint in vHistory],
                )
            ],
            pFillWidth=True,
        )
        self.exam_chart.setVisible(len(vHistory) >= 2)

    def request_exam(self):
        """Montre les thèmes à revoir pour l'offre, puis propose l'examen blanc."""
        if self.offer is None:
            return

        vRevision = build_offer_revision(
            self.database_file, load_active_quiz(self.database_file), self.offer
        )

        if not vRevision["themes"]:
            QMessageBox.information(
                self,
                "Examen blanc",
                "Aucun thème de révision ne correspond aux compétences de cette "
                "offre. Importez des questions sur ces sujets depuis la page Révision.",
            )
            return

        vThemes = "\n".join(
            f"• {vTheme['label']} : {vTheme['score']} % acquis "
            f"({', '.join(vTheme['matched'])})"
            for vTheme in vRevision["themes"]
        )
        vAnswer = QMessageBox.question(
            self,
            "Examen blanc",
            "Thèmes demandés par l'offre, les moins maîtrisés d'abord :\n\n"
            f"{vThemes}\n\nCommencer un examen blanc de "
            f"{vRevision['exam_count']} questions ?",
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            self.exam_requested.emit(self.offer)

    def copy_prompt(self, pKind):
        """Copie une demande préparée pour ChatGPT puis ouvre le site."""
        vPrompt = build_prompts(
            load_profile(self.database_file), self.offer, self.company_summary
        )[pKind]

        QApplication.clipboard().setText(vPrompt)
        QDesktopServices.openUrl(QUrl(CHATGPT_URL))

        self.assistant_label.setText(
            f"Demande « {PROMPT_KINDS[pKind]} » copiée : collez-la dans ChatGPT "
            "(Ctrl+V) et relisez-la avant de l'envoyer."
        )

        logger.info("Demande ChatGPT copiée : %s", pKind)

    def show_company_info(self):
        """Affiche les entreprises trouvées dans l'annuaire public sous ce nom."""
        vCompanyName = self.offer.get("company")

        vCompanies = None
        vMessage = None

        # Requête courte mais bloquante : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vCompanies = lookup_company(vCompanyName, load_home(self.database_file))

        except ValueError as vException:
            vMessage = str(vException)

        finally:
            QApplication.restoreOverrideCursor()

        if vCompanies is None:
            QMessageBox.warning(self, "Infos sur l'entreprise", vMessage)

        elif not vCompanies:
            QMessageBox.information(
                self,
                "Infos sur l'entreprise",
                f"Aucune entreprise française trouvée sous le nom « {vCompanyName} ».",
            )

        else:
            # Les résultats possibles sont repris dans la demande « Comprendre
            # l'entreprise » : ChatGPT peut reconnaître la bonne société.
            self.company_summary = " ; ".join(
                summarize_company(vCompany) for vCompany in vCompanies
            )
            show_text_dialog(
                self,
                f"Entreprises trouvées pour « {vCompanyName} »",
                pHtml=describe_companies_html(vCompanies),
            )

    def check_availability(self):
        """Vérifie le lien de l'offre et enregistre un résultat net."""
        if self.offer is None:
            return

        # Requête courte mais bloquante : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            vAvailability = check_offer_link(self.offer.get("url") or "")

            if vAvailability is not None:
                set_availability(
                    self.database_file,
                    self.offer["source"],
                    self.offer["source_id"],
                    vAvailability,
                    datetime.now(),
                )
                self.offer["availability"] = vAvailability

        finally:
            QApplication.restoreOverrideCursor()

        self.show_availability(AVAILABILITY_MESSAGES[vAvailability], vAvailability)

    def show_availability(self, pText, pAvailability):
        """Affiche le résultat de la vérification, en gras et en couleur."""
        self.availability_label.setText(pText)
        self.availability_label.setStyleSheet(
            f"color: {COLORS[AVAILABILITY_TONES[pAvailability]]}; font-weight: 600;"
            if pText
            else ""
        )
