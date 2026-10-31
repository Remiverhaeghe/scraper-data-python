"""Visite guidée en surimpression : la mascotte présente les pages principales

Un voile sombre couvre la fenêtre ; la carte de Boulon apparaît en fondu à
chaque étape, pendant que la page présentée s'ouvre derrière.
"""

from PySide6.QtCore import QByteArray, QEvent, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button
from job.onboarding import build_tour

FADE_MS = 300


class TourOverlay(QWidget):
    """Voile et carte de la visite ; finished est émis à la fin ou quand on passe."""

    finished = Signal()

    def __init__(self, pWindow, pNavigate):
        """Couvre la fenêtre et montre la première étape."""
        super().__init__(pWindow)

        self.navigate = pNavigate
        self.steps = build_tour()
        self.index = 0
        self.setGeometry(pWindow.rect())
        pWindow.installEventFilter(self)

        self.card = QFrame(self)
        # La surimpression n'hérite pas du style des pages : la carte a le sien
        self.card.setObjectName("tourCard")
        self.card.setStyleSheet(
            f"QFrame#tourCard {{ background: {COLORS['surface']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 16px; }}"
        )
        self.card.setFixedWidth(560)
        self.mascot = QSvgWidget()
        self.mascot.setFixedSize(110, 110)
        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.step_label = QLabel()
        self.step_label.setObjectName("cardSubtitle")
        self.previous_button = create_button("Précédent")
        self.previous_button.clicked.connect(lambda: self.show_step(self.index - 1))
        self.next_button = create_button(
            "Suivant", "arrow-right", "primaryButton", COLORS["on_primary"]
        )
        self.next_button.clicked.connect(self.next_step)
        self.skip_button = create_button("Passer la visite")
        self.skip_button.clicked.connect(self.close_tour)

        vTexts = QVBoxLayout()
        vTexts.addWidget(self.title_label)
        vTexts.addWidget(self.text_label)
        vTexts.addWidget(self.step_label)
        vTop = QHBoxLayout()
        vTop.addWidget(self.mascot)
        vTop.addLayout(vTexts, 1)
        vButtons = QHBoxLayout()
        vButtons.addWidget(self.skip_button)
        vButtons.addStretch(1)
        vButtons.addWidget(self.previous_button)
        vButtons.addWidget(self.next_button)
        vLayout = QVBoxLayout(self.card)
        vLayout.setContentsMargins(24, 20, 24, 20)
        vLayout.addLayout(vTop)
        vLayout.addLayout(vButtons)

        self.effect = QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", self)
        self.animation.setDuration(FADE_MS)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)

        self.show_step(0)
        self.show()
        self.raise_()

    def eventFilter(self, pObject, pEvent):  # pylint: disable=invalid-name
        """Suit la taille de la fenêtre pour la couvrir entièrement."""
        if pObject is self.parent() and pEvent.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            self.place_card()

        return super().eventFilter(pObject, pEvent)

    def place_card(self):
        """Centre la carte en bas de la fenêtre, pour laisser voir la page."""
        self.card.adjustSize()
        self.card.move(
            (self.width() - self.card.width()) // 2,
            max(20, self.height() - self.card.height() - 40),
        )

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine le voile qui assombrit la page derrière la carte."""
        vPainter = QPainter(self)
        vPainter.fillRect(self.rect(), QColor(15, 23, 42, 110))
        vPainter.end()

    def show_step(self, pIndex):
        """Ouvre la page de l'étape et montre la carte en fondu."""
        self.index = max(0, min(pIndex, len(self.steps) - 1))
        vStep = self.steps[self.index]

        self.navigate(vStep["page"])
        self.mascot.load(QByteArray(vStep["svg"].encode("utf-8")))
        self.title_label.setText(vStep["title"])
        self.text_label.setText(vStep["text"])
        self.step_label.setText(f"Étape {vStep['position']} sur {vStep['count']}")
        self.previous_button.setEnabled(self.index > 0)
        self.next_button.setText(
            "Terminer" if self.index == len(self.steps) - 1 else "Suivant"
        )
        self.place_card()
        self.raise_()
        self.animation.stop()
        self.animation.start()

    def next_step(self):
        """Passe à l'étape suivante, ou termine la visite sur la dernière."""
        if self.index == len(self.steps) - 1:
            self.close_tour()
        else:
            self.show_step(self.index + 1)

    def close_tour(self):
        """Ferme la visite et revient à l'accueil."""
        self.parent().removeEventFilter(self)
        self.navigate("home")
        self.hide()
        self.deleteLater()
        self.finished.emit()

    def keyPressEvent(self, pEvent):  # pylint: disable=invalid-name
        """Échap passe la visite, les flèches changent d'étape."""
        if pEvent.key() == Qt.Key.Key_Escape:
            self.close_tour()
        elif pEvent.key() == Qt.Key.Key_Right:
            self.next_step()
        elif pEvent.key() == Qt.Key.Key_Left:
            self.show_step(self.index - 1)
        else:
            super().keyPressEvent(pEvent)
