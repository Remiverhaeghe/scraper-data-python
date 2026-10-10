"""Composants graphiques partagés entre les pages"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from gui.icons import get_icon
from gui.theme import ACCENTS, COLORS


def create_page_header(pLayout, pTitle, pSubtitle, pActions=(), pIcon=None):
    """Ajoute le titre, son icône, le sous-titre et les boutons d'action d'une page."""

    vTitle = QLabel(pTitle)
    vTitle.setObjectName("pageTitle")

    vTitleRow = QHBoxLayout()
    vTitleRow.setSpacing(12)

    if pIcon is not None:
        vIcon = create_icon_label(pIcon, COLORS["primary"], 22)
        vIcon.setObjectName("pageIcon")
        vIcon.setFixedSize(40, 40)
        vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vTitleRow.addWidget(vIcon)

    vTitleRow.addWidget(vTitle)
    vTitleRow.addStretch()

    vSubtitle = QLabel(pSubtitle)
    vSubtitle.setObjectName("pageSubtitle")
    vSubtitle.setWordWrap(True)

    vTexts = QVBoxLayout()
    vTexts.setSpacing(4)
    vTexts.addLayout(vTitleRow)
    vTexts.addWidget(vSubtitle)

    vHeader = QHBoxLayout()
    vHeader.addLayout(vTexts, 1)

    for vAction in pActions:
        vHeader.addWidget(vAction, 0, Qt.AlignmentFlag.AlignVCenter)

    pLayout.addLayout(vHeader)
    pLayout.addSpacing(18)


def create_button(pText, pIcon=None, pObjectName=None, pIconColor=None):
    """Crée un bouton, éventuellement avec une icône et un style nommé."""

    rButton = QPushButton(pText)
    rButton.setCursor(Qt.CursorShape.PointingHandCursor)

    if pObjectName is not None:
        rButton.setObjectName(pObjectName)

    if pIcon is not None:
        rButton.setIcon(get_icon(pIcon, pIconColor or COLORS["text"], 18))
        rButton.setIconSize(QSize(18, 18))

    return rButton


def create_card(pTitle=None, pSubtitle=None):
    """Crée une carte blanche et retourne la carte et son layout de contenu."""

    vCard = QFrame()
    vCard.setObjectName("card")

    vLayout = QVBoxLayout(vCard)
    vLayout.setContentsMargins(20, 18, 20, 18)
    vLayout.setSpacing(10)

    if pTitle is not None:
        vTitle = QLabel(pTitle)
        vTitle.setObjectName("cardTitle")
        vLayout.addWidget(vTitle)

    if pSubtitle is not None:
        vSubtitle = QLabel(pSubtitle)
        vSubtitle.setObjectName("cardSubtitle")
        vLayout.addWidget(vSubtitle)

    rCard = (vCard, vLayout)

    return rCard


def create_icon_label(pIcon, pColor, pSize=20):
    """Crée un libellé affichant uniquement une icône."""

    rLabel = QLabel()
    rLabel.setPixmap(get_icon(pIcon, pColor, pSize).pixmap(pSize, pSize))

    return rLabel


class StatisticCard(QFrame):
    """Affiche une valeur chiffrée sur fond coloré, avec son icône et son libellé."""

    clicked = Signal()

    def __init__(self, pLabel, pIcon, pAccent, pClickable=False):
        """Construit la carte avec une valeur vide."""
        super().__init__()

        if pClickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        vColor, vBackground = ACCENTS[pAccent]

        self.setObjectName("statisticCard")
        self.setStyleSheet(
            f"QFrame#statisticCard {{ background: {vBackground}; border-radius: 12px; }}"
            f"QLabel#statisticValue {{ color: {vColor}; }}"
        )

        vIcon = create_icon_label(pIcon, vColor, 22)
        vIcon.setFixedSize(44, 44)
        vIcon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vIcon.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 10px;")

        self.value_label = QLabel("-")
        self.value_label.setObjectName("statisticValue")

        self.label = QLabel(pLabel)
        self.label.setObjectName("statisticLabel")
        self.label.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(0)
        vTexts.addWidget(self.value_label)
        vTexts.addWidget(self.label)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(18, 16, 18, 16)
        vLayout.setSpacing(14)
        vLayout.addWidget(vIcon)
        vLayout.addLayout(vTexts, 1)

    def set_value(self, pValue):
        """Met à jour la valeur affichée."""
        self.value_label.setText(str(pValue))

    def set_label(self, pLabel):
        """Met à jour le libellé, lorsqu'il dépend d'un réglage."""
        self.label.setText(pLabel)

    def mouseReleaseEvent(self, pEvent):
        """Émet clicked lorsque la carte est cliquée."""
        super().mouseReleaseEvent(pEvent)

        if self.rect().contains(pEvent.position().toPoint()):
            self.clicked.emit()
