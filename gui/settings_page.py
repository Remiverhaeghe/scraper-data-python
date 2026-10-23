"""Page des paramètres : apparence, règles, planification, notifications, sources"""

import smtplib
from datetime import datetime

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.token_access_panel import TokenAccessPanel
from gui.company_pages_panel import CompanyPagesPanel
from gui.data_panel import DataPanel
from gui.theme import COLORS, THEME_CHOICES, THEME_SETTING
from gui.widgets import (
    FlowLayout,
    align_spin_box,
    clear_layout,
    create_button,
    create_card,
    create_fold_button,
    create_icon_label,
    create_page_header,
    create_scroll_content,
    show_message,
)
from config import WEB_BASE_URL
from job.calendar import (
    build_subscription_url,
    get_calendar_token,
    renew_calendar_token,
)
from job.companies import load_company_rules, save_company_rules
from job.mobile_sync import (
    API_PREFIX,
    build_connection_png,
    get_certificate_fingerprint,
    get_mobile_token,
    renew_mobile_token,
)
from job.notification import build_test_email
from job.schedule import (
    MIN_SCORE_CHOICES,
    SCHEDULE_INTERVALS,
    clear_scheduled_search,
    describe_extra_searches,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    format_min_score,
    load_schedule,
    save_extra_searches,
    save_min_score,
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.registry import SOURCES
from storage.saved_searches import get_saved_searches
from utils.logger import get_logger
from utils.mailer import EMAIL_SETTINGS, get_missing_email_settings, send_email

logger = get_logger(__name__)

THEME_ICONS = {"system": "monitor", "light": "sun", "dark": "moon"}

# Hauteur des listes d'entreprises : quelques lignes, la liste défile au-delà.
COMPANY_EDIT_HEIGHT = 76

# En dessous de cette largeur de page, les cartes passent sur une colonne.
SINGLE_COLUMN_WIDTH = 1100


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
    data_reset = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les cartes de la page."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.saved_searches = {}

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

        # Deux colonnes indépendantes : dans une grille, une carte courte prendrait
        # la hauteur de sa voisine et s'étirerait.
        # Deux colonnes sur un écran large, une seule dans une fenêtre réduite :
        # les cartes sont redistribuées au redimensionnement (resizeEvent).
        self.card_groups = (
            [
                self.create_appearance_card(),
                self.create_rules_card(),
                self.create_schedule_card(),
                self.calendar_panel,
                self.mobile_panel,
            ],
            [
                self.create_notification_card(),
                self.create_sources_card(),
                self.company_pages_panel,
                self.create_companies_card(),
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

        self.refresh_schedule()
        self.calendar_panel.refresh()
        self.mobile_panel.refresh()
        self.company_pages_panel.refresh()

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

            vColumn.addStretch()

    def resizeEvent(self, pEvent):  # pylint: disable=invalid-name
        """Passe sur une colonne quand la page devient trop étroite pour deux."""
        super().resizeEvent(pEvent)

        self.arrange_cards(self.width() < SINGLE_COLUMN_WIDTH)

    def create_appearance_card(self):
        """Construit le choix du thème, mémorisé pour les prochains lancements."""
        vCard, vLayout = create_card("Apparence", "Thème de l'interface")

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

        return vCard

    def create_rules_card(self):
        """Construit le formulaire des règles de calcul, enregistrées en base."""
        vCard, vLayout = create_card(
            "Règles de calcul",
            "Partagées avec le tableau de bord web. Le net des offres est recalculé.",
        )

        vSettings = load_settings(self.database_file)

        self.setting_spins = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(10)

        for vRow, (vKey, vDefinition) in enumerate(SETTING_DEFINITIONS.items()):
            vSpin = align_spin_box(QDoubleSpinBox())
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
            # Changer le net ou l'impôt recalcule le salaire net de toutes les offres en
            # base : le nombre d'offres concernées est indiqué dans le message.
            _, vRecomputed = save_settings(self.database_file, vValues)

        except ValueError as vException:
            show_message(self.rules_message, str(vException), "warning")

        except Exception:
            logger.exception("Échec de l'enregistrement des règles de calcul")

            show_message(
                self.rules_message,
                "Les règles n'ont pas pu être enregistrées.",
                "danger",
            )

        else:
            show_message(
                self.rules_message,
                (
                    f"Règles enregistrées, salaire net recalculé pour {vRecomputed} "
                    "offre(s)."
                    if vRecomputed
                    else "Règles enregistrées."
                ),
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

    def create_schedule_card(self):
        """Construit l'activation, la fréquence et l'état de la recherche planifiée."""
        vCard, vLayout = create_card(
            "Recherche planifiée",
            "Lancée par le planificateur (python -m scheduler), parmi les "
            "recherches enregistrées de la page Recherche.",
        )

        self.schedule_search_label = QLabel()
        self.schedule_search_label.setObjectName("activityTitle")
        self.schedule_search_label.setWordWrap(True)

        self.schedule_sources_label = QLabel()
        self.schedule_sources_label.setObjectName("cardSubtitle")
        self.schedule_sources_label.setWordWrap(True)

        vSearchTexts = QVBoxLayout()
        vSearchTexts.setSpacing(2)
        vSearchTexts.addWidget(self.schedule_search_label)
        vSearchTexts.addWidget(self.schedule_sources_label)

        vSearch = QHBoxLayout()
        vSearch.setSpacing(10)
        vSearch.addWidget(
            create_icon_label("search", COLORS["primary"], 18),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        vSearch.addLayout(vSearchTexts, 1)

        self.remove_schedule_button = create_button(
            "", "trash-2", "iconButton", COLORS["danger"]
        )
        self.remove_schedule_button.setToolTip(
            "Retirer la recherche planifiée et désactiver la planification"
        )
        self.remove_schedule_button.clicked.connect(self.remove_scheduled_search)
        vSearch.addWidget(self.remove_schedule_button, 0, Qt.AlignmentFlag.AlignTop)

        # Recopie les critères et les sources : modifier ensuite la recherche
        # enregistrée ne change pas la recherche planifiée.
        self.schedule_search_combo = QComboBox()
        self.schedule_search_combo.setToolTip(
            "Remplace la recherche planifiée à l'enregistrement"
        )

        self.extra_searches_title = QLabel("Lancer aussi ces recherches enregistrées")
        self.extra_searches_title.setObjectName("cardSubtitle")

        self.extra_searches_layout = FlowLayout(12)
        self.extra_search_checks = {}

        self.schedule_extra_label = QLabel()
        self.schedule_extra_label.setObjectName("cardSubtitle")
        self.schedule_extra_label.setWordWrap(True)
        vSearchTexts.addWidget(self.schedule_extra_label)

        self.schedule_check = QCheckBox("Activer la recherche planifiée")

        self.interval_combo = QComboBox()

        for vHours in SCHEDULE_INTERVALS:
            self.interval_combo.addItem(format_interval(vHours), vHours)

        vOptions = QHBoxLayout()
        vOptions.setSpacing(12)
        vOptions.addWidget(self.schedule_check)
        vOptions.addStretch()
        vOptions.addWidget(self.interval_combo)

        self.schedule_runs_label = QLabel()
        self.schedule_runs_label.setObjectName("cardSubtitle")
        self.schedule_runs_label.setWordWrap(True)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save_schedule)

        self.schedule_message = QLabel()
        self.schedule_message.setObjectName("cardSubtitle")
        self.schedule_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.schedule_message, 1)

        vLayout.addLayout(vSearch)
        vLayout.addWidget(self.schedule_search_combo)
        vLayout.addWidget(self.extra_searches_title)
        vLayout.addLayout(self.extra_searches_layout)
        vLayout.addLayout(vOptions)
        vLayout.addWidget(self.schedule_runs_label)
        vLayout.addLayout(vActions)

        return vCard

    def create_notification_card(self):
        """Construit l'adresse des notifications et l'état du compte Gmail."""
        vCard, vLayout = create_card(
            "Notifications e-mail",
            "Nouvelles offres de la recherche planifiée et relances du jour, par Gmail",
        )

        # Seuls les noms des variables manquantes sont affichés, jamais leurs valeurs.
        vMissing = get_missing_email_settings()

        if vMissing:
            vIcon, vColor = "circle-alert", COLORS["warning"]
            vText = "À renseigner dans .env : " + ", ".join(vMissing)
        else:
            vIcon, vColor = "circle-check", COLORS["success"]
            vText = f"Compte Gmail configuré dans .env ({', '.join(EMAIL_SETTINGS)})"

        vState = QLabel(vText)
        vState.setObjectName("cardSubtitle")
        vState.setWordWrap(True)

        vStateRow = QHBoxLayout()
        vStateRow.setSpacing(10)
        vStateRow.addWidget(create_icon_label(vIcon, vColor, 18))
        vStateRow.addWidget(vState, 1)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(
            "Adresse de destination, ex. prenom@gmail.com"
        )

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save_email)

        self.test_email_button = create_button(
            "Envoyer un e-mail de test", "send", pIconColor=COLORS["primary"]
        )
        self.test_email_button.setEnabled(not vMissing)
        self.test_email_button.clicked.connect(self.send_test_email)

        self.email_message = QLabel()
        self.email_message.setObjectName("cardSubtitle")
        self.email_message.setWordWrap(True)

        # Le score compare l'offre aux compétences de la page Profil.
        self.min_score_combo = QComboBox()
        self.min_score_combo.setToolTip(
            "Seules les nouvelles offres assez proches du profil sont envoyées"
        )

        for vScore in MIN_SCORE_CHOICES:
            self.min_score_combo.addItem(format_min_score(vScore), vScore)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.test_email_button)
        vActions.addStretch()

        vLayout.addLayout(vStateRow)
        vLayout.addWidget(self.email_edit)
        vLayout.addWidget(self.min_score_combo)
        vLayout.addLayout(vActions)
        vLayout.addWidget(self.email_message)

        return vCard

    def refresh(self):
        """Relit la planification et les entreprises à l'affichage de la page."""
        self.refresh_schedule()
        self.refresh_companies()

    def create_companies_card(self):
        """Construit les listes d'entreprises à exclure et à privilégier."""
        vCard, vLayout = create_card(
            "Entreprises",
            "Une entreprise par ligne. Les exclues sont masquées de la liste des "
            "offres, les privilégiées marquées d'une étoile.",
        )

        self.company_edits = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)

        # Exclues en rouge, privilégiées en vert : le rôle de chaque liste se voit.
        for vColumn, (vKind, vLabel, vIcon, vTone) in enumerate(
            (
                ("excluded", "À exclure", "circle-alert", "danger"),
                ("preferred", "À privilégier", "circle-check", "success"),
            )
        ):
            vTitle = QLabel(vLabel)
            vTitle.setStyleSheet(f"color: {COLORS[vTone]}; font-weight: 600;")

            vTitleRow = QHBoxLayout()
            vTitleRow.setSpacing(6)
            vTitleRow.addWidget(create_icon_label(vIcon, COLORS[vTone], 16))
            vTitleRow.addWidget(vTitle, 1)

            vEdit = QPlainTextEdit()
            vEdit.setObjectName(f"{vKind}Companies")
            vEdit.setPlaceholderText("Ex. Acme\nGlobex")
            vEdit.setFixedHeight(COMPANY_EDIT_HEIGHT)

            self.company_edits[vKind] = vEdit
            vGrid.addLayout(vTitleRow, 0, vColumn)
            vGrid.addWidget(vEdit, 1, vColumn)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save_companies)

        self.companies_message = QLabel()
        self.companies_message.setObjectName("cardSubtitle")
        self.companies_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.companies_message, 1)

        vLayout.addLayout(vGrid)
        vLayout.addLayout(vActions)

        self.refresh_companies()

        return vCard

    def refresh_companies(self):
        """Relit les listes d'entreprises en base."""
        try:
            vRules = load_company_rules(self.database_file)

        except Exception:
            logger.exception("Impossible de lire les listes d'entreprises")

            show_message(
                self.companies_message, "Les listes n'ont pas pu être lues.", "danger"
            )

        else:
            for vKind, vEdit in self.company_edits.items():
                vEdit.setPlainText("\n".join(vRules[vKind]))

    def save_companies(self):
        """Enregistre les deux listes d'entreprises."""
        try:
            vRules = save_company_rules(
                self.database_file,
                self.company_edits["excluded"].toPlainText(),
                self.company_edits["preferred"].toPlainText(),
            )

        except ValueError as vException:
            vMessage, vTone = str(vException), "warning"

        except Exception:
            logger.exception("Échec de l'enregistrement des listes d'entreprises")

            vMessage, vTone = "Les listes n'ont pas pu être enregistrées.", "danger"

        else:
            self.refresh_companies()

            vMessage, vTone = (
                f"{len(vRules['excluded'])} entreprise(s) exclue(s), "
                f"{len(vRules['preferred'])} privilégiée(s).",
                "success",
            )

        show_message(self.companies_message, vMessage, vTone)

    def refresh_saved_searches(self):
        """Propose les recherches enregistrées pour remplacer la recherche planifiée."""
        try:
            self.saved_searches = {
                vSearch["name"]: vSearch
                for vSearch in get_saved_searches(self.database_file)
            }

        except Exception:
            logger.exception("Impossible de lire les recherches enregistrées")

            self.saved_searches = {}

        self.schedule_search_combo.clear()
        self.schedule_search_combo.addItem(
            (
                "Garder la recherche actuelle"
                if self.saved_searches
                else "Aucune recherche enregistrée dans la page Recherche"
            ),
            None,
        )

        for vName in self.saved_searches:
            self.schedule_search_combo.addItem(f"Planifier « {vName} »", vName)

        clear_layout(self.extra_searches_layout)

        self.extra_search_checks = {
            vName: QCheckBox(vName) for vName in self.saved_searches
        }

        for vCheck in self.extra_search_checks.values():
            self.extra_searches_layout.addWidget(vCheck)

        self.extra_searches_title.setVisible(bool(self.saved_searches))

    def refresh_schedule(self):
        """Relit la planification et l'adresse de notification en base."""
        self.refresh_saved_searches()

        try:
            vSchedule = load_schedule(self.database_file)

        except Exception:
            logger.exception("Impossible de charger la planification")

            self.schedule_runs_label.setText("La planification n'a pas pu être lue.")

        else:
            vSearch, vSources = describe_scheduled_search(vSchedule)

            self.schedule_search_label.setText(vSearch)
            self.schedule_sources_label.setText(vSources)
            self.schedule_sources_label.setVisible(bool(vSources))

            vExtra = describe_extra_searches(vSchedule)

            self.schedule_extra_label.setText(vExtra)
            self.schedule_extra_label.setVisible(bool(vExtra))

            for vName, vCheck in self.extra_search_checks.items():
                vCheck.setChecked(vName in vSchedule["extra_searches"])
            self.schedule_check.setChecked(vSchedule["enabled"])
            self.remove_schedule_button.setVisible(vSchedule["search"] is not None)
            self.interval_combo.setCurrentIndex(
                self.interval_combo.findData(vSchedule["interval_hours"])
            )
            self.schedule_runs_label.setText(
                describe_schedule_runs(vSchedule, datetime.now())
            )
            self.email_edit.setText(vSchedule["email"] or "")
            self.min_score_combo.setCurrentIndex(
                self.min_score_combo.findData(vSchedule["min_score"])
            )

    def save_schedule(self):
        """Enregistre l'activation et la fréquence de la recherche planifiée."""
        vName = self.schedule_search_combo.currentData()

        try:
            if vName is not None:
                vSearch = self.saved_searches[vName]

                save_scheduled_search(
                    self.database_file, vSearch["sources"], vSearch["criteria"]
                )

            vErrors = save_schedule_options(
                self.database_file,
                self.schedule_check.isChecked(),
                self.interval_combo.currentData(),
            )

            if not vErrors:
                save_extra_searches(
                    self.database_file,
                    [
                        vName
                        for vName, vCheck in self.extra_search_checks.items()
                        if vCheck.isChecked()
                    ],
                )

        except Exception:
            logger.exception("Échec de l'enregistrement de la planification")

            show_message(
                self.schedule_message,
                "La planification n'a pas pu être enregistrée.",
                "danger",
            )
            return

        if not vErrors:
            self.refresh_schedule()

        show_message(
            self.schedule_message,
            " ".join(vErrors) or "Planification enregistrée.",
            "warning" if vErrors else "success",
        )

    def remove_scheduled_search(self):
        """Retire la recherche planifiée, après confirmation."""
        if (
            QMessageBox.question(
                self,
                "Retirer la recherche planifiée",
                "La recherche planifiée sera retirée et la planification "
                "désactivée. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            clear_scheduled_search(self.database_file)

        except Exception:
            logger.exception("Échec du retrait de la recherche planifiée")

            show_message(
                self.schedule_message, "La recherche n'a pas pu être retirée.", "danger"
            )

        else:
            self.refresh_schedule()
            show_message(self.schedule_message, "Recherche planifiée retirée.")

    def save_email(self):
        """Enregistre l'adresse de destination des notifications."""
        try:
            vErrors = save_notification_email(
                self.database_file, self.email_edit.text()
            ) or save_min_score(self.database_file, self.min_score_combo.currentData())

        except Exception:
            logger.exception("Échec de l'enregistrement de l'adresse de notification")

            show_message(
                self.email_message, "L'adresse n'a pas pu être enregistrée.", "danger"
            )
            return

        if vErrors:
            show_message(self.email_message, " ".join(vErrors), "warning")
        elif self.email_edit.text().strip():
            show_message(self.email_message, "Adresse enregistrée.")
        else:
            show_message(self.email_message, "Notifications désactivées.", "warning")

    def send_test_email(self):
        """Envoie un e-mail de test à l'adresse saisie."""
        vEmail = self.email_edit.text().strip()

        if not vEmail:
            show_message(
                self.email_message, "Saisissez d'abord une adresse.", "warning"
            )
            return

        # L'envoi est court mais bloquant : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            send_email(vEmail, *build_test_email())

        except (OSError, smtplib.SMTPException, ValueError) as vException:
            logger.error("Échec de l'e-mail de test : %s", vException)

            show_message(
                self.email_message, f"Échec de l'envoi : {vException}", "danger"
            )

        else:
            show_message(self.email_message, "E-mail de test envoyé.")

        finally:
            QApplication.restoreOverrideCursor()

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
                "subtitle": "Révision sur le téléphone, même hors ligne : saisissez "
                "cette adresse et ce jeton dans l'application. Les réponses "
                "rejoignent la progression d'ici au retour du réseau.",
                "placeholder": "Aucun jeton créé",
                "create": "Créer le jeton",
                "renew": "Renouveler le jeton",
                "icon": "lock",
                "tooltip": "Un nouveau jeton désactive l'ancien",
                "confirm": "Le jeton actuel cessera de fonctionner : l'application "
                "mobile devra utiliser le nouveau. Continuer ?",
                "created": "Jeton créé : saisissez-le dans l'application.",
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
