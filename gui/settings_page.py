"""Page des paramètres : apparence, règles, planification, notifications, sources"""

import smtplib
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS, THEME_CHOICES, is_dark_theme
from gui.widgets import (
    align_spin_box,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
    create_scroll_content,
)
from config import WEB_HOST, WEB_PORT
from job.calendar import (
    build_subscription_url,
    get_calendar_token,
    renew_calendar_token,
)
from job.companies import load_company_rules, save_company_rules
from job.notification import build_test_email
from job.schedule import (
    MIN_SCORE_CHOICES,
    SCHEDULE_INTERVALS,
    clear_scheduled_search,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    format_min_score,
    load_schedule,
    save_min_score,
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from job.sources.registry import SOURCES
from storage.archive import export_archive, restore_archive
from storage.maintenance import reset_database
from storage.saved_searches import get_saved_searches
from utils.logger import get_logger
from utils.mailer import EMAIL_SETTINGS, get_missing_email_settings, send_email

logger = get_logger(__name__)

THEME_ICONS = {"light": "sun", "dark": "moon"}

# Adresse du tableau de bord : WEB_HOST vaut l'adresse Tailscale pour un accès
# depuis le téléphone, voir le README.
WEB_BASE_URL = f"http://{WEB_HOST}:{WEB_PORT}"


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
                self.create_calendar_card(),
            ),
            (
                self.create_notification_card(),
                self.create_sources_card(),
                self.create_companies_card(),
                self.create_archive_card(),
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
        self.refresh_calendar()

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

        for vColumn, (vKind, vLabel) in enumerate(
            (("excluded", "À exclure"), ("preferred", "À privilégier"))
        ):
            vTitle = QLabel(vLabel)
            vTitle.setObjectName("fieldLabel")

            vEdit = QPlainTextEdit()
            vEdit.setPlaceholderText("Ex. Acme\nGlobex")
            vEdit.setFixedHeight(110)

            self.company_edits[vKind] = vEdit
            vGrid.addWidget(vTitle, 0, vColumn)
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

            self.companies_message.setText("Les listes n'ont pas pu être lues.")

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
            vMessage = str(vException)

        except Exception:
            logger.exception("Échec de l'enregistrement des listes d'entreprises")

            vMessage = "Les listes n'ont pas pu être enregistrées."

        else:
            self.refresh_companies()

            vMessage = (
                f"{len(vRules['excluded'])} entreprise(s) exclue(s), "
                f"{len(vRules['preferred'])} privilégiée(s)."
            )

        self.companies_message.setText(vMessage)

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

        except Exception:
            logger.exception("Échec de l'enregistrement de la planification")

            vErrors = ["La planification n'a pas pu être enregistrée."]

        if not vErrors:
            self.refresh_schedule()

        self.schedule_message.setText(" ".join(vErrors) or "Planification enregistrée.")

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

            self.schedule_message.setText("La recherche n'a pas pu être retirée.")

        else:
            self.refresh_schedule()
            self.schedule_message.setText("Recherche planifiée retirée.")

    def save_email(self):
        """Enregistre l'adresse de destination des notifications."""
        try:
            vErrors = save_notification_email(
                self.database_file, self.email_edit.text()
            ) or save_min_score(self.database_file, self.min_score_combo.currentData())

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

    def create_calendar_card(self):
        """Construit l'adresse d'abonnement de l'agenda aux relances et entretiens."""
        vCard, vLayout = create_card(
            "Abonnement à l'agenda",
            "Relances et entretiens relus automatiquement par l'agenda du téléphone "
            "ou du PC, sur le réseau local ou par Tailscale.",
        )

        self.calendar_edit = QLineEdit()
        self.calendar_edit.setReadOnly(True)
        self.calendar_edit.setPlaceholderText("Aucune adresse créée")

        self.calendar_button = create_button(
            "Créer l'adresse", "calendar", pIconColor=COLORS["primary"]
        )
        self.calendar_button.setToolTip("Une nouvelle adresse désactive l'ancienne")
        self.calendar_button.clicked.connect(self.renew_calendar)

        self.copy_calendar_button = create_button(
            "Copier", "copy", pIconColor=COLORS["primary"]
        )
        self.copy_calendar_button.clicked.connect(self.copy_calendar)

        self.calendar_message = QLabel()
        self.calendar_message.setObjectName("cardSubtitle")
        self.calendar_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.calendar_button)
        vActions.addWidget(self.copy_calendar_button)
        vActions.addWidget(self.calendar_message, 1)

        vLayout.addWidget(self.calendar_edit)
        vLayout.addLayout(vActions)

        return vCard

    def refresh_calendar(self):
        """Affiche l'adresse d'abonnement enregistrée."""
        try:
            vUrl = build_subscription_url(
                WEB_BASE_URL, get_calendar_token(self.database_file)
            )

        except Exception:
            logger.exception("Impossible de lire l'adresse d'abonnement à l'agenda")

            vUrl = None

        self.calendar_edit.setText(vUrl or "")
        self.calendar_button.setText(
            "Renouveler l'adresse" if vUrl else "Créer l'adresse"
        )
        self.copy_calendar_button.setEnabled(bool(vUrl))

    def renew_calendar(self):
        """Crée une adresse d'abonnement ; une adresse existante est d'abord confirmée."""
        if self.calendar_edit.text() and (
            QMessageBox.question(
                self,
                "Renouveler l'adresse",
                "L'adresse actuelle cessera de fonctionner : les agendas abonnés "
                "devront utiliser la nouvelle. Continuer ?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            renew_calendar_token(self.database_file)

        except Exception:
            logger.exception("Échec de la création de l'adresse d'abonnement")

            self.calendar_message.setText("L'adresse n'a pas pu être créée.")

        else:
            self.refresh_calendar()
            self.calendar_message.setText(
                "Adresse créée : ajoutez-la dans l'agenda comme agenda par URL."
            )

    def copy_calendar(self):
        """Copie l'adresse d'abonnement dans le presse-papiers."""
        QApplication.clipboard().setText(self.calendar_edit.text())

        self.calendar_message.setText("Adresse copiée.")

    def create_archive_card(self):
        """Construit l'export et la restauration de la sauvegarde complète."""
        vCard, vLayout = create_card(
            "Sauvegarde complète",
            "Base et pièces jointes dans une archive .zip, pour changer de PC sans "
            "rien perdre. La restauration sauvegarde d'abord les données actuelles.",
        )

        self.export_archive_button = create_button(
            "Exporter…", "download", pIconColor=COLORS["primary"]
        )
        self.export_archive_button.clicked.connect(self.choose_archive_target)

        self.restore_archive_button = create_button(
            "Restaurer…", "upload", "dangerButton", COLORS["danger"]
        )
        self.restore_archive_button.clicked.connect(self.choose_archive_source)

        self.archive_message = QLabel()
        self.archive_message.setObjectName("cardSubtitle")
        self.archive_message.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(self.export_archive_button)
        vActions.addWidget(self.restore_archive_button)
        vActions.addWidget(self.archive_message, 1)

        vLayout.addLayout(vActions)

        return vCard

    def choose_archive_target(self):
        """Demande où enregistrer la sauvegarde complète puis l'écrit."""
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la sauvegarde complète",
            str(Path.home() / f"jobboard-{datetime.now():%Y%m%d}.zip"),
            "Archive (*.zip)",
        )

        if vPath:
            self.export_archive(vPath)

    def export_archive(self, pPath):
        """Écrit la base et les pièces jointes dans l'archive choisie."""
        try:
            vCount = export_archive(self.database_file, pPath)

        except Exception:
            logger.exception("Échec de l'export de la sauvegarde complète")

            self.archive_message.setText("L'export a échoué. Voir les journaux.")

        else:
            self.archive_message.setText(
                f"Sauvegarde exportée : base et {vCount} pièce(s) jointe(s)."
            )

    def choose_archive_source(self):
        """Demande l'archive à restaurer, puis une confirmation."""
        vPath, _ = QFileDialog.getOpenFileName(
            self,
            "Restaurer une sauvegarde complète",
            str(Path.home()),
            "Archive (*.zip)",
        )

        # Par sécurité, Entrée annule : il faut cliquer sur Oui.
        if vPath and (
            QMessageBox.warning(
                self,
                "Restaurer la sauvegarde",
                "Les données actuelles seront remplacées par celles de l'archive. "
                "Elles sont d'abord sauvegardées dans data/backups. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.restore_archive(vPath)

    def restore_archive(self, pPath):
        """Restaure l'archive ; les pages sont ensuite reconstruites."""
        try:
            vBackupFile = restore_archive(self.database_file, pPath, datetime.now())

        except ValueError as vException:
            logger.warning("Restauration refusée : %s", vException)

            self.archive_message.setText(str(vException))

        except Exception:
            logger.exception("Échec de la restauration de la sauvegarde complète")

            self.archive_message.setText("La restauration a échoué. Voir les journaux.")

        else:
            self.data_reset.emit(
                f"Sauvegarde restaurée. Anciennes données : {vBackupFile.name}"
            )

    def create_reset_card(self):
        """Construit la réinitialisation des données, précédée d'une sauvegarde."""
        vCard, vLayout = create_card(
            "Réinitialisation",
            "Efface les offres, candidatures, relances, historique, réglages et "
            "recherches enregistrées. Les questions de révision sont conservées. "
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
            "enregistrées et planifiée, adresse de notification, progression de "
            "révision. Les questions de révision importées sont conservées. Une "
            "sauvegarde de la base est faite avant, dans data/backups. Continuer ?"
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
        self.restore_archive_button.setEnabled(pEnabled)
