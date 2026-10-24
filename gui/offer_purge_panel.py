"""Panneau de purge des offres hors sujet : aperçu puis suppression confirmée"""

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.offer_purge import (
    add_excluded_words,
    find_offers_to_purge,
    load_excluded_words,
    parse_purge_words,
    purge_offers,
    save_excluded_words,
    suggest_excluded_words,
)
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
        self.excluded_words = []

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

        self.exclude_check = QCheckBox(
            "Exclure aussi ces mots des prochaines recherches"
        )
        self.exclude_check.setChecked(True)
        self.exclude_check.setToolTip(
            "Sans cela, les offres supprimées reviendraient à la prochaine recherche"
        )

        self.excluded_label = QLabel()
        self.excluded_label.setObjectName("cardSubtitle")
        self.excluded_label.setWordWrap(True)

        vEditButton = create_button("Modifier…", "list-checks")
        vEditButton.setToolTip("Mots qui écartent une offre dès sa récupération")
        vEditButton.clicked.connect(self.edit_excluded_words)

        vExcluded = QHBoxLayout()
        vExcluded.addWidget(self.excluded_label, 1)
        vExcluded.addWidget(vEditButton)

        # Mots typiques des offres ignorées, ajoutés d'un clic
        self.suggestions = []
        self.suggestion_label = QLabel()
        self.suggestion_label.setObjectName("cardSubtitle")
        self.suggestion_label.setWordWrap(True)

        self.suggestion_button = create_button("Exclure ces mots", "list-checks")
        self.suggestion_button.clicked.connect(self.add_suggestions)

        vSuggestions = QHBoxLayout()
        vSuggestions.addWidget(self.suggestion_label, 1)
        vSuggestions.addWidget(self.suggestion_button)

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
        vCardLayout.addWidget(self.exclude_check)
        vCardLayout.addWidget(self.message_label)
        vCardLayout.addLayout(vExcluded)
        vCardLayout.addLayout(vSuggestions)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

        self.reset_preview()
        self.show_excluded_words()

    def show_excluded_words(self):
        """Affiche les mots qui écartent une offre dès sa récupération."""
        try:
            vWords = load_excluded_words(self.database_file)

        except Exception:
            logger.exception("Impossible de lire les mots exclus")

            vWords = []

        self.excluded_words = vWords
        self.excluded_label.setText(
            "Mots exclus de toutes les recherches : " + ", ".join(vWords)
            if vWords
            else "Aucun mot exclu de toutes les recherches."
        )

        try:
            self.suggestions = suggest_excluded_words(self.database_file)

        except Exception:
            logger.exception("Impossible de proposer des mots exclus")

            self.suggestions = []

        self.suggestion_label.setText(
            "Souvent dans vos offres ignorées, jamais dans les retenues : "
            + ", ".join(f"{vWord} ({vCount})" for vWord, vCount in self.suggestions)
        )
        self.suggestion_label.setVisible(bool(self.suggestions))
        self.suggestion_button.setVisible(bool(self.suggestions))

    def add_suggestions(self):
        """Ajoute les mots suggérés à la liste des mots exclus."""
        add_excluded_words(self.database_file, [vWord for vWord, _ in self.suggestions])
        self.show_excluded_words()
        show_message(self.message_label, "Mots suggérés ajoutés aux mots exclus.")

    def edit_excluded_words(self):
        """Modifie la liste des mots exclus, séparés par des virgules."""
        vText, vAccepted = QInputDialog.getText(
            self,
            "Mots exclus de toutes les recherches",
            "Mots séparés par des virgules (vide : aucun) :",
            text=", ".join(self.excluded_words),
        )

        if not vAccepted:
            return

        try:
            save_excluded_words(self.database_file, vText)

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except Exception:
            logger.exception("Échec de l'enregistrement des mots exclus")

            show_message(
                self.message_label, "Les mots n'ont pas pu être enregistrés.", "danger"
            )
            return

        self.show_excluded_words()
        show_message(self.message_label, "Mots exclus enregistrés.")

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

            if self.exclude_check.isChecked():
                add_excluded_words(self.database_file, vWords)

        except Exception:
            logger.exception("Échec de la purge des offres")

            show_message(
                self.message_label,
                "La suppression a échoué, aucune offre n'a été retirée.",
                "danger",
            )
            return

        self.reset_preview()
        self.show_excluded_words()

        show_message(
            self.message_label,
            f"{vCount} offre(s) supprimée(s)"
            + (f", sauvegarde : {vBackupFile.name}" if vBackupFile else "")
            + (
                ". Ces mots écartent désormais les offres des prochaines recherches."
                if self.exclude_check.isChecked()
                else ". Elles pourront revenir à la prochaine recherche."
            ),
        )

        self.purged.emit(vCount)
