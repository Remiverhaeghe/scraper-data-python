"""Page des paramètres : apparence, règles de calcul, sources et informations"""

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config import (
    APPLICATION_NAME,
    CONTACT_URL,
    LICENSE_NAME,
    LICENSE_URL,
    REPOSITORY_URL,
    TAGLINE,
)
from gui.theme import COLORS, THEME_CHOICES, is_dark_theme
from gui.widgets import (
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.registry import SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)

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


class SettingsPage(QWidget):
    """Regroupe les réglages de l'application et l'état de sa configuration."""

    theme_requested = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les cartes de la page."""
        super().__init__()

        self.database_file = pDatabaseFile

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
        vGrid.addWidget(self.create_rules_card(), 1, 0, 2, 1)
        vGrid.addWidget(self.create_sources_card(), 0, 1, 2, 1)
        vGrid.addWidget(self.create_about_card(), 2, 1)
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
        """Construit le formulaire des règles de calcul, enregistrées en base."""
        vCard, vLayout = create_card(
            "Règles de calcul",
            "Partagées avec le tableau de bord web ; le net des offres est recalculé",
        )

        vSettings = load_settings(self.database_file)

        self.setting_spins = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(10)

        for vRow, (vKey, vDefinition) in enumerate(SETTING_DEFINITIONS.items()):
            vSpin = QDoubleSpinBox()
            vSpin.setDecimals(0 if vDefinition.is_integer else 1)
            vSpin.setRange(vDefinition.minimum, vDefinition.maximum)
            vSpin.setSingleStep(vDefinition.step)
            vSpin.setSuffix(f" {vDefinition.unit}")
            vSpin.setValue(vSettings[vKey])
            vSpin.setToolTip(vDefinition.help)
            vSpin.setFixedWidth(150)

            vName = QLabel(vDefinition.label)
            vName.setObjectName("activityTitle")

            vHelp = QLabel(vDefinition.help)
            vHelp.setObjectName("cardSubtitle")
            vHelp.setWordWrap(True)

            vTexts = QVBoxLayout()
            vTexts.setSpacing(2)
            vTexts.addWidget(vName)
            vTexts.addWidget(vHelp)

            vGrid.addLayout(vTexts, vRow, 0)
            vGrid.addWidget(vSpin, vRow, 1)

            self.setting_spins[vKey] = vSpin

        vGrid.setColumnStretch(0, 1)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save_rules)

        self.rules_message = QLabel()
        self.rules_message.setObjectName("cardSubtitle")
        self.rules_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.rules_message, 1)

        vLayout.addLayout(vGrid)
        vLayout.addLayout(vActions)

        return vCard

    def save_rules(self):
        """Enregistre les règles de calcul et indique les offres recalculées."""
        vValues = {vKey: vSpin.value() for vKey, vSpin in self.setting_spins.items()}

        try:
            _, vRecomputed = save_settings(self.database_file, vValues)

        except ValueError as vException:
            self.rules_message.setText(str(vException))

        except Exception:
            logger.exception("Échec de l'enregistrement des règles de calcul")

            self.rules_message.setText("Les règles n'ont pas pu être enregistrées.")

        else:
            self.rules_message.setText(
                f"Règles enregistrées, salaire net recalculé pour {vRecomputed} offre(s)."
                if vRecomputed
                else "Règles enregistrées."
            )

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

        vLicense = QLabel(
            f'<a href="{LICENSE_URL}">Licence {LICENSE_NAME}</a>. '
            "Icônes Lucide, sous licence ISC."
        )
        vLicense.setObjectName("cardSubtitle")
        vLicense.setWordWrap(True)
        vLicense.setOpenExternalLinks(True)

        vGithubButton = create_button("Code source sur GitHub", "github")
        vGithubButton.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL))
        )

        vContactButton = create_button(
            "Me contacter sur LinkedIn", "linkedin", pIconColor=COLORS["primary"]
        )
        vContactButton.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(CONTACT_URL))
        )

        vButtons = QHBoxLayout()
        vButtons.addWidget(vGithubButton)
        vButtons.addWidget(vContactButton)

        vLayout.addWidget(vLicense)
        vLayout.addLayout(vButtons)

        return vCard

    def set_theme_enabled(self, pEnabled):
        """Bloque le changement de thème pendant une recherche.

        Changer de thème reconstruit les pages, ce qui interromprait la recherche.
        """
        for vButton in self.theme_buttons.buttons():
            vButton.setEnabled(pEnabled)
