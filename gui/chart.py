"""Histogramme et camembert dessinés avec QPainter"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme import COLORS

# Hauteur réservée sous les barres pour les libellés, au-dessus pour les valeurs
LABEL_HEIGHT = 18

# Hauteur d'une ligne de la légende affichée lorsqu'il y a plusieurs séries
LEGEND_ROW_HEIGHT = 18

# Hauteur réservée au titre d'un camembert, au-dessus de l'anneau
PIE_TITLE_HEIGHT = 22

# Diamètre minimal de l'anneau et écart avant sa légende
MIN_PIE_DIAMETER = 90
LEGEND_GAP = 20

# En dessous de cette largeur par groupe de barres, un libellé sur deux est affiché
MIN_LABEL_WIDTH = 40

# Une valeur plus de OUTLIER_RATIO fois supérieure à la suivante (un premier import,
# par exemple) écraserait les autres barres : l'échelle s'arrête alors à
# OUTLIER_SCALE fois la suivante, et la barre coupée affiche sa valeur.
OUTLIER_RATIO = 3
OUTLIER_SCALE = 1.5

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

        vSorted = sorted(vValues, reverse=True)
        rMaximum = (vSorted[0] if vSorted else 0) or 1

        # Seulement entre les valeurs d'une même série : deux séries d'ordres de
        # grandeur différents sur une échelle commune ne sont pas un pic isolé.
        vOneSeries = self.independent_scales or len(self.series) <= 1

        if (
            vOneSeries
            and len(vSorted) > 1
            and 0 < vSorted[1] * OUTLIER_RATIO < vSorted[0]
        ):
            rMaximum = round(vSorted[1] * OUTLIER_SCALE)

        return rMaximum

    def get_scale(self):
        """Retourne la valeur de la ligne haute du graphique et sa couleur, par échelle.

        Avec des échelles indépendantes, chaque série non vide a la sienne.
        """
        rScale = (
            [
                (self.get_maximum(vValues), vColor)
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

        # Le libellé de l'axe vertical occupe une ligne au-dessus des barres.
        vTop = LABEL_HEIGHT * (2 if vYAxisLabel else 1)
        vLegendItems = [
            (f"{vName} · {sum(vValues)}", vColor)
            for vName, vColor, vValues in self.series
        ]
        vLegendHeight = (
            draw_legend(vPainter, vLegendItems, self.width(), 0, pDraw=False)
            if len(self.series) > 1
            else 0
        )
        vChartHeight = (
            self.height()
            - vTop
            - LABEL_HEIGHT
            - (LABEL_HEIGHT if vXAxisLabel else 0)
            - vLegendHeight
        )

        if vYAxisLabel:
            self.draw_scale(vPainter, vYAxisLabel)

        self.draw_frame(
            vPainter, vTop, vTop + vChartHeight, vLegendItems, vLegendHeight
        )

        if self.labels:
            vSlot = self.width() / len(self.labels)

            if not self.fill_width:
                vSlot = min(vSlot, MAX_SLOT_WIDTH)

            vBarWidth = min(vSlot * 0.7 / len(self.series), 22)
            vGroupWidth = vBarWidth * len(self.series)

            for vIndex, vLabel in enumerate(self.labels):
                vGroupLeft = vIndex * vSlot + (vSlot - vGroupWidth) / 2

                for vSeriesIndex, (_, vColor, vValues) in enumerate(self.series):
                    self.draw_bar(
                        vPainter,
                        QRectF(
                            vGroupLeft + vSeriesIndex * vBarWidth,
                            vTop,
                            vBarWidth,
                            vChartHeight,
                        ),
                        vValues[vIndex],
                        self.get_maximum(vValues),
                        vColor[vIndex] if isinstance(vColor, (list, tuple)) else vColor,
                    )

                # Le dernier libellé, souvent le jour courant, reste toujours visible.
                if vSlot >= MIN_LABEL_WIDTH or (len(self.labels) - 1 - vIndex) % 2 == 0:
                    self.draw_day_label(
                        vPainter, vLabel, (vIndex + 0.5) * vSlot, vTop + vChartHeight
                    )

        vPainter.end()

    def draw_scale(self, pPainter, pYAxisLabel):
        """Écrit le libellé de l'axe vertical, puis la valeur de la ligne haute."""
        pPainter.setPen(QColor(COLORS["muted"]))
        pPainter.drawText(
            QRectF(0, 0, self.width(), LABEL_HEIGHT),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            pYAxisLabel,
        )

        vLeft = pPainter.fontMetrics().horizontalAdvance(pYAxisLabel + "   ")

        for vValue, vColor in self.get_scale():
            vText = f"max {vValue}"
            pPainter.setPen(QColor(vColor))
            pPainter.drawText(
                QRectF(vLeft, 0, self.width(), LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                vText,
            )
            vLeft += pPainter.fontMetrics().horizontalAdvance(vText + "   ")

    def draw_frame(self, pPainter, pTop, pBaseline, pLegendItems, pLegendHeight):
        """Trace la ligne de base, la ligne haute, l'axe horizontal et la légende."""
        vXAxisLabel, vYAxisLabel = self.axes
        vWidth = self.width()

        if vXAxisLabel:
            pPainter.setPen(QColor(COLORS["muted"]))
            pPainter.drawText(
                QRectF(0, pBaseline + LABEL_HEIGHT, vWidth, LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignCenter,
                vXAxisLabel,
            )

        if pLegendHeight:
            draw_legend(
                pPainter, pLegendItems, vWidth, self.height() - pLegendHeight + 6
            )

        pPainter.setPen(QColor(COLORS["border"]))
        pPainter.drawLine(0, pBaseline, vWidth, pBaseline)

        if vYAxisLabel:
            pPainter.setPen(QPen(QColor(COLORS["border"]), 1, Qt.PenStyle.DashLine))
            pPainter.drawLine(0, pTop, vWidth, pTop)

    def draw_bar(self, pPainter, pSlot, pValue, pMaximum, pColor):
        """Dessine une barre dans pSlot (sa colonne, haute de toute la zone).

        Une valeur au-delà de l'échelle est coupée, marquée de deux traits et
        affiche son nombre ; sans légende, chaque barre affiche le sien.
        """
        vCut = pValue > pMaximum
        vHeight = max(
            pSlot.height() * min(pValue, pMaximum) / pMaximum, 3 if pValue else 2
        )
        vBaseline = pSlot.bottom()
        vLeft = pSlot.left()

        pPainter.setPen(Qt.PenStyle.NoPen)
        pPainter.setBrush(QColor(pColor if pValue else COLORS["border"]))
        pPainter.drawRoundedRect(
            QRectF(vLeft + 1, vBaseline - vHeight, pSlot.width() - 2, vHeight), 3, 3
        )

        if vCut:
            # Deux traits blancs en biais signalent la barre coupée.
            pPainter.setPen(QPen(QColor("#ffffff"), 2))
            for vOffset in (10, 16):
                pPainter.drawLine(
                    QPointF(vLeft, pSlot.top() + vOffset + 3),
                    QPointF(vLeft + pSlot.width(), pSlot.top() + vOffset - 3),
                )

        if pValue and (vCut or len(self.series) == 1):
            pPainter.setPen(QColor(COLORS["heading"]))
            pPainter.drawText(
                QRectF(
                    vLeft - 10,
                    vBaseline - vHeight - LABEL_HEIGHT,
                    pSlot.width() + 20,
                    LABEL_HEIGHT,
                ),
                Qt.AlignmentFlag.AlignCenter,
                str(pValue),
            )

    def draw_day_label(self, pPainter, pLabel, pCenter, pBaseline):
        """Écrit le libellé centré sous son groupe, décalé seulement s'il déborde."""
        vLabelWidth = pPainter.fontMetrics().horizontalAdvance(pLabel) + 4
        vLabelLeft = min(max(pCenter - vLabelWidth / 2, 0), self.width() - vLabelWidth)

        pPainter.setPen(QColor(COLORS["muted"]))
        pPainter.drawText(
            QRectF(vLabelLeft, pBaseline, vLabelWidth, LABEL_HEIGHT),
            Qt.AlignmentFlag.AlignCenter,
            pLabel,
        )


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
        vLegend = [
            (
                f"{vLabel}  ·  {vValue} "
                f"({round(100 * vValue / vTotal) if vTotal else 0} %)",
                vColor,
            )
            for vLabel, vValue, vColor in self.shares
        ]

        # La légende est mesurée d'abord : l'anneau prend la place qui reste,
        # sans descendre sous une taille lisible.
        vLegendWidth = max(
            (vPainter.fontMetrics().horizontalAdvance(vText) for vText, _ in vLegend),
            default=0,
        )
        vDiameter = max(
            MIN_PIE_DIAMETER,
            min(vHeight - 8, self.width() - vLegendWidth - LEGEND_GAP - 22),
        )
        vRing = QRectF(4, vTop + (vHeight - vDiameter) / 2, vDiameter, vDiameter)

        if self.title:
            self.draw_title(vPainter, vRing)

        self.draw_ring(vPainter, vRing, vTotal)
        self.draw_legend_rows(
            vPainter, vLegend, vRing.right() + LEGEND_GAP, vTop, vHeight
        )

        vPainter.end()

    def draw_title(self, pPainter, pRing):
        """Écrit le titre centré sur l'anneau, élargi vers la droite s'il est long."""
        pPainter.save()
        pPainter.setPen(QColor(COLORS["muted"]))

        vFont = pPainter.font()
        vFont.setBold(True)
        pPainter.setFont(vFont)

        vTitleWidth = max(
            pRing.width(), pPainter.fontMetrics().horizontalAdvance(self.title) + 8
        )
        pPainter.drawText(
            QRectF(pRing.left(), 0, vTitleWidth, PIE_TITLE_HEIGHT),
            Qt.AlignmentFlag.AlignCenter,
            self.title,
        )
        pPainter.restore()

    def draw_ring(self, pPainter, pRing, pTotal):
        """Dessine les parts, le trou central et le total au milieu."""
        if pTotal:
            # Qt compte les angles en seizièmes de degré, à partir de trois heures.
            vStart = 90 * 16

            for _, vValue, vColor in self.shares:
                vSpan = -round(360 * 16 * vValue / pTotal)

                pPainter.setPen(Qt.PenStyle.NoPen)
                pPainter.setBrush(QColor(vColor))
                pPainter.drawPie(pRing, vStart, vSpan)

                vStart += vSpan
        else:
            pPainter.setPen(Qt.PenStyle.NoPen)
            pPainter.setBrush(QColor(COLORS["border"]))
            pPainter.drawEllipse(pRing)

        # Le disque central transforme le camembert en anneau, plus lisible.
        vMargin = pRing.width() * 0.22
        vHole = pRing.adjusted(vMargin, vMargin, -vMargin, -vMargin)

        pPainter.setBrush(QColor(COLORS["surface"]))
        pPainter.drawEllipse(vHole)

        pPainter.save()
        pPainter.setPen(QColor(COLORS["heading"]))

        vFont = pPainter.font()
        vFont.setBold(True)
        scale_font(vFont, 1.4)
        pPainter.setFont(vFont)

        # Dans un petit anneau, le total est réduit pour tenir dans le trou.
        vAvailable = vHole.width() * 0.85
        vNeeded = pPainter.fontMetrics().horizontalAdvance(str(pTotal))

        if vNeeded > vAvailable:
            scale_font(vFont, vAvailable / vNeeded)
            pPainter.setFont(vFont)

        pPainter.drawText(vHole, Qt.AlignmentFlag.AlignCenter, str(pTotal))
        pPainter.restore()

    def draw_legend_rows(self, pPainter, pLegend, pLeft, pTop, pHeight):
        """Écrit la légende à droite de l'anneau, une ligne par part."""
        vRowHeight = 22
        vLegendTop = pTop + (pHeight - vRowHeight * len(self.shares)) / 2
        vTextWidth = self.width() - pLeft - 18

        for vIndex, (vText, vColor) in enumerate(pLegend):
            vRowTop = vLegendTop + vIndex * vRowHeight

            pPainter.setPen(Qt.PenStyle.NoPen)
            pPainter.setBrush(QColor(vColor))
            pPainter.drawRoundedRect(QRectF(pLeft, vRowTop + 5, 10, 10), 3, 3)

            # Fenêtre vraiment trop étroite : le texte est abrégé, jamais coupé net.
            pPainter.setPen(QColor(COLORS["text"]))
            pPainter.drawText(
                QRectF(pLeft + 18, vRowTop, vTextWidth, vRowHeight),
                Qt.AlignmentFlag.AlignVCenter,
                pPainter.fontMetrics().elidedText(
                    vText, Qt.TextElideMode.ElideRight, int(vTextWidth)
                ),
            )
