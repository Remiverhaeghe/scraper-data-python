"""Histogramme et camembert dessinés avec QPainter"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
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

# Largeur maximale d'un jour : avec peu de jours, les barres restent à gauche
# au lieu de s'étaler sur toute la largeur.
MAX_SLOT_WIDTH = 56


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
        self.axes = (None, None)
        self.empty_text = ""
        self.fill_width = False
        self.setMinimumHeight(170)

    def set_series(
        self,
        pLabels,
        pSeries,
        pIndependentScales=False,
        pAxes=(None, None),
        pEmptyText="",
        pFillWidth=False,
    ):
        """Remplace les données : pSeries contient des (nom, couleur, valeurs).

        Avec pIndependentScales, chaque série a sa propre échelle : une série de
        faibles valeurs reste visible à côté d'une série de valeurs élevées.
        pAxes donne les libellés des axes horizontal et vertical ; pEmptyText
        remplace le graphique lorsque toutes les valeurs sont nulles. La couleur
        peut être une liste, une par barre ; pFillWidth répartit les barres sur
        toute la largeur, pour des catégories plutôt que des jours.
        """
        self.labels = pLabels
        self.series = pSeries
        self.independent_scales = pIndependentScales
        self.axes = pAxes
        self.empty_text = pEmptyText
        self.fill_width = pFillWidth
        self.update()

    def is_empty(self):
        """Indique si aucune série ne contient de valeur."""
        rEmpty = not any(vValue for _, _, vValues in self.series for vValue in vValues)

        return rEmpty

    def get_maximum(self, pValues):
        """Retourne la valeur qui correspond à la hauteur maximale d'une barre."""
        vValues = (
            pValues
            if self.independent_scales
            else [vValue for _, _, vSeries in self.series for vValue in vSeries]
        )

        rMaximum = max(vValues, default=0) or 1

        return rMaximum

    def get_scale(self):
        """Retourne la valeur de la ligne haute du graphique et sa couleur, par échelle.

        Avec des échelles indépendantes, chaque série non vide a la sienne.
        """
        rScale = (
            [
                (max(vValues), vColor)
                for _, vColor, vValues in self.series
                if any(vValues)
            ]
            if self.independent_scales
            else [(self.get_maximum([]), COLORS["muted"])]
        )

        return rScale

    def paintEvent(self, _pEvent):
        """Dessine les barres groupées par libellé, puis la légende en dessous.

        Avec plusieurs séries, le total de chacune figure dans la légende plutôt
        qu'au-dessus des barres, où les nombres se chevaucheraient.
        """
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.empty_text and self.is_empty():
            vPainter.setPen(QColor(COLORS["muted"]))
            vPainter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text
            )
            vPainter.end()
            return

        vXAxisLabel, vYAxisLabel = self.axes
        vWidth = self.width()

        # Le libellé de l'axe vertical occupe une ligne au-dessus des barres.
        vTop = LABEL_HEIGHT * (2 if vYAxisLabel else 1)

        if vYAxisLabel:
            vPainter.setPen(QColor(COLORS["muted"]))
            vPainter.drawText(
                QRectF(0, 0, vWidth, LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                vYAxisLabel,
            )

            # Valeur de la ligne haute, à droite du libellé de l'axe
            vLeft = vPainter.fontMetrics().horizontalAdvance(vYAxisLabel + "   ")

            for vValue, vColor in self.get_scale():
                vText = f"max {vValue}"
                vPainter.setPen(QColor(vColor))
                vPainter.drawText(
                    QRectF(vLeft, 0, vWidth, LABEL_HEIGHT),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    vText,
                )
                vLeft += vPainter.fontMetrics().horizontalAdvance(vText + "   ")

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

        vXAxisHeight = LABEL_HEIGHT if vXAxisLabel else 0
        vChartHeight = (
            self.height() - vTop - LABEL_HEIGHT - vXAxisHeight - vLegendHeight
        )
        vBaseline = vTop + vChartHeight

        if vXAxisLabel:
            vPainter.setPen(QColor(COLORS["muted"]))
            vPainter.drawText(
                QRectF(0, vBaseline + LABEL_HEIGHT, vWidth, LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignCenter,
                vXAxisLabel,
            )

        if vHasLegend:
            draw_legend(
                vPainter, vLegendItems, vWidth, self.height() - vLegendHeight + 6
            )

        vPainter.setPen(QColor(COLORS["border"]))
        vPainter.drawLine(0, vBaseline, vWidth, vBaseline)

        if vYAxisLabel:
            vPainter.setPen(QPen(QColor(COLORS["border"]), 1, Qt.PenStyle.DashLine))
            vPainter.drawLine(0, vTop, vWidth, vTop)

        if self.labels:
            vSlot = vWidth / len(self.labels)

            if not self.fill_width:
                vSlot = min(vSlot, MAX_SLOT_WIDTH)
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
                    vBarColor = (
                        vColor[vIndex] if isinstance(vColor, (list, tuple)) else vColor
                    )
                    vPainter.setBrush(QColor(vBarColor if vValue else COLORS["border"]))
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

    def paintEvent(self, _pEvent):
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
