"""Mots-clés de recherche proposés à partir du profil, en pastilles cliquables"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from gui.widgets import FlowLayout, clear_layout
from job.profile import load_profile, suggest_keywords
from utils.logger import get_logger

logger = get_logger(__name__)


class KeywordSuggestions(QWidget):
    """Propose les intitulés et compétences du profil comme mots-clés."""

    keyword_chosen = Signal(str)

    def __init__(self):
        """Construit la ligne vide, masquée tant qu'aucun mot-clé n'est proposé."""
        super().__init__()

        vTitle = QLabel("Depuis mon profil")
        vTitle.setObjectName("cardSubtitle")
        vTitle.setToolTip("Cliquez pour reprendre le mot-clé")

        self.chips_layout = FlowLayout()

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(10)
        vLayout.addWidget(vTitle, 0, Qt.AlignmentFlag.AlignTop)
        vLayout.addLayout(self.chips_layout, 1)

        self.hide()

    def refresh(self, pDatabaseFile):
        """Relit le profil et affiche une pastille par mot-clé proposé."""
        vKeywords = []

        try:
            vKeywords = suggest_keywords(load_profile(pDatabaseFile))

        except Exception:
            logger.exception("Impossible de lire le profil pour les suggestions")

        clear_layout(self.chips_layout)

        for vKeyword in vKeywords:
            vButton = QPushButton(vKeyword)
            vButton.setObjectName("chipButton")
            vButton.setCursor(Qt.CursorShape.PointingHandCursor)
            vButton.clicked.connect(
                lambda _=False, pKeyword=vKeyword: self.keyword_chosen.emit(pKeyword)
            )
            self.chips_layout.addWidget(vButton)

        self.setVisible(bool(vKeywords))
