"""Histogramme et camembert dessinés avec QPainter"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from gui.theme import COLORS

# Hauteur réservée sous les barres pour les libellés, au-dessus pour les valeurs
LABEL_HEIGHT = 18

# Hauteur d'une ligne de la légende affichée lorsqu'il y a plusieurs séries
LEGEND_ROW_HEIGHT = 18

# En dessous de cette largeur par groupe de barres, un libellé sur deux est affiché
MIN_LABEL_WIDTH = 40


def draw_legend(pPainter, pItems, pWidth):
    """Dessine une légende qui passe à la ligne ; retourne la hauteur occupée."""

    vLeft = 0
    vTop = 0

    for vLabel, vColor in pItems:
        vWidth = pPainter.fontMetrics().horizontalAdvance(vLabel)

        if vLeft and vLeft + vWidth + 16 > pWidth:
            vLeft = 0
            vTop += LEGEND_ROW_HEIGHT

        pPainter.setPen(Qt.PenStyle.NoPen)
        pPainter.setBrush(QColor(vColor))
        pPainter.drawRoundedRect(QRectF(vLeft, vTop + 4, 10, 10), 3, 3)

        pPainter.setPen(QColor(COLORS["muted"]))
        pPainter.drawText(
            QRectF(vLeft + 16, vTop, vWidth + 4, LEGEND_ROW_HEIGHT),
            Qt.AlignmentFlag.AlignVCenter,
            vLabel,
        )

        vLeft += vWidth + 36

    rHeight = vTop + LEGEND_ROW_HEIGHT + 6

    return rHeight


class BarChart(QWidget):
    """Affiche une ou plusieurs séries de barres groupées par libellé."""

    def __init__(self):
        """Crée un histogramme vide."""
        super().__init__()

        self.labels = []
        self.series = []
        self.independent_scales = False
        self.setMinimumHeight(170)

    def set_series(self, pLabels, pSeries, pIndependentScales=False):
        """Remplace les données : pSeries contient des (nom, couleur, valeurs).

        Avec pIndependentScales, chaque série a sa propre échelle : une série de
        faibles valeurs reste visible à côté d'une série de valeurs élevées.
        """
        self.labels = pLabels
        self.series = pSeries
        self.independent_scales = pIndependentScales
        self.update()

    def get_maximum(self, pValues):
        """Retourne la valeur qui correspond à la hauteur maximale d'une barre."""
        vValues = (
            pValues
            if self.independent_scales
            else [vValue for _, _, vSeries in self.series for vValue in vSeries]
        )

        rMaximum = max(vValues, default=0) or 1

        return rMaximum

    def paintEvent(self, pEvent):
        """Dessine la légende éventuelle puis les barres groupées par libellé.

        Avec plusieurs séries, le total de chacune figure dans la légende plutôt
        qu'au-dessus des barres, où les nombres se chevaucheraient.
        """
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vWidth = self.width()
        vTop = LABEL_HEIGHT

        vHasLegend = len(self.series) > 1

        if vHasLegend:
            vTop += draw_legend(
                vPainter,
                [
                    (f"{vName} · {sum(vValues)}", vColor)
                    for vName, vColor, vValues in self.series
                ],
                vWidth,
            )

        vChartHeight = self.height() - vTop - LABEL_HEIGHT
        vBaseline = vTop + vChartHeight

        vPainter.setPen(QColor(COLORS["border"]))
        vPainter.drawLine(0, vBaseline, vWidth, vBaseline)

        if self.labels:
            vSlot = vWidth / len(self.labels)
            vBarWidth = min(vSlot * 0.7 / len(self.series), 22)
            vGroupWidth = vBarWidth * len(self.series)

            for vIndex, vLabel in enumerate(self.labels):
                vGroupLeft = vIndex * vSlot + (vSlot - vGroupWidth) / 2

                for vSeriesIndex, (_, vColor, vValues) in enumerate(self.series):
                    vValue = vValues[vIndex]
                    vMaximum = self.get_maximum(vValues)
                    vHeight = max(vChartHeight * vValue / vMaximum, 3 if vValue else 2)
                    vLeft = vGroupLeft + vSeriesIndex * vBarWidth

                    vPainter.setPen(Qt.PenStyle.NoPen)
                    vPainter.setBrush(QColor(vColor if vValue else COLORS["border"]))
                    vPainter.drawRoundedRect(
                        QRectF(vLeft + 1, vBaseline - vHeight, vBarWidth - 2, vHeight),
                        3,
                        3,
                    )

                    if vValue and not vHasLegend:
                        vPainter.setPen(QColor(COLORS["heading"]))
                        vPainter.drawText(
                            QRectF(
                                vLeft - 10,
                                vBaseline - vHeight - LABEL_HEIGHT,
                                vBarWidth + 20,
                                LABEL_HEIGHT,
                            ),
                            Qt.AlignmentFlag.AlignCenter,
                            str(vValue),
                        )

                # Le dernier libellé, souvent le jour courant, reste toujours visible.
                if vSlot >= MIN_LABEL_WIDTH or (len(self.labels) - 1 - vIndex) % 2 == 0:
                    vLabelLeft = min(
                        max(vIndex * vSlot - vSlot / 2, 0), vWidth - 2 * vSlot
                    )

                    vPainter.setPen(QColor(COLORS["muted"]))
                    vPainter.drawText(
                        QRectF(vLabelLeft, vBaseline, vSlot * 2, LABEL_HEIGHT),
                        Qt.AlignmentFlag.AlignCenter,
                        vLabel,
                    )

        vPainter.end()


class PieChart(QWidget):
    """Affiche des parts sous forme d'anneau, avec leur légende à droite."""

    def __init__(self):
        """Crée un camembert vide."""
        super().__init__()

        self.shares = []
        self.setMinimumHeight(170)

    def set_shares(self, pShares):
        """Remplace les parts : des (libellé, valeur, couleur)."""
        self.shares = pShares
        self.update()

    def paintEvent(self, pEvent):
        """Dessine l'anneau puis la légende avec valeur et pourcentage."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vTotal = sum(vValue for _, vValue, _ in self.shares)
        vDiameter = min(self.height() - 8, self.width() / 2)
        vRing = QRectF(4, (self.height() - vDiameter) / 2, vDiameter, vDiameter)

        if vTotal:
            # Qt compte les angles en seizièmes de degré, à partir de trois heures.
            vStart = 90 * 16

            for _, vValue, vColor in self.shares:
                vSpan = -round(360 * 16 * vValue / vTotal)

                vPainter.setPen(Qt.PenStyle.NoPen)
                vPainter.setBrush(QColor(vColor))
                vPainter.drawPie(vRing, vStart, vSpan)

                vStart += vSpan
        else:
            vPainter.setPen(Qt.PenStyle.NoPen)
            vPainter.setBrush(QColor(COLORS["border"]))
            vPainter.drawEllipse(vRing)

        # Le disque central transforme le camembert en anneau, plus lisible.
        vHole = vRing.adjusted(
            vDiameter * 0.22, vDiameter * 0.22, -vDiameter * 0.22, -vDiameter * 0.22
        )

        vPainter.setBrush(QColor(COLORS["surface"]))
        vPainter.drawEllipse(vHole)

        vPainter.setPen(QColor(COLORS["heading"]))
        vFont = vPainter.font()
        vFont.setBold(True)
        vFont.setPointSizeF(vFont.pointSizeF() * 1.4)
        vPainter.setFont(vFont)
        vPainter.drawText(vHole, Qt.AlignmentFlag.AlignCenter, str(vTotal))

        vFont.setBold(False)
        vFont.setPointSizeF(vFont.pointSizeF() / 1.4)
        vPainter.setFont(vFont)

        vLegendLeft = vRing.right() + 20
        vRowHeight = 22
        vLegendTop = (self.height() - vRowHeight * len(self.shares)) / 2

        for vIndex, (vLabel, vValue, vColor) in enumerate(self.shares):
            vTop = vLegendTop + vIndex * vRowHeight

            vPainter.setPen(Qt.PenStyle.NoPen)
            vPainter.setBrush(QColor(vColor))
            vPainter.drawRoundedRect(QRectF(vLegendLeft, vTop + 5, 10, 10), 3, 3)

            vPercent = round(100 * vValue / vTotal) if vTotal else 0

            vPainter.setPen(QColor(COLORS["text"]))
            vPainter.drawText(
                QRectF(
                    vLegendLeft + 18, vTop, self.width() - vLegendLeft - 18, vRowHeight
                ),
                Qt.AlignmentFlag.AlignVCenter,
                f"{vLabel}  ·  {vValue} ({vPercent} %)",
            )

        vPainter.end()
