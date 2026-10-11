"""Fenêtre de saisie manuelle d'une offre"""

from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from job.contract import CONTRACT_TYPES
from job.manual_offers import add_manual_offer
from utils.logger import get_logger

logger = get_logger(__name__)


class ManualOfferDialog(QDialog):
    """Saisit une offre trouvée ailleurs ; reste ouverte tant qu'elle est incomplète."""

    def __init__(self, pDatabaseFile, pParent=None):
        """Construit le formulaire, champs obligatoires signalés par un astérisque."""
        super().__init__(pParent)

        self.database_file = pDatabaseFile
        self.source_id = None

        self.setWindowTitle("Ajouter une offre")
        self.resize(620, 560)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Ex. Développeur Java")

        self.company_edit = QLineEdit()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://…")

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Texte de l'annonce : compétences, télétravail et salaire y sont repérés."
        )

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Ex. Lille")

        self.contract_combo = QComboBox()
        self.contract_combo.addItem("Non précisé", None)

        for vContract in CONTRACT_TYPES:
            self.contract_combo.addItem(vContract, vContract)

        self.salary_edit = QLineEdit()
        self.salary_edit.setPlaceholderText("Ex. 45 k€ brut annuel")

        self.remote_check = QCheckBox("Télétravail possible")

        vHint = QLabel("* obligatoire. Renseignez au moins le lien ou la description.")
        vHint.setObjectName("cardSubtitle")

        self.error_label = QLabel()
        self.error_label.setObjectName("warning")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        vForm = QFormLayout()
        vForm.addRow("Titre *", self.title_edit)
        vForm.addRow("Entreprise *", self.company_edit)
        vForm.addRow("Lien", self.url_edit)
        vForm.addRow("Description", self.description_edit)
        vForm.addRow("Lieu", self.location_edit)
        vForm.addRow("Contrat", self.contract_combo)
        vForm.addRow("Salaire annoncé", self.salary_edit)
        vForm.addRow("", self.remote_check)

        vButtons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        vButtons.button(QDialogButtonBox.StandardButton.Save).setText("Ajouter")
        vButtons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        vButtons.accepted.connect(self.save)
        vButtons.rejected.connect(self.reject)

        vLayout = QVBoxLayout(self)
        vLayout.addLayout(vForm)
        vLayout.addWidget(vHint)
        vLayout.addWidget(self.error_label)
        vLayout.addWidget(vButtons)

    def get_fields(self):
        """Retourne les champs saisis, sous les noms attendus par job.manual_offers."""
        rFields = {
            "title": self.title_edit.text(),
            "company": self.company_edit.text(),
            "url": self.url_edit.text(),
            "description": self.description_edit.toPlainText(),
            "location": self.location_edit.text(),
            "contract": self.contract_combo.currentData(),
            "salary_label": self.salary_edit.text(),
            "remote": "oui" if self.remote_check.isChecked() else None,
        }

        return rFields

    def save(self):
        """Crée l'offre, ou affiche ce qui manque sans fermer la fenêtre."""
        try:
            self.source_id = add_manual_offer(
                self.database_file, self.get_fields(), datetime.now()
            )

        except ValueError as vException:
            self.error_label.setText(str(vException))
            self.error_label.show()

        except Exception:
            logger.exception("Échec de l'ajout manuel d'une offre")

            self.error_label.setText("L'offre n'a pas pu être enregistrée.")
            self.error_label.show()

        else:
            self.accept()
