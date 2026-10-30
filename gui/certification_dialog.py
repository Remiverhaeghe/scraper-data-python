"""Fenêtre d'une certification : obtention, organisme, numéro et documents"""

from datetime import date

from PySide6.QtCore import QDate, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.offer_attachments import AttachmentsPanel
from job.certifications import DOCUMENT_SOURCE, save_details, save_owned
from utils.logger import get_logger

logger = get_logger(__name__)

# Champs texte de la fenêtre : (clé enregistrée, libellé, exemple affiché)
TEXT_FIELDS = (
    ("organism", "Organisme certificateur", "ETS Global, AFNOR, Microsoft, Apave…"),
    ("number", "N° du certificat", "Numéro ou identifiant du candidat"),
    ("level", "Niveau ou score", "B2V-BR, 850 points, catégories 1A et 3…"),
    ("verify_link", "Lien de vérification", "https://… (Credly, Microsoft Learn…)"),
    ("funding_used", "Financement utilisé", "CPF, employeur, OPCO, France Travail…"),
)


def create_date_edit(pValue):
    """Retourne un champ date au format français, au jour donné ou à aujourd'hui."""

    rDateEdit = QDateEdit()
    rDateEdit.setCalendarPopup(True)
    rDateEdit.setDisplayFormat("dd/MM/yyyy")
    rDateEdit.setDate(
        QDate.fromString(pValue, "yyyy-MM-dd") if pValue else QDate.currentDate()
    )
    rDateEdit.setEnabled(bool(pValue))

    return rDateEdit


class CertificationDialog(QDialog):
    """Saisit l'obtention d'une certification, ses informations et ses documents."""

    def __init__(self, pDatabaseFile, pRow, pParent=None):
        """Construit la fenêtre à partir d'une ligne de build_overview."""
        super().__init__(pParent)

        self.database_file = pDatabaseFile
        self.row = pRow
        vDetails = pRow["details"]

        self.setWindowTitle(pRow["label"])
        self.setMinimumWidth(560)

        vHint = QLabel(f"{pRow['advice']}\n{pRow['funding']}")
        vHint.setObjectName("cardSubtitle")
        vHint.setWordWrap(True)

        self.owned_check = QCheckBox("Je l'ai, obtenue le")
        self.owned_check.setChecked(bool(pRow["obtained"]))
        self.obtained_edit = create_date_edit(pRow["obtained"])
        self.owned_check.toggled.connect(self.obtained_edit.setEnabled)

        self.expires_check = QCheckBox("Date indiquée sur le certificat")
        self.expires_check.setChecked(bool(vDetails.get("expires")))
        self.expires_check.setToolTip(
            "Sinon, la fin de validité est calculée avec la durée habituelle"
        )
        self.expires_edit = create_date_edit(
            vDetails.get("expires") or pRow["valid_until"]
        )
        self.expires_edit.setEnabled(bool(vDetails.get("expires")))
        self.expires_check.toggled.connect(self.expires_edit.setEnabled)

        vForm = QFormLayout()
        vForm.addRow("Obtention", self.create_row(self.owned_check, self.obtained_edit))

        self.fields = {}

        for vKey, vLabel, vPlaceholder in TEXT_FIELDS:
            vEdit = QLineEdit(vDetails.get(vKey, ""))
            vEdit.setPlaceholderText(vPlaceholder)
            self.fields[vKey] = vEdit
            vForm.addRow(vLabel, vEdit)

        vForm.insertRow(
            4, "Expire le", self.create_row(self.expires_check, self.expires_edit)
        )

        self.notes_edit = QPlainTextEdit(vDetails.get("notes", ""))
        self.notes_edit.setPlaceholderText(
            "Centre d'examen, recyclage prévu, remarques…"
        )
        self.notes_edit.setMaximumHeight(80)
        vForm.addRow("Notes", self.notes_edit)

        self.documents = AttachmentsPanel(
            pDatabaseFile, "Certificat, attestation, carte"
        )
        self.documents.set_offer({"source": DOCUMENT_SOURCE, "source_id": pRow["id"]})

        vDocumentsHint = QLabel(
            "Les documents sont rangés dès leur ajout, sur cet ordinateur uniquement."
        )
        vDocumentsHint.setObjectName("cardSubtitle")

        vLinkButton = QPushButton("Fiche de l'organisme")
        vLinkButton.setObjectName("linkButton")
        vLinkButton.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(pRow["link"]))
        )

        vButtons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        vButtons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        vButtons.button(QDialogButtonBox.StandardButton.Cancel).setText("Fermer")
        vButtons.accepted.connect(self.save)
        vButtons.rejected.connect(self.reject)

        vBottom = QHBoxLayout()
        vBottom.addWidget(vLinkButton)
        vBottom.addStretch()
        vBottom.addWidget(vButtons)

        vLayout = QVBoxLayout(self)
        vLayout.setSpacing(12)
        vLayout.addWidget(vHint)
        vLayout.addLayout(vForm)
        vLayout.addWidget(self.documents)
        vLayout.addWidget(vDocumentsHint)
        vLayout.addLayout(vBottom)

    @staticmethod
    def create_row(pCheck, pDateEdit):
        """Retourne une case à cocher suivie de son champ date."""

        rRow = QHBoxLayout()
        rRow.addWidget(pCheck)
        rRow.addWidget(pDateEdit)
        rRow.addStretch()

        return rRow

    def get_details(self):
        """Retourne les informations saisies, la date d'expiration en ISO."""

        rDetails = {vKey: vEdit.text() for vKey, vEdit in self.fields.items()}
        rDetails["notes"] = self.notes_edit.toPlainText()

        if self.expires_check.isChecked():
            rDetails["expires"] = self.expires_edit.date().toPython().isoformat()

        return rDetails

    def save(self):
        """Enregistre l'obtention et les informations, puis ferme la fenêtre."""
        vObtained = (
            self.obtained_edit.date().toPython()
            if self.owned_check.isChecked()
            else None
        )

        if vObtained is not None and vObtained > date.today():
            QMessageBox.warning(
                self, "Certification", "La date d'obtention est dans le futur."
            )
            return

        try:
            save_details(self.database_file, self.row["id"], self.get_details())
            save_owned(self.database_file, self.row["id"], vObtained)

        except ValueError as vException:
            QMessageBox.warning(self, "Certification", str(vException))
            return

        except Exception:
            logger.exception("Certification non enregistrée : %s", self.row["id"])
            QMessageBox.warning(
                self, "Certification", "La certification n'a pas pu être enregistrée."
            )
            return

        self.accept()
