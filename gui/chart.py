"""Histogramme et camembert dessinés avec QPainter"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from gui.theme import COLORS

# Hauteur réservée sous les barres pour les libellés, au-dessus pour les valeurs
LABEL_HEIGHT = 18

# Hauteur d'une ligne de la légende affichée lorsqu'il y a plusieurs séries
LEGEND_ROW_HEIGHT = 18

# Hauteur réservée au titre d'un camembert, au-dessus de l'anneau
PIE_TITLE_HEIGHT = 22

# En dessous de cette largeur par groupe de barres, un libellé sur deux est affiché
MIN_LABEL_WIDTH = 40


def scale_font(pFont, pFactor):
    """Agrandit ou réduit une police, qu'elle soit définie en points ou en pixels.

    La feuille de style fixe la taille en pixels : la taille en points vaut
    alors -1 et ne peut pas être multipliée.
    """

    if pFont.pointSizeF() > 0:
        pFont.setPointSizeF(pFont.pointSizeF() * pFactor)
    else:
        pFont.setPixelSize(max(round(pFont.pixelSize() * pFactor), 1))


def draw_legend(pPainter, pItems, pWidth, pTop, pDraw=True):
    """Dessine une légende qui passe à la ligne et retourne sa hauteur.

    Avec pDraw à False, la légende est seulement mesurée, pour réserver sa
    place sous le graphique avant de dessiner les barres.
    """

    vLeft = 0
    vTop = pTop

    for vLabel, vColor in pItems:
        vWidth = pPainter.fontMetrics().horizontalAdvance(vLabel)

        if vLeft and vLeft + vWidth + 16 > pWidth:
            vLeft = 0
            vTop += LEGEND_ROW_HEIGHT

        if pDraw:
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

    rHeight = vTop - pTop + LEGEND_ROW_HEIGHT + 6

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
        """Dessine les barres groupées par libellé, puis la légende en dessous.

        Avec plusieurs séries, le total de chacune figure dans la légende plutôt
        qu'au-dessus des barres, où les nombres se chevaucheraient.
        """
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vWidth = self.width()
        vTop = LABEL_HEIGHT

        vHasLegend = len(self.series) > 1
        vLegendItems = [
            (f"{vName} · {sum(vValues)}", vColor)
            for vName, vColor, vValues in self.series
        ]
        vLegendHeight = (
            draw_legend(vPainter, vLegendItems, vWidth, 0, pDraw=False)
            if vHasLegend
            else 0
        )

        vChartHeight = self.height() - vTop - LABEL_HEIGHT - vLegendHeight
        vBaseline = vTop + vChartHeight

        if vHasLegend:
            draw_legend(
                vPainter, vLegendItems, vWidth, self.height() - vLegendHeight + 6
            )

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
                    # Centré sous sa barre, le texte n'est décalé que s'il
                    # déborde du graphique.
                    vLabelWidth = vPainter.fontMetrics().horizontalAdvance(vLabel) + 4
                    vLabelLeft = min(
                        max((vIndex + 0.5) * vSlot - vLabelWidth / 2, 0),
                        vWidth - vLabelWidth,
                    )

                    vPainter.setPen(QColor(COLORS["muted"]))
                    vPainter.drawText(
                        QRectF(vLabelLeft, vBaseline, vLabelWidth, LABEL_HEIGHT),
                        Qt.AlignmentFlag.AlignCenter,
                        vLabel,
                    )

        vPainter.end()


class PieChart(QWidget):
    """Affiche des parts sous forme d'anneau, avec leur légende à droite."""

    def __init__(self, pTitle=None):
        """Crée un camembert vide, avec un titre centré au-dessus de l'anneau."""
        super().__init__()

        self.title = pTitle
        self.shares = []
        self.setMinimumHeight(170 + (PIE_TITLE_HEIGHT if pTitle else 0))

    def set_shares(self, pShares):
        """Remplace les parts : des (libellé, valeur, couleur)."""
        self.shares = pShares
        self.update()

    def paintEvent(self, pEvent):
        """Dessine l'anneau puis la légende avec valeur et pourcentage."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vTotal = sum(vValue for _, vValue, _ in self.shares)
        vTop = PIE_TITLE_HEIGHT if self.title else 0
        vHeight = self.height() - vTop
        vDiameter = min(vHeight - 8, self.width() / 2)
        vRing = QRectF(4, vTop + (vHeight - vDiameter) / 2, vDiameter, vDiameter)

        if self.title:
            vPainter.save()
            vPainter.setPen(QColor(COLORS["muted"]))

            vFont = vPainter.font()
            vFont.setBold(True)
            vPainter.setFont(vFont)

            vPainter.drawText(
                QRectF(vRing.left(), 0, vRing.width(), PIE_TITLE_HEIGHT),
                Qt.AlignmentFlag.AlignCenter,
                self.title,
            )
            vPainter.restore()

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

        vPainter.save()
        vPainter.setPen(QColor(COLORS["heading"]))

        vFont = vPainter.font()
        vFont.setBold(True)
        scale_font(vFont, 1.4)

        vPainter.setFont(vFont)
        vPainter.drawText(vHole, Qt.AlignmentFlag.AlignCenter, str(vTotal))
        vPainter.restore()

        vLegendLeft = vRing.right() + 20
        vRowHeight = 22
        vLegendTop = vTop + (vHeight - vRowHeight * len(self.shares)) / 2

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
