"""Entonnoir des candidatures : envoyées, réponses, entretiens puis acceptées"""

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gui.theme import ACCENTS
from gui.widgets import clear_layout, create_card

# Couleur de chaque étape, celles des cartes statistiques de la page
STAGE_ACCENTS = ("blue", "green", "amber", "purple")

LABEL_WIDTH = 90


class FunnelPanel(QWidget):
    """Montre la part des envois qui atteint chaque étape et le passage entre elles."""

    def __init__(self):
        """Construit la carte vide ; remplie par set_funnel."""
        super().__init__()

        self.rows_layout = QGridLayout()
        self.rows_layout.setHorizontalSpacing(12)
        self.rows_layout.setVerticalSpacing(8)
        self.rows_layout.setColumnStretch(1, 1)

        vCard, vCardLayout = create_card(
            "Entonnoir des candidatures",
            "Part des candidatures envoyées qui atteint chaque étape, et passage "
            "depuis l'étape précédente.",
            pIcon="send",
        )
        vCardLayout.addLayout(self.rows_layout)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def set_funnel(self, pFunnel):
        """Affiche une barre par étape, à la couleur de sa carte statistique."""
        clear_layout(self.rows_layout)

        for vRow, (vStage, vAccent) in enumerate(zip(pFunnel, STAGE_ACCENTS)):
            vColor, vBackground = ACCENTS[vAccent]

            vLabel = QLabel(vStage["label"])
            vLabel.setObjectName("fieldLabel")
            vLabel.setFixedWidth(LABEL_WIDTH)

            vBar = QProgressBar()
            vBar.setValue(vStage["share"])
            vBar.setFormat(f"{vStage['count']}  ·  {vStage['share']} %")
            vBar.setStyleSheet(
                f"QProgressBar {{ background: {vBackground}; border: none; "
                "border-radius: 6px; min-height: 22px; text-align: center; }}"
                f"QProgressBar::chunk {{ background: {vColor}; border-radius: 6px; }}"
            )

            vConversion = QLabel(
                ""
                if vStage["conversion"] is None
                else f"{vStage['conversion']} % de l'étape précédente"
            )
            vConversion.setObjectName("cardSubtitle")

            self.rows_layout.addWidget(vLabel, vRow, 0)
            self.rows_layout.addWidget(vBar, vRow, 1)
            self.rows_layout.addWidget(vConversion, vRow, 2)
