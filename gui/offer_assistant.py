"""Aide à la candidature d'une offre : préparation, examen blanc, ChatGPT et lien"""

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs import show_preparation, show_text_dialog
from gui.theme import COLORS
from gui.widgets import create_button
from job.assistant import CHATGPT_URL, PROMPT_KINDS, build_prompts
from job.company_info import lookup_company, summarize_company
from job.interview_revision import build_offer_revision
from job.preparation import prepare_application
from job.presentation import (
    AVAILABILITY_HELP,
    AVAILABILITY_LABELS,
    AVAILABILITY_MESSAGES,
    AVAILABILITY_TONES,
    can_lookup_company,
    format_date,
    safe_url,
)
from job.profile import is_profile_empty, load_profile
from job.quiz import load_active_quiz
from storage.job_offers import set_availability
from utils.link_checker import check_offer_link
from utils.logger import get_logger

logger = get_logger(__name__)


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
        vLayout.addWidget(self.exam_button)
        vLayout.addWidget(self.chatgpt_button)
        vLayout.addWidget(self.company_info_button)
        vLayout.addWidget(self.assistant_label)
        vLayout.addWidget(self.availability_button)
        vLayout.addWidget(self.availability_label)

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
        self.show_availability(
            describe_availability(vOffer),
            (
                vOffer.get("availability")
                if vOffer.get("availability_checked_at")
                else None
            ),
        )

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
                prepare_application(vProfile, self.offer),
            )

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
            vCompanies = lookup_company(vCompanyName)

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
