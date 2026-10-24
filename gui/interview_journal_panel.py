"""Journal d'entretien d'une offre : questions posées et impressions"""

from datetime import datetime
from html import escape

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs import show_text_dialog
from gui.theme import COLORS
from gui.widgets import create_button, show_message
from job.interview_journal import (
    collect_company_questions,
    describe_note,
    record_interview,
)
from storage.interview_notes import get_interview_notes
from utils.logger import get_logger

logger = get_logger(__name__)


class InterviewDialog(QDialog):
    """Saisie d'une entrée du journal : questions posées puis impressions."""

    def __init__(self, pParent):
        """Construit les deux champs et les boutons Enregistrer et Annuler."""
        super().__init__(pParent)

        self.setWindowTitle("Noter un entretien")
        self.resize(520, 420)

        self.questions_edit = QPlainTextEdit()
        self.questions_edit.setPlaceholderText(
            "Une question par ligne, telle qu'elle a été posée"
        )

        self.impressions_edit = QPlainTextEdit()
        self.impressions_edit.setPlaceholderText(
            "Ce qui s'est bien passé, ce qui est à retravailler, la suite annoncée"
        )

        vButtons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        vButtons.accepted.connect(self.accept)
        vButtons.rejected.connect(self.reject)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(QLabel("Questions posées"))
        vLayout.addWidget(self.questions_edit, 2)
        vLayout.addWidget(QLabel("Impressions"))
        vLayout.addWidget(self.impressions_edit, 1)
        vLayout.addWidget(vButtons)


class InterviewJournalPanel(QWidget):
    """Compte les entrées du journal de l'offre et permet d'en ajouter."""

    def __init__(self, pDatabaseFile):
        """Construit le résumé et les deux boutons, vides sans offre choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None
        self.notes = []

        self.summary_label = QLabel()
        self.summary_label.setObjectName("cardSubtitle")
        self.summary_label.setWordWrap(True)

        self.company_label = QLabel()
        self.company_label.setWordWrap(True)
        self.company_label.hide()

        vAddButton = create_button(
            "Noter un entretien…", "file-text", pIconColor=COLORS["primary"]
        )
        vAddButton.setToolTip("Questions posées et impressions, reprises en révision")
        vAddButton.clicked.connect(self.add_note)

        self.show_button = create_button("Voir", "list-checks")
        self.show_button.clicked.connect(self.show_notes)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vAddButton)
        vButtons.addWidget(self.show_button)
        vButtons.addStretch()

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(QLabel("Journal d'entretien"))
        vLayout.addWidget(self.summary_label)
        vLayout.addWidget(self.company_label)
        vLayout.addLayout(vButtons)

    def set_offer(self, pOffer):
        """Relit le journal de l'offre affichée."""
        self.offer = pOffer
        self.notes = []
        vCompanyQuestions = []

        if pOffer is not None:
            try:
                self.notes = get_interview_notes(
                    self.database_file, pOffer["source"], pOffer["source_id"]
                )
                vCompanyQuestions = collect_company_questions(
                    self.database_file, pOffer
                )

            except Exception:
                logger.exception("Impossible de lire le journal d'entretien")

        self.summary_label.setText(
            f"{len(self.notes)} entrée(s), la dernière le {describe_note(self.notes[0])}"
            if self.notes
            else "Aucune entrée pour cette offre."
        )
        self.show_button.setEnabled(bool(self.notes))
        self.company_label.setVisible(bool(vCompanyQuestions))
        self.company_label.setText(
            "Déjà posées par cette entreprise : "
            + " ; ".join(vItem["question"] for vItem in vCompanyQuestions)
        )

    def add_note(self):
        """Ouvre la saisie d'une entrée, puis l'enregistre."""
        if self.offer is None:
            return

        vDialog = InterviewDialog(self)

        if vDialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.save_note(
            vDialog.questions_edit.toPlainText(),
            vDialog.impressions_edit.toPlainText(),
        )

    def save_note(self, pQuestions, pImpressions):
        """Enregistre une entrée datée de maintenant."""
        try:
            record_interview(
                self.database_file,
                self.offer["source"],
                self.offer["source_id"],
                datetime.now(),
                pQuestions,
                pImpressions,
            )

        except ValueError as vException:
            show_message(self.summary_label, str(vException), "warning")
            return

        except Exception:
            logger.exception("Échec de l'enregistrement du journal d'entretien")

            show_message(
                self.summary_label, "L'entrée n'a pas pu être enregistrée.", "danger"
            )
            return

        self.set_offer(self.offer)

    def show_notes(self):
        """Affiche les entrées du journal, la plus récente en tête."""
        vHtml = "".join(
            f"<h3>{escape(describe_note(vNote))}</h3>"
            + (
                "<ul>"
                + "".join(
                    f"<li>{escape(vQuestion)}</li>"
                    for vQuestion in vNote["questions"].splitlines()
                )
                + "</ul>"
                if vNote["questions"]
                else ""
            )
            + (
                f"<p>{escape(vNote['impressions']).replace(chr(10), '<br>')}</p>"
                if vNote["impressions"]
                else ""
            )
            for vNote in self.notes
        )

        show_text_dialog(self, "Journal d'entretien", pHtml=vHtml)
