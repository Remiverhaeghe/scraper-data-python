"""Bandeau de la Révision : thèmes demandés par les offres et encore sans question,
puis thèmes à renforcer d'après l'auto-évaluation du profil"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import FlowLayout, clear_layout, create_button, create_card
from job.profile import load_profile
from job.quiz import load_active_quiz
from job.quiz_generation import build_empty_priority_themes
from job.self_assessment import find_weak_themes
from utils.logger import get_logger

logger = get_logger(__name__)


class QuizPriorityBanner(QWidget):
    """Met en avant les thèmes à préparer en premier, avec leur demande ChatGPT."""

    # Libellé du thème dont la demande de questions est à préparer
    prepare_requested = Signal(str)

    # Clé du thème à réviser, jugé faible dans l'auto-évaluation
    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit la carte, masquée tant qu'aucun thème n'est à préparer."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.buttons_layout = FlowLayout(8)
        self.weak_layout = FlowLayout(8)

        self.empty_title = QLabel(
            "Demandés dans vos offres, sans question : la demande ChatGPT est "
            "copiée d'un clic."
        )
        self.empty_title.setObjectName("cardSubtitle")
        self.weak_title = QLabel(
            "À renforcer d'après votre auto-évaluation (page Profil) :"
        )
        self.weak_title.setObjectName("cardSubtitle")

        vCard, vCardLayout = create_card("À préparer en priorité", pIcon="target")
        vCardLayout.addWidget(self.empty_title)
        vCardLayout.addLayout(self.buttons_layout)
        vCardLayout.addWidget(self.weak_title)
        vCardLayout.addLayout(self.weak_layout)

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

        vWeakThemes = self.read_weak_themes()
        clear_layout(self.weak_layout)

        for vTheme in vWeakThemes:
            vButton = create_button(
                f"{vTheme['label']} · {vTheme['skill']} {vTheme['level']}/10",
                "graduation-cap",
                pIconColor=COLORS["warning"],
            )
            vButton.setToolTip("Réviser ce thème en répétition espacée")
            vButton.clicked.connect(
                lambda _=False, pKey=vTheme["key"]: self.theme_requested.emit(pKey)
            )
            self.weak_layout.addWidget(vButton)

        self.empty_title.setVisible(bool(vThemes))
        self.weak_title.setVisible(bool(vWeakThemes))
        self.setVisible(bool(vThemes or vWeakThemes))

    def read_weak_themes(self):
        """Retourne les thèmes liés aux compétences jugées faibles, ou une liste vide."""
        try:
            rThemes = find_weak_themes(
                load_profile(self.database_file), load_active_quiz(self.database_file)
            )

        except Exception:
            logger.exception("Impossible de lire l'auto-évaluation")

            rThemes = []

        return rThemes
