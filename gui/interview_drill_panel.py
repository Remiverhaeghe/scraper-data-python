"""Entraînement à l'oral : une question à la fois, réponse révélée puis auto-évaluée"""

from datetime import datetime

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.interview_drill import get_due_cards, grade_card
from utils.logger import get_logger

logger = get_logger(__name__)


class InterviewDrillPanel(QWidget):
    """Fait réviser à voix haute les questions d'entretien dues aujourd'hui."""

    def __init__(self, pDatabaseFile):
        """Construit la carte ; les questions sont lues par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.cards = []

        self.question_label = QLabel()
        self.question_label.setObjectName("activityTitle")
        self.question_label.setWordWrap(True)

        self.origin_label = QLabel()
        self.origin_label.setObjectName("cardSubtitle")

        self.answer_label = QLabel()
        self.answer_label.setWordWrap(True)
        self.answer_label.hide()

        self.reveal_button = create_button(
            "Voir ma réponse", "file-text", pIconColor=COLORS["primary"]
        )
        self.reveal_button.clicked.connect(self.reveal)

        self.known_button = create_button("Je savais", pObjectName="primaryButton")
        self.known_button.clicked.connect(lambda: self.grade(True))

        self.again_button = create_button("À revoir", "history")
        self.again_button.clicked.connect(lambda: self.grade(False))

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vButtons = QHBoxLayout()
        vButtons.addWidget(self.reveal_button)
        vButtons.addWidget(self.known_button)
        vButtons.addWidget(self.again_button)
        vButtons.addStretch()

        vCard, vCardLayout = create_card(
            "Entraînement à l'oral",
            "Répondez à voix haute, puis comparez à votre réponse préparée. Une "
            "question sue revient plus tard, une question à revoir dès demain.",
            pIcon="bot",
            pKey="profile/drill",
        )
        vCardLayout.addWidget(self.origin_label)
        vCardLayout.addWidget(self.question_label)
        vCardLayout.addWidget(self.answer_label)
        vCardLayout.addLayout(vButtons)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Relit les questions dues et affiche la première."""
        try:
            self.cards = get_due_cards(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de lire les questions d'entretien")

            self.cards = []

        self.show_card()

    def show_card(self):
        """Affiche la question en cours, réponse masquée, ou la fin de la série."""
        vCard = self.cards[0] if self.cards else None

        self.question_label.setText(
            vCard["question"]
            if vCard
            else "Aucune question à revoir aujourd'hui : préparez des réponses "
            "STAR ou notez les questions de vos entretiens."
        )
        self.origin_label.setText(
            f"{vCard['origin']} · {len(self.cards)} à revoir" if vCard else ""
        )
        self.answer_label.hide()
        self.reveal_button.setEnabled(vCard is not None)
        self.known_button.setEnabled(False)
        self.again_button.setEnabled(False)

    def reveal(self):
        """Montre la réponse préparée et propose l'auto-évaluation."""
        if not self.cards:
            return

        self.answer_label.setText(
            self.cards[0]["answer"]
            or "Pas de réponse écrite : préparez-la dans les réponses STAR."
        )
        self.answer_label.show()
        self.known_button.setEnabled(True)
        self.again_button.setEnabled(True)

    def grade(self, pKnown):
        """Enregistre l'auto-évaluation et passe à la question suivante."""
        if not self.cards:
            return

        try:
            grade_card(self.database_file, self.cards[0]["id"], pKnown, datetime.now())

        except Exception:
            logger.exception("Échec de l'enregistrement de l'entraînement")

            show_message(
                self.message_label, "La réponse n'a pas pu être notée.", "danger"
            )
            return

        self.cards.pop(0)
        self.show_card()
