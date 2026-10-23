"""Fenêtre de saisie d'une candidature spontanée"""

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.widgets import show_message
from job.manual_offers import add_spontaneous_application
from utils.logger import get_logger

logger = get_logger(__name__)


class SpontaneousDialog(QDialog):
    """Saisit l'entreprise, le poste visé, un lien et une note, puis enregistre."""

    def __init__(self, pParent, pDatabaseFile):
        """Construit le formulaire vide."""
        super().__init__(pParent)

        self.database_file = pDatabaseFile
        self.setWindowTitle("Candidature spontanée")
        self.resize(520, 260)

        self.company_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Développeur Java")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Site carrière ou page de contact")
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Envoyée à la RH par e-mail")

        vForm = QFormLayout()
        vForm.addRow("Entreprise", self.company_edit)
        vForm.addRow("Poste visé", self.title_edit)
        vForm.addRow("Lien", self.url_edit)
        vForm.addRow("Note", self.note_edit)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        vButtons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        vButtons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        vButtons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        vButtons.accepted.connect(self.save)
        vButtons.rejected.connect(self.reject)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(
            QLabel(
                "Pour une entreprise sans offre publiée : la candidature rejoint "
                "la colonne Postulé, avec sa relance programmée."
            )
        )
        vLayout.addLayout(vForm)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(vButtons)

    def save(self):
        """Enregistre la candidature ; la fenêtre reste ouverte en cas d'erreur."""
        try:
            add_spontaneous_application(
                self.database_file,
                self.company_edit.text().strip(),
                self.title_edit.text().strip(),
                self.url_edit.text().strip(),
                self.note_edit.text().strip(),
                datetime.now(),
            )

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        self.accept()
