"""Suivi de candidature d'une offre : statut, relance, entretien et notes"""

from datetime import datetime

from PySide6.QtCore import QDate, QDateTime, QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.interview_journal_panel import InterviewJournalPanel
from gui.offer_attachments import AttachmentsPanel
from gui.widgets import align_spin_box, create_button
from job.application_tracking import describe_status_history
from job.presentation import STATUS_LABELS, format_date
from job.settings import load_settings
from storage.job_applications import (
    delete_application,
    get_application,
    get_status_history,
    record_follow_up,
    save_application,
)
from storage.job_offers import FOLLOW_UP_STATUSES
from utils.logger import get_logger

logger = get_logger(__name__)


def describe_application(pApplication):
    """Résume les dates de candidature et de relance."""

    vParts = []

    if pApplication and pApplication.get("applied_at"):
        vParts.append(
            f"Candidature envoyée le {format_date(pApplication['applied_at'])}."
        )

    if pApplication and pApplication.get("follow_up_count"):
        vParts.append(
            f"{pApplication['follow_up_count']} relance(s), la dernière le "
            f"{format_date(pApplication['last_follow_up_at'])}."
        )

    rDescription = " ".join(vParts)

    return rDescription


class ApplicationPanel(QGroupBox):
    """Formulaire de suivi de la candidature à l'offre affichée."""

    changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit le formulaire, vide tant qu'aucune offre n'est choisie."""
        super().__init__("Suivi")

        self.database_file = pDatabaseFile
        self.offer = None

        self.status_combo = QComboBox()
        self.status_combo.addItem("Aucun suivi", None)

        for vStatus, vLabel in STATUS_LABELS.items():
            self.status_combo.addItem(vLabel, vStatus)

        self.follow_up_check = QCheckBox("Relance prévue le")

        self.follow_up_edit = align_spin_box(QDateEdit())
        self.follow_up_edit.setCalendarPopup(True)
        self.follow_up_edit.setDisplayFormat("dd/MM/yyyy")
        self.follow_up_edit.calendarWidget().setMinimumSize(320, 240)

        self.follow_up_check.toggled.connect(self.follow_up_edit.setEnabled)

        self.interview_check = QCheckBox("Entretien le")

        self.interview_edit = align_spin_box(QDateTimeEdit())
        self.interview_edit.setCalendarPopup(True)
        self.interview_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.interview_edit.calendarWidget().setMinimumSize(320, 240)

        self.interview_check.toggled.connect(self.interview_edit.setEnabled)

        # Les deux dates partagent une colonne : même largeur, sans texte coupé.
        vDates = QGridLayout()
        vDates.setHorizontalSpacing(8)
        vDates.addWidget(self.follow_up_check, 0, 0)
        vDates.addWidget(self.follow_up_edit, 0, 1)
        vDates.addWidget(self.interview_check, 1, 0)
        vDates.addWidget(self.interview_edit, 1, 1)
        vDates.setColumnStretch(1, 1)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Notes")

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.follow_up_button = QPushButton("J'ai relancé aujourd'hui")
        self.follow_up_button.clicked.connect(self.add_follow_up)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vSaveButton)
        vButtons.addWidget(self.follow_up_button)
        vButtons.addStretch()

        self.application_label = QLabel()
        self.application_label.setObjectName("pageSubtitle")
        self.application_label.setWordWrap(True)

        self.attachments = AttachmentsPanel(pDatabaseFile)
        self.journal = InterviewJournalPanel(pDatabaseFile)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.status_combo)
        vLayout.addLayout(vDates)
        vLayout.addWidget(self.notes_edit)
        vLayout.addLayout(vButtons)
        vLayout.addWidget(self.application_label)
        vLayout.addWidget(self.journal)
        vLayout.addWidget(self.attachments)

    def set_offer(self, pOffer):
        """Affiche le suivi et les pièces jointes d'une offre, ou les vide."""
        self.offer = pOffer
        self.load_application()

    def load_application(self):
        """Remplit le formulaire de suivi à partir de la base."""
        vApplication = None

        if self.offer is not None:
            vApplication = get_application(
                self.database_file, self.offer["source"], self.offer["source_id"]
            )

        vApplication = vApplication or {}

        self.status_combo.setCurrentIndex(
            max(self.status_combo.findData(vApplication.get("status")), 0)
        )

        vFollowUpDate = vApplication.get("follow_up_date")

        self.follow_up_check.setChecked(bool(vFollowUpDate))
        self.follow_up_edit.setEnabled(bool(vFollowUpDate))
        self.follow_up_edit.setDate(
            QDate.fromString(vFollowUpDate[:10], "yyyy-MM-dd")
            if vFollowUpDate
            else QDate.currentDate().addDays(self.get_follow_up_days())
        )

        vInterviewAt = vApplication.get("interview_at")

        self.interview_check.setChecked(bool(vInterviewAt))
        self.interview_edit.setEnabled(bool(vInterviewAt))
        self.interview_edit.setDateTime(
            QDateTime.fromString(vInterviewAt, "yyyy-MM-ddTHH:mm")
            if vInterviewAt
            else QDateTime(QDate.currentDate().addDays(7), QTime(10, 0))
        )

        self.notes_edit.setPlainText(vApplication.get("notes") or "")
        self.follow_up_button.setVisible(
            vApplication.get("status") in FOLLOW_UP_STATUSES
        )
        vHistory = (
            describe_status_history(
                get_status_history(
                    self.database_file, self.offer["source"], self.offer["source_id"]
                )
            )
            if self.offer is not None
            else ""
        )
        self.application_label.setText(
            "\n".join(
                vPart
                for vPart in (
                    describe_application(vApplication),
                    f"Historique : {vHistory}" if vHistory else "",
                )
                if vPart
            )
        )
        self.attachments.set_offer(self.offer)
        self.journal.set_offer(self.offer)

    def get_follow_up_days(self):
        """Retourne le délai de relance défini dans les paramètres."""
        rDays = load_settings(self.database_file)["follow_up_days"]

        return rDays

    def get_follow_up_date(self):
        """Retourne la date de relance saisie, ou None si aucune n'est prévue."""
        rDate = None

        if self.follow_up_check.isChecked():
            vDate = self.follow_up_edit.date()
            rDate = datetime(vDate.year(), vDate.month(), vDate.day())

        return rDate

    def get_interview_at(self):
        """Retourne la date et l'heure d'entretien saisies, ou None."""
        rInterviewAt = None

        if self.interview_check.isChecked():
            vValue = self.interview_edit.dateTime()
            rInterviewAt = datetime(
                vValue.date().year(),
                vValue.date().month(),
                vValue.date().day(),
                vValue.time().hour(),
                vValue.time().minute(),
            )

        return rInterviewAt

    def save(self):
        """Enregistre le suivi, ou le supprime si aucun statut n'est choisi."""
        vStatus = self.status_combo.currentData()
        vSource = self.offer["source"]
        vSourceId = self.offer["source_id"]

        try:
            if vStatus is None:
                delete_application(self.database_file, vSource, vSourceId)
            else:
                save_application(
                    self.database_file,
                    vSource,
                    vSourceId,
                    vStatus,
                    pFollowUpDate=self.get_follow_up_date(),
                    pNotes=self.notes_edit.toPlainText().strip(),
                    pFollowUpDays=self.get_follow_up_days(),
                    pInterviewAt=self.get_interview_at(),
                )

        except Exception:
            logger.exception(
                "Échec de l'enregistrement du suivi %s %s", vSource, vSourceId
            )

            self.application_label.setText("Le suivi n'a pas pu être enregistré.")

        else:
            self.load_application()
            self.changed.emit()

    def add_follow_up(self):
        """Enregistre une relance faite aujourd'hui et programme la suivante."""
        record_follow_up(
            self.database_file,
            self.offer["source"],
            self.offer["source_id"],
            pFollowUpDays=self.get_follow_up_days(),
        )

        self.load_application()
        self.changed.emit()
