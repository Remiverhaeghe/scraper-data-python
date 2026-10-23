"""Grille d'auto-évaluation : un niveau de 0 à 10 par compétence"""

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    align_spin_box,
    clear_layout,
    create_button,
    create_card,
    show_message,
)
from job.profile import load_profile
from job.self_assessment import (
    KNOWN_LEVEL,
    MAX_LEVEL,
    WEAK_LEVEL,
    build_grid,
    save_skill_levels,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Compétences par ligne de la grille : deux colonnes « compétence, niveau »
GRID_COLUMNS = 2


class SelfAssessmentPanel(QWidget):
    """Note chaque compétence ; le score des offres et la révision en tiennent compte."""

    def __init__(self, pDatabaseFile):
        """Construit la carte ; la grille est remplie par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.spins = {}

        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(6)

        self.new_skill_edit = QLineEdit()
        self.new_skill_edit.setPlaceholderText("Autre compétence à noter")
        self.new_skill_edit.returnPressed.connect(self.add_skill)

        vAddButton = create_button("Ajouter", pIconColor=COLORS["primary"])
        vAddButton.clicked.connect(self.add_skill)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.new_skill_edit, 1)
        vActions.addWidget(vAddButton)
        vActions.addWidget(vSaveButton)

        vCard, vCardLayout = create_card(
            "Auto-évaluation des compétences",
            f"Niveau de 0 (inconnue) à {MAX_LEVEL}. À partir de {KNOWN_LEVEL}, la "
            f"compétence compte dans le score des offres ; de 1 à {WEAK_LEVEL}, ses "
            "thèmes sont proposés en priorité dans la Révision.",
            pIcon="target",
            pKey="profile/self_assessment",
        )
        vCardLayout.addLayout(self.grid_layout)
        vCardLayout.addLayout(vActions)
        vCardLayout.addWidget(self.message_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Relit la grille enregistrée."""
        try:
            vGrid = build_grid(load_profile(self.database_file))

        except Exception:
            logger.exception("Impossible de lire l'auto-évaluation")
            vGrid = []

        self.show_grid(vGrid)

    def show_grid(self, pGrid):
        """Affiche une ligne par compétence, avec son niveau."""
        clear_layout(self.grid_layout)
        self.spins = {}

        for vIndex, (vSkill, vLevel) in enumerate(pGrid):
            self.add_row(vIndex, vSkill, vLevel)

    def add_row(self, pIndex, pSkill, pLevel):
        """Ajoute une compétence et son niveau à la grille."""
        vSpin = align_spin_box(QSpinBox())
        vSpin.setRange(0, MAX_LEVEL)
        vSpin.setSpecialValueText("—")
        vSpin.setValue(pLevel)

        vRow, vColumn = divmod(pIndex, GRID_COLUMNS)
        self.grid_layout.addWidget(QLabel(pSkill), vRow, 2 * vColumn)
        self.grid_layout.addWidget(vSpin, vRow, 2 * vColumn + 1)
        self.spins[pSkill] = vSpin

    def add_skill(self):
        """Ajoute à la grille la compétence saisie, si elle n'y est pas déjà."""
        vSkill = self.new_skill_edit.text().strip()

        if vSkill and vSkill.lower() not in {vName.lower() for vName in self.spins}:
            self.add_row(len(self.spins), vSkill, 0)

        self.new_skill_edit.clear()

    def save(self):
        """Enregistre les niveaux saisis."""
        try:
            vGrid = save_skill_levels(
                self.database_file,
                {vSkill: vSpin.value() for vSkill, vSpin in self.spins.items()},
            )

        except Exception:
            logger.exception("Auto-évaluation non enregistrée")
            show_message(
                self.message_label,
                "L'auto-évaluation n'a pas pu être enregistrée.",
                "danger",
            )
            return

        self.show_grid(vGrid)
        show_message(
            self.message_label,
            f"{sum(1 for _, vLevel in vGrid if vLevel)} compétence(s) notée(s).",
        )
