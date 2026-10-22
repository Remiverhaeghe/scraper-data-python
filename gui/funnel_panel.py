"""Entonnoir des candidatures : envoyées, réponses, entretiens puis acceptées"""

from PySide6.QtCore import Qt
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
BAR_HEIGHT = 24

EMPTY_TEXT = (
    "Aucune candidature envoyée pour l'instant : l'entonnoir se remplira dès la "
    "première, en passant une offre au statut « Postulé »."
)


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
        """Affiche une barre par étape, à la couleur de sa carte statistique.

        Sans candidature envoyée, un message remplace quatre barres vides.
        """
        clear_layout(self.rows_layout)

        if not pFunnel or not pFunnel[0]["count"]:
            vEmpty = QLabel(EMPTY_TEXT)
            vEmpty.setObjectName("cardSubtitle")
            vEmpty.setWordWrap(True)
            self.rows_layout.addWidget(vEmpty, 0, 0, 1, 3)
            return

        for vRow, (vStage, vAccent) in enumerate(zip(pFunnel, STAGE_ACCENTS)):
            vColor, vBackground = ACCENTS[vAccent]

            vLabel = QLabel(vStage["label"])
            vLabel.setObjectName("fieldLabel")
            vLabel.setFixedWidth(LABEL_WIDTH)

            vBar = QProgressBar()
            vBar.setValue(vStage["share"])
            vBar.setFormat(f"{vStage['count']}  ·  {vStage['share']} %")
            # Hauteur fixée hors feuille de style : la grille la prend en compte et
            # ne coupe plus la dernière barre.
            vBar.setFixedHeight(BAR_HEIGHT)
            vBar.setStyleSheet(
                f"QProgressBar {{ background: {vBackground}; border: none; "
                "border-radius: 6px; text-align: center; }}"
                f"QProgressBar::chunk {{ background: {vColor}; border-radius: 6px; }}"
            )

            vConversion = QLabel(
                ""
                if vStage["conversion"] is None
                else f"{vStage['conversion']} % de l'étape précédente"
            )
            vConversion.setObjectName("cardSubtitle")

            vMiddle = Qt.AlignmentFlag.AlignVCenter
            self.rows_layout.addWidget(vLabel, vRow, 0, vMiddle)
            self.rows_layout.addWidget(vBar, vRow, 1, vMiddle)
            self.rows_layout.addWidget(vConversion, vRow, 2, vMiddle)
