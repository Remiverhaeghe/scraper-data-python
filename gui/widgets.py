"""Composants graphiques partagés entre les pages"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


def create_page_header(pLayout, pTitle, pSubtitle):
    """Ajoute le titre et le sous-titre d'une page à son layout."""

    vTitle = QLabel(pTitle)
    vTitle.setObjectName("pageTitle")

    vSubtitle = QLabel(pSubtitle)
    vSubtitle.setObjectName("pageSubtitle")

    pLayout.addWidget(vTitle)
    pLayout.addWidget(vSubtitle)
    pLayout.addSpacing(16)


class StatisticCard(QFrame):
    """Affiche une valeur chiffrée et son libellé."""

    def __init__(self, pLabel):
        """Construit la carte avec une valeur vide."""
        super().__init__()

        self.setObjectName("statisticCard")

        self.value_label = QLabel("-")
        self.value_label.setObjectName("statisticValue")

        vLabel = QLabel(pLabel)
        vLabel.setObjectName("statisticLabel")
        vLabel.setWordWrap(True)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(18, 14, 18, 14)
        vLayout.addWidget(self.value_label)
        vLayout.addWidget(vLabel)

    def set_value(self, pValue):
        """Met à jour la valeur affichée."""
        self.value_label.setText(str(pValue))
