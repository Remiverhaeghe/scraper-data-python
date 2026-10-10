"""Panneau de détail d'une offre et de son suivi de candidature"""

from datetime import datetime

from PySide6.QtCore import QDate, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config import FOLLOW_UP_DAYS
from gui.offers_model import format_net_salary
from job.presentation import STATUS_LABELS, format_date, safe_url
from storage.job_applications import (
    delete_application,
    get_application,
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


class OfferDetailPanel(QWidget):
    """Affiche une offre et permet de mettre à jour son suivi."""

    application_changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit le panneau, vide tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None

        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.title_label.setWordWrap(True)

        self.company_label = QLabel()
        self.company_label.setObjectName("pageSubtitle")
        self.company_label.setWordWrap(True)

        self.open_button = QPushButton("Ouvrir l'offre")
        self.open_button.clicked.connect(self.open_offer)

        self.info_labels = {}

        vInfoForm = QFormLayout()

        for vKey, vLabel in (
            ("contract", "Contrat"),
            ("salary", "Net mensuel"),
            ("salary_label", "Salaire annoncé"),
            ("remote", "Télétravail"),
            ("benefits", "Avantages"),
            ("published_at", "Publiée le"),
            ("source_label", "Source"),
        ):
            self.info_labels[vKey] = QLabel()
            self.info_labels[vKey].setWordWrap(True)
            vInfoForm.addRow(vLabel, self.info_labels[vKey])

        self.description = QTextBrowser()

        vSummary = QVBoxLayout()
        vSummary.addWidget(self.title_label)
        vSummary.addWidget(self.company_label)
        vSummary.addWidget(self.open_button)
        vSummary.addLayout(vInfoForm)
        vSummary.addStretch()

        vSummaryWidget = QWidget()
        vSummaryWidget.setFixedWidth(340)
        vSummaryWidget.setLayout(vSummary)

        vApplicationGroup = self.create_application_group()
        vApplicationGroup.setFixedWidth(340)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(0, 12, 0, 0)
        vLayout.setSpacing(16)
        vLayout.addWidget(vSummaryWidget)
        vLayout.addWidget(self.description, 1)
        vLayout.addWidget(vApplicationGroup)

        self.setEnabled(False)

    def create_application_group(self):
        """Construit le formulaire de suivi de candidature."""
        self.status_combo = QComboBox()
        self.status_combo.addItem("Aucun suivi", None)

        for vStatus, vLabel in STATUS_LABELS.items():
            self.status_combo.addItem(vLabel, vStatus)

        self.follow_up_check = QCheckBox("Relance prévue le")

        self.follow_up_edit = QDateEdit()
        self.follow_up_edit.setCalendarPopup(True)
        self.follow_up_edit.setDisplayFormat("dd/MM/yyyy")

        self.follow_up_check.toggled.connect(self.follow_up_edit.setEnabled)

        vFollowUp = QHBoxLayout()
        vFollowUp.addWidget(self.follow_up_check)
        vFollowUp.addWidget(self.follow_up_edit)
        vFollowUp.addStretch()

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Notes")

        vSaveButton = QPushButton("Enregistrer")
        vSaveButton.setObjectName("primaryButton")
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

        rGroup = QGroupBox("Suivi")

        vLayout = QVBoxLayout(rGroup)
        vLayout.addWidget(self.status_combo)
        vLayout.addLayout(vFollowUp)
        vLayout.addWidget(self.notes_edit)
        vLayout.addLayout(vButtons)
        vLayout.addWidget(self.application_label)

        return rGroup

    def show_offer(self, pOffer):
        """Affiche une offre préparée par prepare_offer, ou vide le panneau."""
        self.offer = pOffer
        self.setEnabled(pOffer is not None)

        vOffer = pOffer or {}

        self.title_label.setText(vOffer.get("title") or "Sans titre")
        self.company_label.setText(
            " · ".join(
                vValue
                for vValue in (vOffer.get("company"), vOffer.get("location"))
                if vValue
            )
        )
        self.open_button.setEnabled(safe_url(vOffer.get("url")) != "#")

        vRemote = vOffer.get("remote")

        vInfos = {
            "contract": vOffer.get("contract"),
            "salary": format_net_salary(vOffer),
            "salary_label": vOffer.get("salary_label"),
            "remote": None if vRemote is None else ("Oui" if vRemote else "Non"),
            "benefits": ", ".join(vOffer.get("benefits") or []),
            "published_at": format_date(vOffer.get("published_at")),
            "source_label": vOffer.get("source_label"),
        }

        for vKey, vLabel in self.info_labels.items():
            vLabel.setText(str(vInfos[vKey] or "Non renseigné"))

        # Texte brut : une description ne doit jamais être interprétée en HTML.
        self.description.setPlainText(vOffer.get("description") or "")

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
            else QDate.currentDate().addDays(FOLLOW_UP_DAYS)
        )

        self.notes_edit.setPlainText(vApplication.get("notes") or "")
        self.follow_up_button.setVisible(
            vApplication.get("status") in FOLLOW_UP_STATUSES
        )
        self.application_label.setText(describe_application(vApplication))

    def get_follow_up_date(self):
        """Retourne la date de relance saisie, ou None si aucune n'est prévue."""
        rDate = None

        if self.follow_up_check.isChecked():
            vDate = self.follow_up_edit.date()
            rDate = datetime(vDate.year(), vDate.month(), vDate.day())

        return rDate

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
                )

        except Exception:
            logger.exception(
                "Échec de l'enregistrement du suivi %s %s", vSource, vSourceId
            )

            self.application_label.setText("Le suivi n'a pas pu être enregistré.")

        else:
            self.load_application()
            self.application_changed.emit()

    def add_follow_up(self):
        """Enregistre une relance faite aujourd'hui et programme la suivante."""
        record_follow_up(
            self.database_file, self.offer["source"], self.offer["source_id"]
        )

        self.load_application()
        self.application_changed.emit()

    def open_offer(self):
        """Ouvre l'offre dans le navigateur, uniquement en http ou https."""
        vUrl = safe_url(self.offer.get("url") if self.offer else None)

        if vUrl != "#":
            QDesktopServices.openUrl(QUrl(vUrl))
