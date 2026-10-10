"""Page des paramètres : apparence, sources, données et informations"""

from pathlib import Path

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
from gui.theme import COLORS, THEME_CHOICES
from gui.widgets import (
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.sources.registry import SOURCES

THEME_ICONS = {"system": "monitor", "light": "sun", "dark": "moon"}


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


class SettingsPage(QWidget):
    """Regroupe les réglages de l'application et l'état de sa configuration."""

    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile, pThemeChoice):
        """Construit les quatre cartes de la page."""
        super().__init__()

        self.database_file = Path(pDatabaseFile).resolve()

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout, "Paramètres", "Apparence, sources et données de l'application"
        )

        vGrid = QGridLayout()
        vGrid.setSpacing(18)
        vGrid.addWidget(self.create_appearance_card(pThemeChoice), 0, 0)
        vGrid.addWidget(self.create_data_card(), 1, 0)
        vGrid.addWidget(self.create_about_card(), 2, 0)
        vGrid.addWidget(self.create_sources_card(), 0, 1, 3, 1)
        vGrid.setColumnStretch(0, 1)
        vGrid.setColumnStretch(1, 1)

        vLayout.addLayout(vGrid)
        vLayout.addStretch()

    def create_appearance_card(self, pThemeChoice):
        """Construit le choix du thème."""
        vCard, vLayout = create_card("Apparence", "Thème de l'interface")

        self.theme_buttons = QButtonGroup(self)

        vButtons = QHBoxLayout()

        for vChoice, vLabel in THEME_CHOICES.items():
            vButton = create_button(
                vLabel, THEME_ICONS[vChoice], "segmentButton", COLORS["primary"]
            )
            vButton.setCheckable(True)
            vButton.setChecked(vChoice == pThemeChoice)
            vButton.clicked.connect(
                lambda _=False, pChoice=vChoice: self.theme_requested.emit(pChoice)
            )

            self.theme_buttons.addButton(vButton)
            vButtons.addWidget(vButton)

        vButtons.addStretch()
        vLayout.addLayout(vButtons)

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

    def create_data_card(self):
        """Construit l'emplacement de la base de données."""
        vCard, vLayout = create_card("Données", "Base SQLite des offres et du suivi")

        vPath = QLabel(str(self.database_file))
        vPath.setWordWrap(True)

        vButton = create_button(
            "Ouvrir le dossier", "folder-open", pIconColor=COLORS["primary"]
        )
        vButton.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.database_file.parent))
            )
        )

        vLayout.addWidget(vPath)
        vLayout.addWidget(vButton, 0)

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

        Changer de thème recrée la fenêtre, ce qui interromprait la recherche.
        """
        for vButton in self.theme_buttons.buttons():
            vButton.setEnabled(pEnabled)
