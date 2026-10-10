"""Composants graphiques partagés entre les pages"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from gui.icons import get_icon
from gui.theme import ACCENTS, COLORS


def create_page_header(pLayout, pTitle, pSubtitle, pActions=()):
    """Ajoute le titre, le sous-titre et les boutons d'action d'une page."""

    vTitle = QLabel(pTitle)
    vTitle.setObjectName("pageTitle")

    vSubtitle = QLabel(pSubtitle)
    vSubtitle.setObjectName("pageSubtitle")
    vSubtitle.setWordWrap(True)

    vTexts = QVBoxLayout()
    vTexts.setSpacing(4)
    vTexts.addWidget(vTitle)
    vTexts.addWidget(vSubtitle)

    vHeader = QHBoxLayout()
    vHeader.addLayout(vTexts, 1)

    for vAction in pActions:
        vHeader.addWidget(vAction, 0, Qt.AlignmentFlag.AlignTop)

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

    def __init__(self, pLabel, pIcon, pAccent):
        """Construit la carte avec une valeur vide."""
        super().__init__()

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

        vLabel = QLabel(pLabel)
        vLabel.setObjectName("statisticLabel")
        vLabel.setWordWrap(True)

        vTexts = QVBoxLayout()
        vTexts.setSpacing(0)
        vTexts.addWidget(self.value_label)
        vTexts.addWidget(vLabel)

        vLayout = QHBoxLayout(self)
        vLayout.setContentsMargins(18, 16, 18, 16)
        vLayout.setSpacing(14)
        vLayout.addWidget(vIcon)
        vLayout.addLayout(vTexts, 1)

    def set_value(self, pValue):
        """Met à jour la valeur affichée."""
        self.value_label.setText(str(pValue))
