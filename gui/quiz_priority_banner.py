"""Bandeau de la Révision : thèmes demandés par les offres et encore sans question"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import FlowLayout, clear_layout, create_button, create_card
from job.quiz import load_active_quiz
from job.quiz_generation import build_empty_priority_themes
from utils.logger import get_logger

logger = get_logger(__name__)


class QuizPriorityBanner(QWidget):
    """Met en avant les thèmes à préparer en premier, avec leur demande ChatGPT."""

    # Libellé du thème dont la demande de questions est à préparer
    prepare_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit la carte, masquée tant qu'aucun thème n'est à préparer."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.buttons_layout = FlowLayout(8)

        vCard, vCardLayout = create_card(
            "À préparer en priorité",
            "Demandés dans vos offres, sans aucune question pour le moment : la "
            "demande ChatGPT est copiée d'un clic.",
            pIcon="target",
        )
        vCardLayout.addLayout(self.buttons_layout)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

        self.hide()

    def refresh(self):
        """Relit les thèmes prioritaires encore vides."""
        try:
            vThemes = build_empty_priority_themes(
                self.database_file, load_active_quiz(self.database_file)
            )

        except Exception:
            logger.exception("Impossible de calculer les thèmes à préparer")

            vThemes = []

        clear_layout(self.buttons_layout)

        for vTheme in vThemes:
            vButton = create_button(
                f"{vTheme['label']} · {vTheme['offer_count']} offre(s)",
                "bot",
                pIconColor=COLORS["primary"],
            )
            vButton.setToolTip("Copie la demande de questions pour ce thème")
            vButton.clicked.connect(
                lambda _=False, pLabel=vTheme["label"]: self.prepare_requested.emit(
                    pLabel
                )
            )
            self.buttons_layout.addWidget(vButton)

        self.setVisible(bool(vThemes))
