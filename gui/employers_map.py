"""Carte schématique des employeurs autour du domicile, sans fond de carte

Le domicile est au centre, entouré de cercles de distance ; chaque employeur est
placé d'après la position de son site le plus proche et coloré selon sa
candidature spontanée. Elle se dessine hors ligne, sans tuiles à télécharger.
"""

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from gui.theme import COLORS
from job.spontaneous_applications import get_contact_tone

# Kilomètres par degré de latitude ; ceux d'un degré de longitude diminuent vers le nord
KM_PER_DEGREE = 111.2
RINGS_KM = (10, 25, 50, 100, 150, 200)
MARGIN = 24
DOT_RADIUS = 5
HOME_RADIUS = 7
# Distance en pixels sous laquelle le survol ou le clic désigne un employeur
PICK_DISTANCE = 8


def project(pHome, pLatitude, pLongitude):
    """Retourne la position d'un point en km (est, nord) par rapport au domicile."""

    rPoint = (
        (pLongitude - pHome["longitude"])
        * KM_PER_DEGREE
        * math.cos(math.radians(pHome["latitude"])),
        (pLatitude - pHome["latitude"]) * KM_PER_DEGREE,
    )

    return rPoint


def place_employers(pHome, pEmployers, pWidth, pHeight):
    """Retourne l'échelle (pixels par km) et les employeurs placés en pixels.

    L'échelle fait tenir l'employeur le plus éloigné ; ceux sans position sont omis.
    """

    vPlaced = [
        (vEmployer, project(pHome, vEmployer["latitude"], vEmployer["longitude"]))
        for vEmployer in pEmployers
        if vEmployer.get("latitude") is not None
        and vEmployer.get("longitude") is not None
    ]
    vFarthest = max(
        [RINGS_KM[0], *(math.hypot(*vKm) for _, vKm in vPlaced)],
    )
    vScale = max(min(pWidth, pHeight) / 2 - MARGIN, 1) / vFarthest

    rPlacement = (
        vScale,
        [
            (
                vEmployer,
                pWidth / 2 + vKm[0] * vScale,
                pHeight / 2 - vKm[1] * vScale,
            )
            for vEmployer, vKm in vPlaced
        ],
    )

    return rPlacement


class EmployersMap(QWidget):
    """Carte des employeurs ; un clic sur un point émet son SIREN."""

    employer_clicked = Signal(str)

    def __init__(self):
        """Crée une carte vide ; set_employers la remplit."""
        super().__init__()

        self.home = None
        self.employers = []
        self.points = []
        self.setMinimumHeight(360)
        self.setMouseTracking(True)

    def set_employers(self, pHome, pEmployers):
        """Remplace le domicile et les employeurs affichés."""
        self.home = pHome
        self.employers = pEmployers
        self.update()

    def find_point(self, pPosition):
        """Retourne l'employeur sous la souris, ou None."""
        rEmployer = next(
            (
                vEmployer
                for vEmployer, vX, vY in self.points
                if math.hypot(vX - pPosition.x(), vY - pPosition.y()) <= PICK_DISTANCE
            ),
            None,
        )

        return rEmployer

    def mouseMoveEvent(self, pEvent):  # pylint: disable=invalid-name
        """Affiche le nom, le secteur et la distance de l'employeur survolé."""
        vEmployer = self.find_point(pEvent.position())

        if vEmployer is None:
            QToolTip.hideText()
            return

        QToolTip.showText(
            pEvent.globalPosition().toPoint(),
            f"{vEmployer['name']}\n{vEmployer['sector']} · {vEmployer['city']}, "
            f"{vEmployer['distance_km']} km"
            + (
                f"\n{vEmployer['spontaneous']['status_label']}"
                if vEmployer.get("spontaneous")
                else ""
            ),
            self,
        )

    def mousePressEvent(self, pEvent):  # pylint: disable=invalid-name
        """Choisit l'employeur cliqué."""
        vEmployer = self.find_point(pEvent.position())

        if vEmployer is not None:
            self.employer_clicked.emit(vEmployer["siren"])

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine les cercles de distance, le domicile puis les employeurs."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vCenter = QPointF(self.width() / 2, self.height() / 2)

        if not self.home:
            vPainter.setPen(QColor(COLORS["muted"]))
            vPainter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Renseignez votre domicile dans les Paramètres pour placer les "
                "employeurs autour de chez vous.",
            )
            vPainter.end()
            self.points = []
            return

        vScale, self.points = place_employers(
            self.home, self.employers, self.width(), self.height()
        )
        vLimit = (min(self.width(), self.height()) / 2 - MARGIN) / vScale

        vPainter.setBrush(Qt.BrushStyle.NoBrush)

        for vRing in RINGS_KM:
            if vRing > vLimit * 1.05:
                break

            vPainter.setPen(QPen(QColor(COLORS["border"]), 1, Qt.PenStyle.DashLine))
            vPainter.drawEllipse(vCenter, vRing * vScale, vRing * vScale)
            vPainter.setPen(QColor(COLORS["muted"]))
            vPainter.drawText(
                QPointF(vCenter.x() + 4, vCenter.y() - vRing * vScale - 4),
                f"{vRing} km",
            )

        vPainter.setPen(QPen(QColor(COLORS["surface"]), 1.5))

        for vEmployer, vX, vY in self.points:
            vPainter.setBrush(
                QColor(COLORS[get_contact_tone(vEmployer.get("spontaneous"))])
            )
            vPainter.drawEllipse(QPointF(vX, vY), DOT_RADIUS, DOT_RADIUS)

        vPainter.setBrush(QColor(COLORS["heading"]))
        vPainter.drawEllipse(vCenter, HOME_RADIUS, HOME_RADIUS)
        vPainter.end()
