"""Carte de l'état de l'application : un indicateur coloré par ligne"""

from datetime import datetime

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import clear_layout, create_card
from job.health import build_health

# Pastille de couleur de chaque indicateur
TONE_MARK = "●"


class HealthPanel(QWidget):
    """Résume les sauvegardes, la planification, les sources et la place occupée."""

    def __init__(self, pDatabaseFile):
        """Construit la carte ; les indicateurs sont lus par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

        self.rows_layout = QGridLayout()
        self.rows_layout.setHorizontalSpacing(10)
        self.rows_layout.setVerticalSpacing(6)
        self.rows_layout.setColumnStretch(2, 1)

        vCard, vCardLayout = create_card(
            "État de l'application",
            "Vert : tout va bien · orange : à surveiller · rouge : à corriger",
            pIcon="circle-check",
            pKey="logs/health",
        )
        vCardLayout.addLayout(self.rows_layout)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def refresh(self):
        """Recalcule les indicateurs."""
        clear_layout(self.rows_layout)

        for vRow, vCheck in enumerate(build_health(self.database_file, datetime.now())):
            vMark = QLabel(TONE_MARK)
            vMark.setStyleSheet(f"color: {COLORS[vCheck['tone']]};")

            vLabel = QLabel(vCheck["label"])
            vLabel.setObjectName("fieldLabel")

            vValue = QLabel(vCheck["value"])
            vValue.setWordWrap(True)

            self.rows_layout.addWidget(vMark, vRow, 0)
            self.rows_layout.addWidget(vLabel, vRow, 1)
            self.rows_layout.addWidget(vValue, vRow, 2)
