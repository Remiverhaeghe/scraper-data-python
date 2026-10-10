"""Histogramme simple dessiné avec QPainter"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from gui.theme import COLORS

# Hauteur réservée sous les barres pour les dates, au-dessus pour les valeurs
LABEL_HEIGHT = 18

# En dessous de cette largeur par barre, seul un libellé sur deux est affiché
MIN_LABEL_WIDTH = 40


class BarChart(QWidget):
    """Affiche une valeur par barre, avec son libellé en dessous."""

    def __init__(self):
        """Crée un histogramme vide."""
        super().__init__()

        self.values = []
        self.setMinimumHeight(160)

    def set_values(self, pValues):
        """Remplace les couples (libellé, valeur) affichés."""
        self.values = pValues
        self.update()

    def paintEvent(self, pEvent):
        """Dessine les barres proportionnellement à la plus grande valeur."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vWidth = self.width()
        vChartHeight = self.height() - 2 * LABEL_HEIGHT
        vMaximum = max((vValue for _, vValue in self.values), default=0) or 1

        vPainter.setPen(QColor(COLORS["border"]))
        vPainter.drawLine(
            0, LABEL_HEIGHT + vChartHeight, vWidth, LABEL_HEIGHT + vChartHeight
        )

        if self.values:
            vSlot = vWidth / len(self.values)
            vBarWidth = min(vSlot * 0.6, 28)

            for vIndex, (vLabel, vValue) in enumerate(self.values):
                vLeft = vIndex * vSlot + (vSlot - vBarWidth) / 2
                vHeight = vChartHeight * vValue / vMaximum
                vTop = LABEL_HEIGHT + vChartHeight - vHeight

                vPainter.setPen(Qt.PenStyle.NoPen)
                vPainter.setBrush(
                    QColor(COLORS["primary"] if vValue else COLORS["primary_light"])
                )
                vPainter.drawRoundedRect(
                    QRectF(vLeft, vTop, vBarWidth, max(vHeight, 3)), 4, 4
                )

                # Le dernier libellé, souvent le jour courant, reste toujours visible.
                vIsLabelled = (
                    vSlot >= MIN_LABEL_WIDTH or (len(self.values) - 1 - vIndex) % 2 == 0
                )

                if vIsLabelled:
                    vPainter.setPen(QColor(COLORS["muted"]))
                    # Libellé centré sous sa barre mais maintenu dans le widget
                    vLabelLeft = min(
                        max(vIndex * vSlot - vSlot / 2, 0), vWidth - 2 * vSlot
                    )

                    vPainter.drawText(
                        QRectF(
                            vLabelLeft,
                            LABEL_HEIGHT + vChartHeight,
                            vSlot * 2,
                            LABEL_HEIGHT,
                        ),
                        Qt.AlignmentFlag.AlignCenter,
                        vLabel,
                    )

                if vValue:
                    vPainter.setPen(QColor(COLORS["heading"]))
                    vPainter.drawText(
                        QRectF(
                            vIndex * vSlot, vTop - LABEL_HEIGHT, vSlot, LABEL_HEIGHT
                        ),
                        Qt.AlignmentFlag.AlignCenter,
                        str(vValue),
                    )

        vPainter.end()
