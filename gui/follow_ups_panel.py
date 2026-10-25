"""Panneau des relances de la semaine : brouillons à copier et relances à noter"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    clear_layout,
    create_button,
    create_card,
    create_pill,
    show_message,
)
from job.application_tracking import mark_followed_up, send_follow_up
from job.notification import describe_follow_up
from utils.logger import get_logger
from utils.mailer import get_missing_email_settings

logger = get_logger(__name__)

# Séparateur des brouillons copiés ensemble, un par entreprise
DRAFT_SEPARATOR = "\n\n----------\n\n"


class FollowUpDialog(QDialog):
    """Relecture d'une relance avant envoi : adresse du recruteur et message."""

    def __init__(self, pParent, pFollowUp):
        """Construit les deux champs, pré-remplis, et les boutons Envoyer et Annuler."""
        super().__init__(pParent)

        self.setWindowTitle("Envoyer la relance")
        self.resize(560, 460)

        self.recipient_edit = QLineEdit(pFollowUp.get("contact_email") or "")
        self.recipient_edit.setPlaceholderText("recruteur@entreprise.fr")
        self.recipient_edit.setMaxLength(254)

        self.draft_edit = QPlainTextEdit(pFollowUp["draft"])

        vButtons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vButtons.button(QDialogButtonBox.StandardButton.Ok).setText("Envoyer")
        vButtons.accepted.connect(self.accept)
        vButtons.rejected.connect(self.reject)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(QLabel("Adresse du recruteur"))
        vLayout.addWidget(self.recipient_edit)
        vLayout.addWidget(QLabel("Message, la première ligne en est l'objet"))
        vLayout.addWidget(self.draft_edit, 1)
        vLayout.addWidget(vButtons)


class FollowUpsPanel(QWidget):
    """Liste les relances en retard ou prévues dans les sept jours."""

    changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit la carte vide ; remplie par set_follow_ups."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.follow_ups = []

        self.copy_all_button = create_button(
            "Copier tous les messages", "copy", pIconColor=COLORS["primary"]
        )
        self.copy_all_button.clicked.connect(self.copy_all)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(10)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Relances de la semaine",
            "Un brouillon par candidature, à relire avant envoi. Notez la relance "
            "une fois le message parti : la suivante est programmée.",
            pIcon="bell-ring",
            pActions=[self.copy_all_button],
        )
        vCardLayout.addLayout(self.rows_layout)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def set_follow_ups(self, pFollowUps):
        """Affiche une ligne par relance, la plus urgente en tête."""
        self.follow_ups = pFollowUps

        clear_layout(self.rows_layout)

        for vFollowUp in pFollowUps:
            self.rows_layout.addWidget(self.create_row(vFollowUp))

        if not pFollowUps:
            vEmpty = QLabel("Aucune relance prévue dans les sept prochains jours.")
            vEmpty.setObjectName("cardSubtitle")
            self.rows_layout.addWidget(vEmpty)

        self.copy_all_button.setEnabled(bool(pFollowUps))

    def create_row(self, pFollowUp):
        """Construit la ligne d'une relance : offre, échéance et actions."""
        vTitle = QLabel(pFollowUp["title"] or "Offre sans titre")
        vTitle.setObjectName("activityTitle")
        vTitle.setWordWrap(True)

        vDetail = QLabel(describe_follow_up(pFollowUp))
        vDetail.setObjectName("cardSubtitle")
        vDetail.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(vDetail)

        vCopyButton = create_button("Copier le message", "copy")
        vCopyButton.clicked.connect(
            lambda: self.copy_drafts([pFollowUp], "Message copié.")
        )

        vSendButton = create_button("Envoyer…", "send")
        vSendButton.setToolTip("Relire le message puis l'envoyer depuis votre Gmail")
        vSendButton.setEnabled(not get_missing_email_settings())
        vSendButton.clicked.connect(lambda: self.send(pFollowUp))

        vDoneButton = create_button("Relance faite", pObjectName="primaryButton")
        vDoneButton.clicked.connect(lambda: self.mark_done(pFollowUp))

        rRow = QWidget()

        vLayout = QHBoxLayout(rRow)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(10)
        vLayout.addWidget(
            create_pill(
                *(
                    ("Remerciement", "success")
                    if pFollowUp.get("kind") == "thanks"
                    else (
                        ("En retard", "warning")
                        if pFollowUp["follow_up_due"]
                        else ("Cette semaine", "primary")
                    )
                )
            ),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        vLayout.addLayout(vTexts, 1)
        vLayout.addWidget(vCopyButton)
        vLayout.addWidget(vSendButton)
        vLayout.addWidget(vDoneButton)

        return rRow

    def copy_drafts(self, pFollowUps, pMessage):
        """Copie les brouillons dans le presse-papiers."""
        QApplication.clipboard().setText(
            DRAFT_SEPARATOR.join(vFollowUp["draft"] for vFollowUp in pFollowUps)
        )

        show_message(self.message_label, pMessage)

    def copy_all(self):
        """Copie tous les brouillons de la semaine, séparés les uns des autres."""
        self.copy_drafts(
            self.follow_ups, f"{len(self.follow_ups)} message(s) copié(s)."
        )

    def send(self, pFollowUp):
        """Ouvre le message à relire, puis l'envoie et note la relance."""
        vDialog = FollowUpDialog(self, pFollowUp)

        if vDialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            send_follow_up(
                self.database_file,
                pFollowUp["source"],
                pFollowUp["source_id"],
                vDialog.recipient_edit.text(),
                vDialog.draft_edit.toPlainText(),
                datetime.now(),
            )

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")
            return

        except OSError:
            logger.exception("Échec de l'envoi de la relance")

            show_message(
                self.message_label,
                "L'envoi a échoué : vérifiez la connexion et réessayez.",
                "danger",
            )
            return

        show_message(self.message_label, "Relance envoyée et notée.")

        self.changed.emit()

    def mark_done(self, pFollowUp):
        """Note la relance comme faite aujourd'hui."""
        try:
            mark_followed_up(
                self.database_file,
                pFollowUp["source"],
                pFollowUp["source_id"],
                datetime.now(),
            )

        except Exception:
            logger.exception("Échec de l'enregistrement de la relance")

            show_message(
                self.message_label, "La relance n'a pas pu être notée.", "danger"
            )
            return

        show_message(self.message_label, "Relance notée, la suivante est programmée.")

        self.changed.emit()
