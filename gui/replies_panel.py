"""Panneau des réponses de recruteurs : statut proposé d'après les messages Gmail"""

import imaplib
import threading
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import (
    clear_layout,
    create_button,
    create_card,
    create_pill,
    show_message,
)
from job.application_replies import apply_reply, check_replies, mark_reply_handled
from job.presentation import STATUS_LABELS
from utils.logger import get_logger

logger = get_logger(__name__)


class RepliesPanel(QWidget):
    """Lit Gmail à la demande et propose le statut annoncé par chaque réponse."""

    changed = Signal()
    # Émis depuis le fil de lecture : (réponses, message, tonalité)
    replies_read = Signal(object, object, str)

    def __init__(self, pDatabaseFile):
        """Construit la carte vide ; remplie après lecture des messages."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.read_button = create_button(
            "Lire mes réponses Gmail", "inbox", pIconColor=COLORS["primary"]
        )
        self.read_button.clicked.connect(self.read)
        self.replies_read.connect(self.show_replies)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(10)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vCard, vCardLayout = create_card(
            "Réponses des recruteurs",
            "Lit vos messages Gmail des 30 derniers jours, en lecture seule, et "
            "propose le statut annoncé : refus ou entretien. Rien du message n'est "
            "enregistré.",
            pIcon="inbox",
            pActions=[self.read_button],
        )
        vCardLayout.addLayout(self.rows_layout)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def read(self):
        """Lance la lecture des messages hors du fil de l'interface."""
        self.read_button.setEnabled(False)
        show_message(self.message_label, "Lecture de Gmail en cours…", None)

        threading.Thread(target=self.run_read, daemon=True).start()

    def run_read(self):
        """Lit les réponses dans un fil séparé et transmet le résultat par signal."""
        try:
            self.replies_read.emit(
                check_replies(self.database_file, datetime.now()), None, "success"
            )

        except ValueError as vException:
            self.replies_read.emit([], str(vException), "warning")

        except (OSError, imaplib.IMAP4.error):
            logger.exception("Lecture de Gmail impossible")
            self.replies_read.emit(
                [],
                "Gmail injoignable ou mot de passe d'application refusé : voir les "
                "journaux.",
                "danger",
            )

    def show_replies(self, pReplies, pMessage, pTone):
        """Affiche une ligne par statut proposé, ou le message d'erreur."""
        self.read_button.setEnabled(True)
        clear_layout(self.rows_layout)

        for vReply in pReplies:
            self.rows_layout.addWidget(self.create_row(vReply))

        show_message(
            self.message_label,
            pMessage
            or (
                f"{len(pReplies)} réponse(s) à traiter."
                if pReplies
                else "Aucune réponse de recruteur à appliquer sur 30 jours."
            ),
            pTone,
        )

    def create_row(self, pReply):
        """Construit la ligne d'une réponse : candidature, message et actions."""
        vTitle = QLabel(pReply["title"] or "Offre sans titre")
        vTitle.setObjectName("activityTitle")
        vTitle.setWordWrap(True)

        vDetail = QLabel(
            " · ".join(
                vPart
                for vPart in (
                    pReply["company"],
                    f"« {pReply['subject']} »",
                    pReply["date"].strftime("%d/%m") if pReply["date"] else None,
                    (
                        f"entretien le {pReply['interview_at']:%d/%m/%Y à %H:%M}"
                        if pReply.get("interview_at")
                        else None
                    ),
                )
                if vPart
            )
        )
        vDetail.setObjectName("cardSubtitle")
        vDetail.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(2)
        vTexts.addWidget(vTitle)
        vTexts.addWidget(vDetail)

        rRow = QWidget()

        vApplyButton = create_button("Appliquer", pObjectName="primaryButton")
        vApplyButton.clicked.connect(lambda: self.handle(rRow, pReply, True))

        vIgnoreButton = create_button("Ignorer")
        vIgnoreButton.clicked.connect(lambda: self.handle(rRow, pReply, False))

        vLayout = QHBoxLayout(rRow)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(10)
        vLayout.addWidget(
            create_pill(
                STATUS_LABELS[pReply["status"]],
                "warning" if pReply["status"] == "REJECTED" else "success",
            ),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        vLayout.addLayout(vTexts, 1)
        vLayout.addWidget(vApplyButton)
        vLayout.addWidget(vIgnoreButton)

        return rRow

    def handle(self, pRow, pReply, pApply):
        """Applique le statut proposé ou ignore le message, puis retire la ligne."""
        if pApply:
            apply_reply(self.database_file, pReply, datetime.now())
            vText = f"Statut « {STATUS_LABELS[pReply['status']]} » appliqué."
        else:
            mark_reply_handled(self.database_file, pReply["message_id"])
            vText = "Réponse ignorée."

        pRow.deleteLater()
        show_message(self.message_label, vText)

        if pApply:
            self.changed.emit()
