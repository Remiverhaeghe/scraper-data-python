"""Éléments animés de la progression : encart du menu, gain de points, célébration

Les animations restent courtes et s'interrompent d'un clic. Le réglage « Jeu et
animations » (Paramètres, Apparence) les rend discrètes ou les coupe ; le réglage
d'accessibilité de Windows qui réduit les animations les rend discrètes aussi.
"""

import ctypes
import math
import random
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSettings,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gui.theme import ACCENTS, COLORS
from gui.widgets import create_icon_label
from job.presentation import CHART_PALETTE

GAME_MODE_SETTING = "game_mode"
GAME_MODES = {"full": "Complet", "discreet": "Discret", "off": "Désactivé"}
GAME_MODE_HELP = {
    "full": "Points, quêtes, confettis au passage de niveau",
    "discreet": "Points et quêtes, sans confettis",
    "off": "Ni encart de niveau ni animation ; la page Progression reste ouverte",
}

# SystemParametersInfo : animations de Windows activées ou non (accessibilité)
SPI_GETCLIENTAREAANIMATION = 0x1042

BAR_ANIMATION_MS = 700
TOAST_MS = 1400
TOAST_RISE = 46
TOAST_MARGIN = 8
TOAST_GAP_MS = 700
CELEBRATION_MS = 2600
CELEBRATION_FADE_MS = 350
CONFETTI_COUNT = 90
FRAME_MS = 16


def prefers_reduced_motion():
    """Indique si Windows demande de réduire les animations."""

    if sys.platform != "win32":
        return False

    vEnabled = ctypes.c_bool(True)

    try:
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(vEnabled), 0
        )

    except (AttributeError, OSError):
        return False

    rReduced = not vEnabled.value

    return rReduced


def get_saved_game_mode():
    """Retourne le mode « Jeu et animations » de ce PC.

    Sans choix enregistré, il suit Windows : discret si les animations y sont
    réduites. Un choix fait dans Paramètres prime ensuite sur Windows.
    """

    vMode = QSettings().value(GAME_MODE_SETTING, None, str)

    if vMode in GAME_MODES:
        rMode = vMode
    else:
        rMode = "discreet" if prefers_reduced_motion() else "full"

    return rMode


def get_game_mode():
    """Retourne le mode appliqué, relu à chaque fois : un changement prend aussitôt."""

    rMode = get_saved_game_mode()

    return rMode


class SidebarProgress(QFrame):
    """Encart du menu latéral : niveau, barre de points et série en cours."""

    clicked = Signal()

    def __init__(self):
        """Construit l'encart vide ; set_progress le remplit."""
        super().__init__()

        self.setObjectName("sidebarProgress")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Votre progression : niveau, quêtes et série")
        vColor, vBackground = ACCENTS["blue"]
        self.setStyleSheet(
            f"QFrame#sidebarProgress {{ background: {vBackground}; "
            "border-radius: 12px; }"
        )

        self.level_label = QLabel("1")
        self.level_label.setFixedSize(28, 28)
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_label.setStyleSheet(
            f"background: {vColor}; color: {COLORS['on_primary']}; "
            "border-radius: 14px; font-weight: 700;"
        )

        self.title_label = QLabel()
        self.title_label.setStyleSheet(f"color: {vColor}; font-weight: 600;")

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: {COLORS['surface']}; border: none; "
            "border-radius: 3px; }"
            f"QProgressBar::chunk {{ background: {vColor}; border-radius: 3px; }}"
        )

        vAmber = ACCENTS["amber"][0]
        self.streak_icon = create_icon_label("flame", vAmber, 16)
        self.streak_label = QLabel()
        self.streak_label.setStyleSheet(f"color: {vAmber}; font-weight: 600;")

        # Compact : le menu garde la place de toutes ses pages. Le détail (points
        # du niveau, série) est dans l'infobulle et sur la page Progression.
        vTop = QHBoxLayout()
        vTop.setSpacing(8)
        vTop.addWidget(self.level_label)
        vTop.addWidget(self.title_label, 1)
        vTop.addWidget(self.streak_icon)
        vTop.addWidget(self.streak_label)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(10, 8, 10, 8)
        vLayout.setSpacing(6)
        vLayout.addLayout(vTop)
        vLayout.addWidget(self.bar)

        self.bar_animation = QPropertyAnimation(self.bar, b"value", self)
        self.bar_animation.setDuration(BAR_ANIMATION_MS)
        self.bar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_progress(self, pProgress, pAnimate=False):
        """Affiche la progression ; la barre se remplit en douceur si pAnimate."""
        self.level_label.setText(str(pProgress["level"]))
        self.title_label.setText(pProgress["title"])
        self.streak_label.setText(str(pProgress["streak"]))
        self.setToolTip(
            f"Niveau {pProgress['level']} · {pProgress['xp_in_level']} / "
            f"{pProgress['xp_for_level']} XP\n{describe_streak(pProgress)}\n"
            "Cliquez pour voir vos quêtes"
        )
        self.bar.setMaximum(pProgress["xp_for_level"])

        if pAnimate:
            self.bar_animation.stop()
            self.bar_animation.setStartValue(min(self.bar.value(), self.bar.maximum()))
            self.bar_animation.setEndValue(pProgress["xp_in_level"])
            self.bar_animation.start()
        else:
            self.bar.setValue(pProgress["xp_in_level"])

    def mouseReleaseEvent(self, pEvent):  # pylint: disable=invalid-name
        """Ouvre la page Progression d'un clic."""
        if pEvent.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

        super().mouseReleaseEvent(pEvent)


def describe_streak(pProgress):
    """Retourne la série en cours en quelques mots, encourageante si elle est à zéro."""

    vStreak = pProgress["streak"]

    if not vStreak:
        rText = "Une action aujourd'hui lance la série"
    elif pProgress["active_today"]:
        rText = f"Série de {vStreak} jour{'s' if vStreak > 1 else ''}"
    else:
        rText = f"Série de {vStreak} jour{'s' if vStreak > 1 else ''} : à prolonger"

    return rText


def show_xp_gain(pWindow, pAnchor, pText, pDelayMs=0):
    """Fait monter un « +15 XP » au-dessus de pAnchor, puis l'efface.

    pDelayMs décale les messages successifs pour qu'ils ne se recouvrent pas.
    """

    vToast = QLabel(pText, pWindow)
    vToast.setStyleSheet(
        f"background: {ACCENTS['green'][1]}; color: {ACCENTS['green'][0]}; "
        "border-radius: 12px; padding: 4px 12px; font-weight: 700;"
    )
    vToast.adjustSize()

    # Centré sur pAnchor, sans sortir de la fenêtre à gauche
    vCenter = pAnchor.mapTo(pWindow, QPoint(pAnchor.width() // 2, 0))
    vStart = QPoint(
        max(TOAST_MARGIN, vCenter.x() - vToast.width() // 2),
        vCenter.y() - vToast.height(),
    )
    vToast.move(vStart)
    vToast.hide()

    vOpacity = QGraphicsOpacityEffect(vToast)
    vToast.setGraphicsEffect(vOpacity)

    vRise = QPropertyAnimation(vToast, b"pos", vToast)
    vRise.setDuration(TOAST_MS)
    vRise.setStartValue(vStart)
    vRise.setEndValue(vStart - QPoint(0, TOAST_RISE))
    vRise.setEasingCurve(QEasingCurve.Type.OutCubic)

    vFade = QPropertyAnimation(vOpacity, b"opacity", vToast)
    vFade.setDuration(TOAST_MS)
    vFade.setKeyValueAt(0, 1.0)
    vFade.setKeyValueAt(0.6, 1.0)
    vFade.setKeyValueAt(1, 0.0)
    vFade.finished.connect(vToast.deleteLater)

    def start():
        """Affiche le message et lance sa montée."""
        vToast.show()
        vToast.raise_()
        vRise.start()
        vFade.start()

    QTimer.singleShot(pDelayMs, start)

    return vToast


class CelebrationOverlay(QWidget):
    """Célébration plein écran : confettis et carte du nouveau niveau.

    Elle se ferme seule après quelques secondes, ou d'un clic.
    """

    def __init__(self, pWindow, pTitle, pSubtitle, pDetail=""):
        """Couvre la fenêtre et lance l'animation."""
        super().__init__(pWindow)

        self.title = pTitle
        self.subtitle = pSubtitle
        self.detail = pDetail
        self.setGeometry(pWindow.rect())
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Position des confettis, sans usage cryptographique.
        vRandom = random.Random()  # nosec B311
        self.confetti = [
            {
                "x": vRandom.uniform(0, self.width()),
                "y": vRandom.uniform(-self.height() * 0.6, -10),
                "speed": vRandom.uniform(0.18, 0.42),
                "drift": vRandom.uniform(-0.06, 0.06),
                "spin": vRandom.uniform(-0.012, 0.012),
                "angle": vRandom.uniform(0, math.pi),
                "size": vRandom.uniform(6, 12),
                "color": QColor(vRandom.choice(CHART_PALETTE)),
            }
            for _ in range(CONFETTI_COUNT)
        ]

        self.clock = QElapsedTimer()
        self.clock.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(FRAME_MS)

        self.show()
        self.raise_()

    def tick(self):
        """Avance l'animation, puis ferme la célébration à son terme."""
        if self.clock.elapsed() >= CELEBRATION_MS + CELEBRATION_FADE_MS:
            self.close_celebration()
        else:
            self.update()

    def close_celebration(self):
        """Arrête l'animation et retire la célébration."""
        self.timer.stop()
        self.hide()
        self.deleteLater()

    def mouseReleaseEvent(self, pEvent):  # pylint: disable=invalid-name
        """Ferme la célébration d'un clic."""
        self.close_celebration()

        super().mouseReleaseEvent(pEvent)

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine le voile, les confettis et la carte qui grandit puis s'efface."""
        vElapsed = self.clock.elapsed()
        vFade = (
            1.0
            if vElapsed < CELEBRATION_MS
            else max(0.0, 1 - (vElapsed - CELEBRATION_MS) / CELEBRATION_FADE_MS)
        )

        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vPainter.setOpacity(vFade)
        vPainter.fillRect(self.rect(), QColor(15, 23, 42, 110))

        for vPiece in self.confetti:
            vX = vPiece["x"] + vPiece["drift"] * vElapsed
            vY = vPiece["y"] + vPiece["speed"] * vElapsed
            vPainter.save()
            vPainter.translate(vX, vY % (self.height() + 40))
            vPainter.rotate(math.degrees(vPiece["angle"] + vPiece["spin"] * vElapsed))
            vPainter.fillRect(
                QRectF(
                    -vPiece["size"] / 2,
                    -vPiece["size"] / 4,
                    vPiece["size"],
                    vPiece["size"] / 2,
                ),
                vPiece["color"],
            )
            vPainter.restore()

        # La carte grandit avec un léger rebond pendant le premier tiers de seconde.
        vScale = QEasingCurve(QEasingCurve.Type.OutBack).valueForProgress(
            min(1.0, vElapsed / 350)
        )
        vWidth, vHeight = 360, 190
        vPainter.translate(self.width() / 2, self.height() / 2)
        vPainter.scale(vScale, vScale)

        vCard = QRectF(-vWidth / 2, -vHeight / 2, vWidth, vHeight)
        vPainter.setPen(Qt.PenStyle.NoPen)
        vPainter.setBrush(QColor(COLORS["surface"]))
        vPainter.drawRoundedRect(vCard, 18, 18)

        # Tailles en pixels : la feuille de style en donne une, pas en points.
        vFont = QFont(self.font())
        vFont.setPixelSize(44)
        vFont.setBold(True)
        vPainter.setFont(vFont)
        vPainter.setPen(QColor(COLORS["primary"]))
        vPainter.drawText(
            QRectF(vCard.left(), vCard.top() + 22, vWidth, 60),
            Qt.AlignmentFlag.AlignCenter,
            self.title,
        )

        vFont.setPixelSize(22)
        vPainter.setFont(vFont)
        vPainter.setPen(QColor(COLORS["heading"]))
        vPainter.drawText(
            QRectF(vCard.left(), vCard.top() + 90, vWidth, 34),
            Qt.AlignmentFlag.AlignCenter,
            self.subtitle,
        )

        vPainter.setFont(self.font())
        vPainter.setPen(QColor(COLORS["muted"]))
        vPainter.drawText(
            QRectF(vCard.left() + 16, vCard.top() + 130, vWidth - 32, 40),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.detail,
        )

        vPainter.end()
