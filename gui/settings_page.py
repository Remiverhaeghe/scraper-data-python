"""Page des paramètres : apparence, règles de calcul, sources et informations"""

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config import APPLICATION_NAME, LICENSE_NAME, REPOSITORY_URL, TAGLINE
from gui.theme import COLORS, THEME_CHOICES, is_dark_theme
from gui.widgets import (
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.presentation import describe_rules
from job.sources.registry import SOURCES

THEME_ICONS = {"light": "sun", "dark": "moon"}


def describe_source_state(pDefinition):
    """Retourne l'icône, sa couleur et le texte de l'état d'une source."""

    vMissing = pDefinition.get_missing_settings()

    if not pDefinition.available:
        rState = ("circle-alert", COLORS["muted"], "Indisponible pour le moment")
    elif vMissing:
        rState = (
            "circle-alert",
            COLORS["warning"],
            "À renseigner dans .env : " + ", ".join(vMissing),
        )
    else:
        rState = ("circle-check", COLORS["success"], "Prête")

    return rState


def create_line(pLabel, pText, pLabelWidth=150):
    """Crée une ligne libellé et texte, utilisée par les cartes de la page."""

    vLabel = QLabel(pLabel)
    vLabel.setObjectName("activityTitle")
    vLabel.setFixedWidth(pLabelWidth)

    vText = QLabel(pText)
    vText.setObjectName("cardSubtitle")
    vText.setWordWrap(True)

    rLayout = QHBoxLayout()
    rLayout.setSpacing(12)
    rLayout.addWidget(vLabel)
    rLayout.addWidget(vText, 1)

    return rLayout


class SettingsPage(QWidget):
    """Regroupe les réglages de l'application et l'état de sa configuration."""

    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les cartes de la page."""
        super().__init__()

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout,
            "Paramètres",
            "Apparence, règles de calcul, sources et informations",
            pIcon="settings",
        )

        vGrid = QGridLayout()
        vGrid.setSpacing(18)
        vGrid.addWidget(self.create_appearance_card(), 0, 0)
        vGrid.addWidget(self.create_rules_card(), 1, 0)
        vGrid.addWidget(self.create_about_card(), 2, 0)
        vGrid.addWidget(self.create_sources_card(), 0, 1, 3, 1)
        vGrid.setColumnStretch(0, 1)
        vGrid.setColumnStretch(1, 1)

        vLayout.addLayout(vGrid)
        vLayout.addStretch()

    def create_appearance_card(self):
        """Construit le choix du thème, mémorisé pour les prochains lancements."""
        vCard, vLayout = create_card("Apparence", "Thème de l'interface")

        self.theme_buttons = QButtonGroup(self)

        vCurrentTheme = "dark" if is_dark_theme() else "light"

        vButtons = QHBoxLayout()

        for vChoice, vLabel in THEME_CHOICES.items():
            vButton = create_button(
                vLabel, THEME_ICONS[vChoice], "segmentButton", COLORS["primary"]
            )
            vButton.setCheckable(True)
            vButton.setChecked(vChoice == vCurrentTheme)
            vButton.clicked.connect(
                lambda _=False, pChoice=vChoice: self.theme_requested.emit(pChoice)
            )

            self.theme_buttons.addButton(vButton)
            vButtons.addWidget(vButton)

        vButtons.addStretch()
        vLayout.addLayout(vButtons)

        return vCard

    def create_rules_card(self):
        """Construit le rappel des règles utilisées pour les chiffres affichés."""
        vCard, vLayout = create_card(
            "Règles de calcul", "Comment les montants et les dates sont obtenus"
        )

        for vLabel, vText in describe_rules():
            vLayout.addLayout(create_line(vLabel, vText))

        return vCard

    def create_sources_card(self):
        """Construit l'état de configuration de chaque source."""
        vCard, vLayout = create_card(
            "Sources",
            "Les clés d'API se renseignent dans le fichier .env, jamais ici",
        )

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(10)

        for vRow, vDefinition in enumerate(SOURCES.values()):
            vIcon, vColor, vText = describe_source_state(vDefinition)

            vName = QLabel(vDefinition.label)
            vName.setObjectName("activityTitle")

            vState = QLabel(vText)
            vState.setObjectName("cardSubtitle")
            vState.setWordWrap(True)

            vGrid.addWidget(create_icon_label(vIcon, vColor, 18), vRow, 0)
            vGrid.addWidget(vName, vRow, 1)
            vGrid.addWidget(vState, vRow, 2)

        vGrid.setColumnStretch(2, 1)

        vLayout.addLayout(vGrid)
        vLayout.addStretch()

        return vCard

    def create_about_card(self):
        """Construit les informations sur l'application."""
        vCard, vLayout = create_card(APPLICATION_NAME, TAGLINE)

        vLicense = QLabel(f"Licence {LICENSE_NAME}. Icônes Lucide, sous licence ISC.")
        vLicense.setObjectName("cardSubtitle")
        vLicense.setWordWrap(True)

        vButton = create_button("Code source sur GitHub", "github")
        vButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL)))

        vLayout.addWidget(vLicense)
        vLayout.addWidget(vButton, 0)

        return vCard

    def set_theme_enabled(self, pEnabled):
        """Bloque le changement de thème pendant une recherche.

        Changer de thème reconstruit les pages, ce qui interromprait la recherche.
        """
        for vButton in self.theme_buttons.buttons():
            vButton.setEnabled(pEnabled)
