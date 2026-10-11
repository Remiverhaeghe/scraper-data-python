"""Page des paramètres : apparence, règles, planification, notifications, sources"""

import smtplib
from datetime import datetime

from PySide6.QtCore import Qt, Signal
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
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS, THEME_CHOICES, is_dark_theme
from gui.widgets import (
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
)
from job.notification import build_test_email
from job.schedule import (
    SCHEDULE_INTERVALS,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    load_schedule,
    save_notification_email,
    save_schedule_options,
)
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.registry import SOURCES
from storage.maintenance import reset_database
from utils.logger import get_logger
from utils.mailer import EMAIL_SETTINGS, get_missing_email_settings, send_email

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
    data_reset = Signal(str)

    def __init__(self, pDatabaseFile):
        """Construit les cartes de la page."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout,
            "Paramètres",
            "Apparence, règles de calcul, planification, notifications et sources",
            pIcon="settings",
        )

        # Deux colonnes indépendantes : dans une grille, une carte courte prendrait
        # la hauteur de sa voisine et s'étirerait.
        vColumns = QHBoxLayout()
        vColumns.setSpacing(18)

        for vCards in (
            (
                self.create_appearance_card(),
                self.create_rules_card(),
                self.create_schedule_card(),
            ),
            (
                self.create_notification_card(),
                self.create_sources_card(),
                self.create_reset_card(),
            ),
        ):
            vColumn = QVBoxLayout()
            vColumn.setSpacing(18)

            for vCard in vCards:
                vColumn.addWidget(vCard)

            vColumn.addStretch()
            vColumns.addLayout(vColumn, 1)

        vLayout.addLayout(vColumns, 1)

        self.refresh_schedule()

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
            "Partagées avec le tableau de bord web. Le net des offres est recalculé.",
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
            # Changer le net ou l'impôt recalcule le salaire net de toutes les offres en
            # base : le nombre d'offres concernées est indiqué dans le message.
            _, vRecomputed = save_settings(self.database_file, vValues)

        except ValueError as vException:
            self.rules_message.setText(str(vException))

        except Exception:
            logger.exception("Échec de l'enregistrement des règles de calcul")

            self.rules_message.setText("Les règles n'ont pas pu être enregistrées.")

        else:
            self.rules_message.setText(
                f"Règles enregistrées, salaire net recalculé pour {vRecomputed} "
                "offre(s)."
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
            "Lancée par le planificateur (python -m scheduler). La recherche se "
            "choisit depuis la page Recherche.",
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
        vLayout.addLayout(vOptions)
        vLayout.addWidget(self.schedule_runs_label)
        vLayout.addLayout(vActions)

        return vCard

    def create_notification_card(self):
        """Construit l'adresse des notifications et l'état du compte Gmail."""
        vCard, vLayout = create_card(
            "Notifications e-mail",
            "Les nouvelles offres de la recherche planifiée, envoyées par Gmail",
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

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.test_email_button)
        vActions.addStretch()

        vLayout.addLayout(vStateRow)
        vLayout.addWidget(self.email_edit)
        vLayout.addLayout(vActions)
        vLayout.addWidget(self.email_message)

        return vCard

    def refresh_schedule(self):
        """Relit la planification et l'adresse de notification en base."""
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
            self.schedule_check.setChecked(vSchedule["enabled"])
            self.interval_combo.setCurrentIndex(
                self.interval_combo.findData(vSchedule["interval_hours"])
            )
            self.schedule_runs_label.setText(
                describe_schedule_runs(vSchedule, datetime.now())
            )
            self.email_edit.setText(vSchedule["email"] or "")

    def save_schedule(self):
        """Enregistre l'activation et la fréquence de la recherche planifiée."""
        try:
            vErrors = save_schedule_options(
                self.database_file,
                self.schedule_check.isChecked(),
                self.interval_combo.currentData(),
            )

        except Exception:
            logger.exception("Échec de l'enregistrement de la planification")

            vErrors = ["La planification n'a pas pu être enregistrée."]

        if not vErrors:
            self.refresh_schedule()

        self.schedule_message.setText(" ".join(vErrors) or "Planification enregistrée.")

    def save_email(self):
        """Enregistre l'adresse de destination des notifications."""
        try:
            vErrors = save_notification_email(
                self.database_file, self.email_edit.text()
            )

        except Exception:
            logger.exception("Échec de l'enregistrement de l'adresse de notification")

            vErrors = ["L'adresse n'a pas pu être enregistrée."]

        if vErrors:
            vMessage = " ".join(vErrors)
        elif self.email_edit.text().strip():
            vMessage = "Adresse enregistrée."
        else:
            vMessage = "Notifications désactivées."

        self.email_message.setText(vMessage)

    def send_test_email(self):
        """Envoie un e-mail de test à l'adresse saisie."""
        vEmail = self.email_edit.text().strip()

        if not vEmail:
            self.email_message.setText("Saisissez d'abord une adresse.")
            return

        # L'envoi est court mais bloquant : le curseur signale l'attente.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            send_email(vEmail, *build_test_email())

        except (OSError, smtplib.SMTPException, ValueError) as vException:
            logger.error("Échec de l'e-mail de test : %s", vException)

            self.email_message.setText(f"Échec de l'envoi : {vException}")

        else:
            self.email_message.setText("E-mail de test envoyé.")

        finally:
            QApplication.restoreOverrideCursor()

    def create_reset_card(self):
        """Construit la réinitialisation des données, précédée d'une sauvegarde."""
        vCard, vLayout = create_card(
            "Réinitialisation",
            "Efface les offres, candidatures, relances, historique, réglages et "
            "recherches enregistrées. "
            "Une sauvegarde de la base est faite juste avant.",
        )

        self.reset_button = create_button(
            "Réinitialiser les données",
            "circle-alert",
            "dangerButton",
            COLORS["danger"],
        )
        self.reset_button.clicked.connect(self.confirm_reset)

        self.reset_message = QLabel()
        self.reset_message.setObjectName("cardSubtitle")
        self.reset_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.reset_button)
        vActions.addWidget(self.reset_message, 1)

        vLayout.addLayout(vActions)

        return vCard

    def confirm_reset(self):
        """Demande confirmation, puis réinitialise les données."""
        vDialog = QMessageBox(self)
        vDialog.setIcon(QMessageBox.Icon.Warning)
        vDialog.setWindowTitle("Réinitialiser les données")
        vDialog.setText("Toutes les données de l'application vont être effacées.")
        vDialog.setInformativeText(
            "Offres, candidatures, relances, historique, réglages, recherches "
            "enregistrées et planifiée, adresse de notification. Une sauvegarde "
            "de la base est "
            "faite avant, dans data/backups. Continuer ?"
        )

        vConfirmButton = vDialog.addButton(
            "Réinitialiser", QMessageBox.ButtonRole.DestructiveRole
        )
        vCancelButton = vDialog.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)

        # Par sécurité, Entrée annule : il faut cliquer sur Réinitialiser.
        vDialog.setDefaultButton(vCancelButton)
        vDialog.exec()

        if vDialog.clickedButton() is vConfirmButton:
            self.reset_data()

    def reset_data(self):
        """Sauvegarde puis efface les données ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = reset_database(self.database_file, datetime.now())

        except Exception:
            logger.exception("Échec de la réinitialisation des données")

            self.reset_message.setText(
                "La réinitialisation a échoué, aucune donnée n'a été effacée "
                "si la sauvegarde n'a pas pu être faite. Voir les journaux."
            )

        else:
            # Les pages sont reconstruites : le message est affiché sur la nouvelle.
            self.data_reset.emit(
                f"Données réinitialisées. Sauvegarde : {vBackupFile.name}"
            )

    def set_actions_enabled(self, pEnabled):
        """Bloque le changement de thème et la réinitialisation pendant une recherche.

        Les deux reconstruisent les pages, ce qui interromprait la recherche.
        """
        for vButton in self.theme_buttons.buttons():
            vButton.setEnabled(pEnabled)

        self.reset_button.setEnabled(pEnabled)
