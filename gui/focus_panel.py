"""Session de concentration sur l'accueil : objectif, anneau du minuteur, bilan"""

from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.widgets import create_button, create_card, show_message
from job.focus_sessions import (
    build_focus_view,
    finish_focus,
    start_focus,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def format_remaining(pSeconds):
    """Retourne un temps restant en minutes et secondes : 24:05."""

    rText = f"{pSeconds // 60:02d}:{pSeconds % 60:02d}"

    return rText


class FocusRing(QWidget):
    """Anneau qui se vide à mesure que la session avance, temps restant au centre."""

    def __init__(self):
        """Démarre plein, sans session."""
        super().__init__()

        self.share = 1.0
        self.text = ""
        self.setFixedSize(120, 120)

    def set_state(self, pShare, pText):
        """Mémorise la part restante et le texte, puis redessine."""
        self.share = max(0.0, min(pShare, 1.0))
        self.text = pText
        self.update()

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine le fond de l'anneau, la part restante et le temps."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vArea = QRectF(10, 10, self.width() - 20, self.height() - 20)

        vPainter.setPen(QPen(QColor(COLORS["border"]), 10))
        vPainter.drawEllipse(vArea)
        vPen = QPen(QColor(COLORS["primary"]), 10)
        vPen.setCapStyle(Qt.PenCapStyle.RoundCap)
        vPainter.setPen(vPen)
        # Qt compte les angles en seizièmes de degré, depuis 3 h, sens antihoraire
        vPainter.drawArc(vArea, 90 * 16, int(-360 * 16 * self.share))
        vPainter.setPen(QColor(COLORS["text"]))
        vFont = vPainter.font()
        vFont.setPointSize(16)
        vFont.setBold(True)
        vPainter.setFont(vFont)
        vPainter.drawText(vArea, Qt.AlignmentFlag.AlignCenter, self.text)
        vPainter.end()


class FocusPanel(QWidget):
    """Carte de l'accueil : commencer une session, la suivre, lire son bilan."""

    def __init__(self, pDatabaseFile):
        """Construit le choix de l'objectif, l'anneau et le bilan."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.view = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        vCard, vLayout = create_card(
            "Session de concentration",
            "25 minutes sur un seul objectif : les points gagnés pendant la session "
            "comptent double",
            "timer",
            "focus",
            pOpen=True,
        )
        self.ring = FocusRing()
        self.goal_combo = QComboBox()
        self.start_button = create_button(
            "Commencer", "timer", "primaryButton", COLORS["on_primary"]
        )
        self.start_button.clicked.connect(self.start)
        self.stop_button = create_button("Arrêter", "history")
        self.stop_button.clicked.connect(self.stop)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("cardSubtitle")

        vControls = QVBoxLayout()
        vControls.addWidget(self.status_label)
        vRow = QHBoxLayout()
        vRow.addWidget(self.goal_combo, 1)
        vRow.addWidget(self.start_button)
        vRow.addWidget(self.stop_button)
        vControls.addLayout(vRow)
        vControls.addWidget(self.summary_label)

        vRowLayout = QHBoxLayout()
        vRowLayout.addWidget(self.ring)
        vRowLayout.addLayout(vControls, 1)
        vLayout.addLayout(vRowLayout)

        vOuter = QVBoxLayout(self)
        vOuter.setContentsMargins(0, 0, 0, 0)
        vOuter.addWidget(vCard)

    def refresh(self):
        """Relit la session : en cours, le minuteur tourne ; sinon, le dernier bilan."""
        try:
            self.view = build_focus_view(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de lire la session de concentration")
            return

        if not self.goal_combo.count():
            for vGoal, vLabel in self.view["goals"].items():
                self.goal_combo.addItem(vLabel, vGoal)

        vCurrent = self.view["current"]
        self.goal_combo.setVisible(vCurrent is None)
        self.start_button.setVisible(vCurrent is None)
        self.stop_button.setVisible(vCurrent is not None)

        if vCurrent:
            self.status_label.setText(f"Objectif : {vCurrent['goal_label']}")
            self.timer.start(1000)
            self.tick()
        else:
            self.timer.stop()
            self.ring.set_state(1.0, format_remaining(self.view["duration"] * 60))
            self.status_label.setText(
                f"{self.view['today']} session(s) menée(s) à terme aujourd'hui."
            )

        self.show_summary(self.view["last"] if vCurrent is None else None)

    def tick(self):
        """Met à jour l'anneau ; à la fin, clôt la session et affiche le bilan."""
        vCurrent = self.view["current"] if self.view else None

        if vCurrent is None:
            return

        vEnds = datetime.fromisoformat(vCurrent["ends_at"])
        vRemaining = max(0, round((vEnds - datetime.now()).total_seconds()))

        if vRemaining == 0:
            self.finish()
            return

        self.ring.set_state(
            vRemaining / (self.view["duration"] * 60), format_remaining(vRemaining)
        )

    def show_summary(self, pLast):
        """Affiche le bilan d'une session : objectif, actions, points et bonus."""
        if not pLast:
            show_message(self.summary_label, "")
            return

        vActions = "\n".join(f"• {vLine}" for vLine in pLast["lines"]) or (
            "• Aucune action comptée pendant la session"
        )
        show_message(
            self.summary_label,
            f"Dernière session · {pLast['goal_label']} · {pLast['minutes']} min\n"
            f"{vActions}\n"
            + (
                f"{pLast['xp']} points, doublés : +{pLast['bonus']} XP de bonus."
                if pLast["completed"]
                else "Session arrêtée avant la fin : pas de bonus."
            ),
            "success" if pLast["completed"] else None,
        )

    def start(self):
        """Commence une session sur l'objectif choisi."""
        try:
            start_focus(
                self.database_file, self.goal_combo.currentData(), datetime.now()
            )

        except ValueError as vError:
            show_message(self.summary_label, str(vError), "warning")
            return

        self.refresh()

    def finish(self):
        """Clôt la session en cours et affiche son bilan."""
        finish_focus(self.database_file, datetime.now())
        self.refresh()

    def stop(self):
        """Arrête la session avant la fin : bilan sans bonus."""
        self.finish()
