"""Carte des récompenses : couleurs d'accent, cadres d'avatar et son de réussite"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import clear_layout, create_card, show_message
from job.cosmetics import choose_cosmetic, set_sounds
from job.progress import describe_level, get_total_xp
from utils.logger import get_logger

logger = get_logger(__name__)


def create_choice_button(pItem, pFrame=False):
    """Crée le bouton d'une récompense : pastille de couleur, coche ou cadenas."""

    vMark = "✓ " if pItem["chosen"] else ""
    vLock = "" if pItem["unlocked"] else f" · niveau {pItem['level']}"
    rButton = QPushButton(f"{vMark}{pItem['label']}{vLock}")
    rButton.setEnabled(pItem["unlocked"])
    rButton.setToolTip(
        "Choisie"
        if pItem["chosen"]
        else (
            "Cliquez pour la choisir"
            if pItem["unlocked"]
            else f"Débloquée au niveau {pItem['level']}"
        )
    )
    vColor = pItem["color"] or COLORS["border"]
    vBorder = (
        f"border: 3px solid {vColor};"
        if pFrame
        else f"border-left: 14px solid {vColor};"
    )
    rButton.setStyleSheet(
        f"QPushButton {{ {vBorder} padding: 6px 10px; border-radius: 8px; }}"
    )

    return rButton


class RewardsCard(QWidget):
    """Choisir une couleur d'accent, un cadre et couper le son ; changed repeint l'interface."""

    changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit la carte ; set_view la remplit."""
        super().__init__()

        self.database_file = pDatabaseFile
        vCard, vLayout = create_card(
            "Récompenses",
            "Chaque niveau débloque de quoi personnaliser l'interface",
            "gift",
            "progress-rewards",
            pOpen=True,
        )
        self.accents_layout = QHBoxLayout()
        self.frames_layout = QHBoxLayout()
        self.sounds_check = QCheckBox(
            "Son court à chaque réussite (niveau, trophée, quête)"
        )
        self.sounds_check.toggled.connect(self.toggle_sounds)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        for vTitle, vRow in (
            ("Couleur d'accent", self.accents_layout),
            ("Cadre du badge de niveau", self.frames_layout),
        ):
            vLabel = QLabel(vTitle)
            vLabel.setObjectName("cardSubtitle")
            vLayout.addWidget(vLabel)
            vLayout.addLayout(vRow)

        vLayout.addWidget(self.sounds_check)
        vLayout.addWidget(self.message_label)

        vOuter = QVBoxLayout(self)
        vOuter.setContentsMargins(0, 0, 0, 0)
        vOuter.addWidget(vCard)

    def set_view(self, pView):
        """Affiche les récompenses, débloquées ou non, et le choix en cours."""
        for vLayout, vItems, vKind in (
            (self.accents_layout, pView["accents"], "accent"),
            (self.frames_layout, pView["frames"], "frame"),
        ):
            clear_layout(vLayout)

            for vItem in vItems:
                vButton = create_choice_button(vItem, vKind == "frame")
                vButton.clicked.connect(
                    lambda _pChecked=False, pKind=vKind, pId=vItem["id"]: self.choose(
                        pKind, pId
                    )
                )
                vLayout.addWidget(vButton)

            vLayout.addStretch(1)

        self.sounds_check.blockSignals(True)
        self.sounds_check.setChecked(pView["sounds"])
        self.sounds_check.blockSignals(False)

    def choose(self, pKind, pId):
        """Enregistre le choix, puis demande de repeindre l'interface."""
        try:
            choose_cosmetic(
                self.database_file,
                pKind,
                pId,
                describe_level(get_total_xp(self.database_file))["level"],
            )

        except ValueError as vError:
            show_message(self.message_label, str(vError), "warning")
            return

        self.changed.emit()

    def toggle_sounds(self, pEnabled):
        """Active ou coupe le son de réussite."""
        set_sounds(self.database_file, pEnabled)
        show_message(
            self.message_label,
            "Son de réussite activé." if pEnabled else "Son de réussite coupé.",
            None,
        )
