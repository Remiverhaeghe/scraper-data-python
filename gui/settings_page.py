"""Page des paramètres : apparence, règles, planification, notifications, sources"""

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.calculation_rules_panel import CalculationRulesPanel
from gui.company_lists_panel import CompanyListsPanel
from gui.token_access_panel import TokenAccessPanel
from gui.company_pages_panel import CompanyPagesPanel
from gui.home_location_panel import HomeLocationPanel
from gui.notification_panel import NotificationPanel
from gui.schedule_panel import SchedulePanel
from gui.progress_widgets import (
    GAME_MODE_HELP,
    GAME_MODE_SETTING,
    GAME_MODES,
    get_saved_game_mode,
)
from gui.data_panel import DataPanel
from gui.theme import (
    COLORS,
    TEXT_SCALE_SETTING,
    TEXT_SCALES,
    THEME_CHOICES,
    THEME_SETTING,
)
from gui.widgets import (
    create_button,
    create_card,
    create_fold_button,
    create_icon_label,
    create_page_header,
    create_scroll_content,
)
from config import WEB_BASE_URL
from job.calendar import (
    build_subscription_url,
    get_calendar_token,
    renew_calendar_token,
)
from job.mobile_sync import (
    API_PREFIX,
    build_connection_png,
    get_certificate_fingerprint,
    get_mobile_token,
    renew_mobile_token,
)
from job.sources.registry import SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)

THEME_ICONS = {"system": "monitor", "light": "sun", "dark": "moon"}

# En dessous de cette largeur de page, les cartes passent sur une colonne.
SINGLE_COLUMN_WIDTH = 1100


def describe_source_state(pDefinition):
    """Retourne l'icône, sa couleur et le texte de l'état d'une source."""

    vMissing = pDefinition.describe_missing()

    if not pDefinition.available:
        rState = ("circle-alert", COLORS["muted"], "Indisponible pour le moment")
    elif vMissing:
        rState = (
            "circle-alert",
            COLORS["muted"] if pDefinition.companies else COLORS["warning"],
            vMissing,
        )
    else:
        rState = ("circle-check", COLORS["success"], "Prête")

    return rState


class SettingsPage(QWidget):
    """Regroupe les réglages de l'application et l'état de sa configuration."""

    theme_requested = Signal(str)
    text_scale_requested = Signal(int)
    game_mode_changed = Signal()
    data_reset = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les cartes de la page."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout,
            "Paramètres",
            "Apparence, règles de calcul, planification, notifications et sources",
            [create_fold_button(self)],
            pIcon="settings",
        )

        self.create_access_panels()

        self.data_panel = DataPanel(pDatabaseFile)
        self.data_panel.data_reset.connect(self.data_reset)

        self.company_pages_panel = CompanyPagesPanel(pDatabaseFile)
        self.home_panel = HomeLocationPanel(pDatabaseFile)
        self.rules_panel = CalculationRulesPanel(pDatabaseFile)
        self.schedule_panel = SchedulePanel(pDatabaseFile)
        self.notification_panel = NotificationPanel(pDatabaseFile)
        self.company_lists_panel = CompanyListsPanel(pDatabaseFile)

        # Deux colonnes indépendantes : dans une grille, une carte courte prendrait
        # la hauteur de sa voisine et s'étirerait.
        # Deux colonnes sur un écran large, une seule dans une fenêtre réduite :
        # les cartes sont redistribuées au redimensionnement (resizeEvent).
        self.card_groups = (
            [
                self.create_appearance_card(),
                self.rules_panel,
                self.schedule_panel,
                self.calendar_panel,
                self.mobile_panel,
            ],
            [
                self.notification_panel,
                self.create_sources_card(),
                self.company_pages_panel,
                self.home_panel,
                self.company_lists_panel,
                self.data_panel,
            ],
        )
        self.columns = []
        self.single_column = None

        vColumns = QHBoxLayout()
        vColumns.setSpacing(18)

        for _ in self.card_groups:
            vColumn = QVBoxLayout()
            vColumn.setSpacing(18)
            self.columns.append(vColumn)
            vColumns.addLayout(vColumn, 1)

        self.arrange_cards(False)

        vLayout.addLayout(vColumns, 1)

        self.schedule_panel.refresh()
        self.notification_panel.refresh()
        self.calendar_panel.refresh()
        self.mobile_panel.refresh()
        self.company_pages_panel.refresh()
        self.home_panel.refresh()

    def arrange_cards(self, pSingleColumn):
        """Range les cartes sur une colonne, ou sur deux côte à côte."""
        if pSingleColumn == self.single_column:
            return

        self.single_column = pSingleColumn

        for vColumn in self.columns:
            while vColumn.count():
                vColumn.takeAt(0)

        vGroups = (
            (self.card_groups[0] + self.card_groups[1], [])
            if pSingleColumn
            else self.card_groups
        )

        for vColumn, vCards in zip(self.columns, vGroups):
            for vCard in vCards:
                vColumn.addWidget(vCard)

            # Facteur 1 : l'espace libre va au ressort, une carte ouverte garde sa
            # hauteur au lieu de s'étirer jusqu'au bas de la colonne voisine.
            vColumn.addStretch(1)

    def resizeEvent(self, pEvent):  # pylint: disable=invalid-name
        """Passe sur une colonne quand la page devient trop étroite pour deux."""
        super().resizeEvent(pEvent)

        self.arrange_cards(self.width() < SINGLE_COLUMN_WIDTH)

    def create_appearance_card(self):
        """Construit le choix du thème, mémorisé pour les prochains lancements."""
        vCard, vLayout = create_card("Apparence", "Thème et taille du texte")

        self.theme_buttons = QButtonGroup(self)

        # Le choix mémorisé, et non le thème affiché : « Auto » reste coché même
        # quand Windows est en clair.
        vCurrentTheme = QSettings().value(THEME_SETTING, "system", str)

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

        self.text_scale_buttons = QButtonGroup(self)
        vCurrentScale = QSettings().value(TEXT_SCALE_SETTING, 100, int)

        vScaleButtons = QHBoxLayout()
        vScaleButtons.addWidget(QLabel("Taille du texte"))

        for vScale, vLabel in TEXT_SCALES.items():
            vButton = create_button(vLabel, pObjectName="segmentButton")
            vButton.setCheckable(True)
            vButton.setChecked(vScale == vCurrentScale)
            vButton.clicked.connect(
                lambda _=False, pScale=vScale: self.text_scale_requested.emit(pScale)
            )

            self.text_scale_buttons.addButton(vButton)
            vScaleButtons.addWidget(vButton)

        vScaleButtons.addStretch()
        vLayout.addLayout(vScaleButtons)

        # Appliqué sans reconstruire les pages : la fenêtre relit ce réglage.
        self.game_mode_buttons = QButtonGroup(self)
        vCurrentMode = get_saved_game_mode()

        vGameButtons = QHBoxLayout()
        vGameButtons.addWidget(QLabel("Jeu et animations"))

        for vMode, vLabel in GAME_MODES.items():
            vButton = create_button(vLabel, pObjectName="segmentButton")
            vButton.setCheckable(True)
            vButton.setChecked(vMode == vCurrentMode)
            vButton.setToolTip(GAME_MODE_HELP[vMode])
            vButton.clicked.connect(
                lambda _=False, pMode=vMode: self.save_game_mode(pMode)
            )

            self.game_mode_buttons.addButton(vButton)
            vGameButtons.addWidget(vButton)

        vGameButtons.addStretch()
        vLayout.addLayout(vGameButtons)

        return vCard

    def save_game_mode(self, pMode):
        """Mémorise le réglage « Jeu et animations » de ce PC."""
        QSettings().setValue(GAME_MODE_SETTING, pMode)
        logger.info("Jeu et animations : %s", GAME_MODES[pMode])
        self.game_mode_changed.emit()

    def create_sources_card(self):
        """Construit l'état de configuration de chaque source."""
        vCard, vLayout = create_card(
            "Sources",
            "Les clés d'API se renseignent dans le fichier .env, jamais ici",
        )

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(10)

        # Le fichier .env n'est lu qu'au démarrage (config.py) : après l'avoir modifié,
        # relancer l'application pour voir l'état des sources à jour.
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

    def refresh(self):
        """Relit la planification et les entreprises à l'affichage de la page."""
        self.schedule_panel.refresh()
        self.notification_panel.refresh()
        self.company_lists_panel.refresh()

    def create_access_panels(self):
        """Construit les accès secrets : agenda par adresse et application mobile."""
        self.calendar_panel = TokenAccessPanel(
            {
                "title": "Abonnement à l'agenda",
                "subtitle": "Relances et entretiens relus automatiquement par "
                "l'agenda du téléphone ou du PC, sur le réseau local ou par Tailscale.",
                "placeholder": "Aucune adresse créée",
                "create": "Créer l'adresse",
                "renew": "Renouveler l'adresse",
                "icon": "calendar",
                "tooltip": "Une nouvelle adresse désactive l'ancienne",
                "confirm": "L'adresse actuelle cessera de fonctionner : les agendas "
                "abonnés devront utiliser la nouvelle. Continuer ?",
                "created": "Adresse créée : ajoutez-la dans l'agenda comme agenda "
                "par URL.",
                "copied": "Adresse copiée.",
                "failed": "L'adresse n'a pas pu être créée.",
            },
            lambda: build_subscription_url(
                WEB_BASE_URL, get_calendar_token(self.database_file)
            ),
            lambda: renew_calendar_token(self.database_file),
        )

        self.mobile_panel = TokenAccessPanel(
            {
                "title": "Application mobile",
                "subtitle": "Révision sur le téléphone, même hors ligne. Un scan "
                "du QR code suffit : adresse, jeton et certificat en une fois. Les "
                "réponses rejoignent la progression d'ici au retour du réseau.",
                "qr": "Connecter un téléphone",
                "placeholder": "Aucun jeton créé",
                "create": "Créer le jeton",
                "renew": "Renouveler le jeton",
                "icon": "lock",
                "tooltip": "Un nouveau jeton désactive l'ancien",
                "confirm": "Le jeton actuel cessera de fonctionner : l'application "
                "mobile devra utiliser le nouveau. Continuer ?",
                "created": "Jeton créé : scannez le QR code avec l'application.",
                "copied": "Jeton copié.",
                "failed": "Le jeton n'a pas pu être créé.",
            },
            lambda: get_mobile_token(self.database_file),
            lambda: renew_mobile_token(self.database_file),
            f"{WEB_BASE_URL}{API_PREFIX}",
            lambda pToken: build_connection_png(
                f"{WEB_BASE_URL}{API_PREFIX}", pToken, get_certificate_fingerprint()
            ),
        )

    def set_actions_enabled(self, pEnabled):
        """Bloque le changement de thème et la réinitialisation pendant une recherche.

        Les deux reconstruisent les pages, ce qui interromprait la recherche.
        """
        for vButton in self.theme_buttons.buttons():
            vButton.setEnabled(pEnabled)

        self.data_panel.set_actions_enabled(pEnabled)
