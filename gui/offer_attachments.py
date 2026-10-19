"""Pièces jointes d'une offre : CV envoyé, lettre, échanges"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from job.presentation import format_date
from storage.attachments import (
    ALLOWED_EXTENSIONS,
    add_attachment,
    delete_attachment,
    get_attachment,
    get_attachments,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class AttachmentsPanel(QWidget):
    """Liste les fichiers joints à l'offre affichée et permet d'en ajouter."""

    def __init__(self, pDatabaseFile):
        """Construit la liste et ses boutons, vide tant qu'aucune offre n'est choisie."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.offer = None

        vTitle = QLabel("Pièces jointes")
        vTitle.setObjectName("fieldLabel")

        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(90)
        self.attachments_list.setToolTip("Double-clic pour ouvrir le fichier")
        self.attachments_list.itemDoubleClicked.connect(self.open_attachment)

        vAddButton = QPushButton("Joindre un fichier…")
        vAddButton.setObjectName("linkButton")
        vAddButton.setToolTip(
            "CV envoyé, lettre : " + ", ".join(ALLOWED_EXTENSIONS) + ", 10 Mo maximum"
        )
        vAddButton.clicked.connect(self.add_attachment)

        vDeleteButton = QPushButton("Supprimer")
        vDeleteButton.setObjectName("linkButton")
        vDeleteButton.clicked.connect(self.delete_attachment)

        vButtons = QHBoxLayout()
        vButtons.addWidget(vAddButton)
        vButtons.addWidget(vDeleteButton)
        vButtons.addStretch()

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(4)
        vLayout.addWidget(vTitle)
        vLayout.addWidget(self.attachments_list)
        vLayout.addLayout(vButtons)

    def set_offer(self, pOffer):
        """Affiche les pièces jointes d'une offre, ou vide la liste."""
        self.offer = pOffer
        self.load_attachments()

    def load_attachments(self):
        """Affiche les pièces jointes de l'offre."""
        self.attachments_list.clear()

        if self.offer is None:
            return

        try:
            vAttachments = get_attachments(
                self.database_file, self.offer["source"], self.offer["source_id"]
            )

        except Exception:
            logger.exception("Impossible de lire les pièces jointes")
            vAttachments = []

        for vAttachment in vAttachments:
            vItem = QListWidgetItem(
                f"{vAttachment['file_name']} · {format_date(vAttachment['added_at'])}"
            )
            vItem.setData(Qt.ItemDataRole.UserRole, vAttachment["id"])
            self.attachments_list.addItem(vItem)

    def add_attachment(self):
        """Joint un fichier choisi sur le disque à l'offre affichée."""
        vFilter = " ".join(f"*{vExtension}" for vExtension in ALLOWED_EXTENSIONS)

        vPath, _ = QFileDialog.getOpenFileName(
            self, "Joindre un fichier", str(Path.home()), f"Documents ({vFilter})"
        )

        if vPath:
            self.attach_file(vPath)

    def attach_file(self, pPath):
        """Range le fichier avec l'offre, ou explique pourquoi il est refusé."""
        try:
            add_attachment(
                self.database_file,
                self.offer["source"],
                self.offer["source_id"],
                Path(pPath).name,
                Path(pPath).read_bytes(),
                datetime.now(),
            )

        except ValueError as vException:
            QMessageBox.warning(self, "Pièce jointe refusée", str(vException))

        except Exception:
            logger.exception("Échec de l'ajout de la pièce jointe")

            QMessageBox.warning(
                self, "Pièce jointe", "Le fichier n'a pas pu être joint."
            )

        self.load_attachments()

    def open_attachment(self, pItem):
        """Ouvre une pièce jointe avec l'application associée à son type."""
        vAttachment = get_attachment(
            self.database_file, pItem.data(Qt.ItemDataRole.UserRole)
        )

        if vAttachment is not None and vAttachment["path"].exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(vAttachment["path"])))
        else:
            QMessageBox.warning(self, "Pièce jointe", "Le fichier est introuvable.")

    def delete_attachment(self):
        """Supprime la pièce jointe sélectionnée, après confirmation."""
        vItem = self.attachments_list.currentItem()

        if vItem is None:
            return

        vAnswer = QMessageBox.question(
            self, "Supprimer la pièce jointe", f"Supprimer « {vItem.text()} » ?"
        )

        if vAnswer == QMessageBox.StandardButton.Yes:
            delete_attachment(self.database_file, vItem.data(Qt.ItemDataRole.UserRole))
            self.load_attachments()
