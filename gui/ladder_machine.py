"""Machine animée du simulateur d'automate : moteur, vérin, tapis ou broche"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme import COLORS
from job.ladder_game import PIECE_PERIOD, SPINDLE_STROKE, VERIN_STROKE

LAMP_RADIUS = 11
OFF_COLOR = "#94a3b8"
ON_COLOR = "#16a34a"
FAULT_COLOR = "#dc2626"
STEEL = "#64748b"

# Sorties qui alimentent le moteur dessiné : un sens, le contacteur de ligne, une pompe
MOTOR_OUTPUTS = ("moteur", "avant", "arriere", "ligne", "pompe1", "pompe2")


class MachineView(QWidget):
    """Dessine la machine d'un niveau et l'état de ses sorties."""

    def __init__(self):
        """Démarre sans machine ; set_state la fournit."""
        super().__init__()

        self.level = None
        self.values = {}
        self.machine = {"position": 0, "run": 0}
        self.angle = 0
        self.setMinimumHeight(220)

    def set_state(self, pLevel, pValues, pMachine):
        """Mémorise l'état à dessiner et redessine."""
        self.level = pLevel
        self.values = pValues
        self.machine = pMachine

        if self.is_motor_running() or pValues.get("tapis") or pValues.get("rotation"):
            self.angle = (self.angle + (-30 if pValues.get("arriere") else 30)) % 360

        self.update()

    def is_motor_running(self):
        """Indique si le moteur est alimenté : une sortie de puissance, pas un voyant."""
        rRunning = self.level is not None and any(
            self.values.get(vName) for vName in MOTOR_OUTPUTS
        )

        return rRunning

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine la machine à gauche et les voyants des sorties à droite."""
        if self.level is None:
            return

        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vPainter.setPen(QPen(QColor(COLORS["text"]), 2))

        vArea = QRectF(10, 10, self.width() * 0.62, self.height() - 20)
        {
            "moteur": self.draw_motor,
            "verin": self.draw_cylinder,
            "tapis": self.draw_conveyor,
            "percage": self.draw_drill,
        }[self.level["machine"]](vPainter, vArea)

        self.draw_lamps(vPainter, QRectF(vArea.right() + 20, 10, 0, 0))
        vPainter.end()

    def draw_motor(self, pPainter, pArea):
        """Moteur avec un repère qui tourne quand il est alimenté."""
        vCenter = pArea.center()
        vRadius = min(pArea.width(), pArea.height()) / 3
        vRunning = self.is_motor_running()

        pPainter.setBrush(QColor(ON_COLOR if vRunning else "#e2e8f0"))
        pPainter.drawEllipse(vCenter, vRadius, vRadius)
        pPainter.save()
        pPainter.translate(vCenter)
        pPainter.rotate(self.angle)
        pPainter.setPen(QPen(QColor("#ffffff" if vRunning else STEEL), 6))
        pPainter.drawLine(QPointF(0, 0), QPointF(vRadius * 0.8, 0))
        pPainter.restore()
        pPainter.drawText(
            QRectF(vCenter.x() - 60, vCenter.y() + vRadius + 6, 120, 20),
            Qt.AlignmentFlag.AlignCenter,
            "Moteur M1",
        )

    def draw_cylinder(self, pPainter, pArea):
        """Vérin horizontal : la tige sort selon la position."""
        vRatio = self.machine["position"] / VERIN_STROKE
        vBody = QRectF(
            pArea.left() + 10, pArea.center().y() - 25, pArea.width() * 0.45, 50
        )
        vRod = vBody.width() * 0.9 * vRatio + 20

        pPainter.setBrush(QColor("#e2e8f0"))
        pPainter.drawRect(vBody)
        pPainter.setBrush(QColor(STEEL))
        pPainter.drawRect(QRectF(vBody.right(), vBody.center().y() - 6, vRod, 12))
        pPainter.drawRect(QRectF(vBody.right() + vRod, vBody.center().y() - 22, 14, 44))
        self.draw_sensor(
            pPainter,
            QPointF(vBody.right() + vBody.width() * 0.9 + 34, vBody.top() - 12),
            "fin_sortie",
        )

    def draw_conveyor(self, pPainter, pArea):
        """Tapis avec des pièces qui défilent et le capteur de passage."""
        vBelt = QRectF(pArea.left() + 10, pArea.center().y(), pArea.width() - 20, 26)
        vPitch = vBelt.width() / 4
        vOffset = (self.machine["run"] % PIECE_PERIOD) / PIECE_PERIOD * vPitch

        pPainter.setBrush(QColor("#cbd5e1"))
        pPainter.drawRoundedRect(vBelt, 13, 13)
        pPainter.setBrush(QColor("#f59e0b"))

        for vIndex in range(5):
            vX = vBelt.left() + vIndex * vPitch + vOffset - vPitch * 0.6

            if vBelt.left() <= vX <= vBelt.right() - 30:
                pPainter.drawRect(QRectF(vX, vBelt.top() - 30, 30, 30))

        self.draw_sensor(
            pPainter, QPointF(vBelt.left() + vPitch * 0.5, vBelt.top() - 52), "piece"
        )

    def draw_drill(self, pPainter, pArea):
        """Broche verticale qui descend vers la pièce."""
        vRatio = self.machine["position"] / SPINDLE_STROKE
        vX = pArea.center().x()
        vTop = pArea.top() + 10
        vTravel = pArea.height() - 90

        pPainter.setBrush(QColor("#e2e8f0"))
        pPainter.drawRect(QRectF(vX - 30, vTop, 60, 40))
        pPainter.setBrush(QColor(ON_COLOR if self.values.get("rotation") else STEEL))
        pPainter.drawRect(QRectF(vX - 5, vTop + 40, 10, 20 + vTravel * vRatio))
        pPainter.setBrush(QColor("#cbd5e1"))
        pPainter.drawRect(QRectF(vX - 70, pArea.bottom() - 26, 140, 26))
        self.draw_sensor(pPainter, QPointF(vX + 60, vTop + 10), "haut")
        self.draw_sensor(pPainter, QPointF(vX + 60, vTop + 40 + vTravel), "bas")

    def draw_sensor(self, pPainter, pPoint, pName):
        """Capteur : un carré qui s'allume quand il détecte."""
        pPainter.save()
        pPainter.setBrush(QColor("#f59e0b" if self.values.get(pName) else "#ffffff"))
        pPainter.drawRect(QRectF(pPoint.x(), pPoint.y(), 14, 14))
        pPainter.setFont(QFont(pPainter.font().family(), 8))
        pPainter.drawText(QPointF(pPoint.x() + 18, pPoint.y() + 11), pName)
        pPainter.restore()

    def draw_lamps(self, pPainter, pOrigin):
        """Voyants des sorties, verts allumés ; un voyant de défaut est rouge."""
        vY = pOrigin.y() + LAMP_RADIUS

        for vVariable in self.level["variables"]:
            if vVariable["kind"] != "output":
                continue

            vOn = bool(self.values.get(vVariable["name"]))
            vColor = FAULT_COLOR if "defaut" in vVariable["name"] else ON_COLOR
            pPainter.setBrush(QColor(vColor if vOn else OFF_COLOR))
            pPainter.drawEllipse(
                QPointF(pOrigin.x() + LAMP_RADIUS, vY), LAMP_RADIUS, LAMP_RADIUS
            )
            pPainter.drawText(
                QPointF(pOrigin.x() + LAMP_RADIUS * 2 + 8, vY + 5), vVariable["name"]
            )
            vY += LAMP_RADIUS * 2 + 12
