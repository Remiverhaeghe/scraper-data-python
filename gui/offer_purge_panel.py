"""Panneau de purge des offres hors sujet : aperçu puis suppression confirmée"""

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.offer_purge import find_offers_to_purge, parse_purge_words, purge_offers
from utils.logger import get_logger

logger = get_logger(__name__)

PREVIEW_HEIGHT = 220


class OfferPurgePanel(QWidget):
    """Supprime les offres dont le titre contient des mots choisis, après aperçu."""

    purged = Signal(int)

    def __init__(self, pDatabaseFile):
        """Construit la saisie des mots, l'aperçu et le bouton de suppression."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.preview_words = []

        self.words_edit = QLineEdit()
        self.words_edit.setPlaceholderText("Ex. stage, alternance, commercial")
        self.words_edit.returnPressed.connect(self.preview)
        # Une saisie modifiée rend l'aperçu périmé : il faut le relancer.
        self.words_edit.textChanged.connect(self.reset_preview)

        vPreviewButton = create_button("Aperçu", "search", pIconColor=COLORS["primary"])
        vPreviewButton.clicked.connect(self.preview)

        self.delete_button = create_button(
            "Supprimer", "trash-2", "dangerButton", COLORS["danger"]
        )
        self.delete_button.clicked.connect(self.delete)

        vInput = QHBoxLayout()
        vInput.setSpacing(10)
        vInput.addWidget(self.words_edit, 1)
        vInput.addWidget(vPreviewButton)
        vInput.addWidget(self.delete_button)

        self.preview_list = QListWidget()
        self.preview_list.setMaximumHeight(PREVIEW_HEIGHT)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Offres hors sujet",
            "Supprime les offres dont le titre contient l'un des mots. Les offres "
            "avec candidature, relance ou pièce jointe sont toujours gardées, et la "
            "base est sauvegardée avant suppression.",
            pKey="quality/purge",
        )
        vCardLayout.addLayout(vInput)
        vCardLayout.addWidget(self.preview_list)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

        self.reset_preview()

    def reset_preview(self):
        """Vide l'aperçu et désactive la suppression jusqu'au prochain aperçu."""
        self.preview_words = []
        self.preview_list.clear()
        self.preview_list.hide()
        self.delete_button.setEnabled(False)
        self.delete_button.setText("Supprimer")

    def preview(self):
        """Liste les offres qui seraient supprimées avec les mots saisis."""
        self.reset_preview()

        try:
            vWords = parse_purge_words(self.words_edit.text())
            vOffers = find_offers_to_purge(self.database_file, vWords)

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except Exception:
            logger.exception("Échec de l'aperçu de la purge des offres")

            show_message(
                self.message_label, "L'aperçu n'a pas pu être calculé.", "danger"
            )
            return

        for vOffer in vOffers:
            self.preview_list.addItem(
                " · ".join(
                    vPart
                    for vPart in (vOffer["title"], vOffer["company"], vOffer["source"])
                    if vPart
                )
            )

        self.preview_words = vWords
        self.preview_list.setVisible(bool(vOffers))
        self.delete_button.setEnabled(bool(vOffers))
        self.delete_button.setText(f"Supprimer {len(vOffers)} offre(s)")

        show_message(
            self.message_label,
            (
                f"{len(vOffers)} offre(s) seraient supprimées."
                if vOffers
                else "Aucune offre à supprimer pour ces mots."
            ),
            "warning" if vOffers else "success",
        )

    def delete(self):
        """Supprime les offres de l'aperçu, après confirmation."""
        if (
            QMessageBox.question(
                self,
                "Supprimer les offres hors sujet",
                f"{self.preview_list.count()} offre(s) seront supprimées après "
                "sauvegarde de la base. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        vWords = self.preview_words

        try:
            vCount, vBackupFile = purge_offers(
                self.database_file, vWords, datetime.now()
            )

        except Exception:
            logger.exception("Échec de la purge des offres")

            show_message(
                self.message_label,
                "La suppression a échoué, aucune offre n'a été retirée.",
                "danger",
            )
            return

        self.reset_preview()

        show_message(
            self.message_label,
            f"{vCount} offre(s) supprimée(s)"
            + (f", sauvegarde : {vBackupFile.name}" if vBackupFile else "")
            + ". Ajoutez ces mots aux « Mots à exclure du titre » de vos "
            "recherches pour qu'elles ne reviennent pas.",
        )

        self.purged.emit(vCount)
