"""Fenêtre principale : menu latéral et pages de l'application"""

import threading
import time
from datetime import date, datetime

import shiboken6
from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import CONTACT_URL, LICENSE_NAME, REPOSITORY_URL, TAGLINE
from gui.branding import create_logo_icon
from gui.dialogs import show_legal_notice, show_license
from gui.applications_page import ApplicationsPage
from gui.aptitude_page import AptitudePage
from gui.certifications_page import CertificationsPage
from gui.challenges_page import ChallengesPage
from gui.circuit_page import CircuitPage
from gui.devops_page import DevopsPage
from gui.git_page import GitPage
from gui.history_page import HistoryPage
from gui.ladder_page import LadderPage
from gui.home_page import HomePage
from gui.logs_page import LogsPage
from gui.market_page import MarketPage
from gui.icons import get_icon
from gui.offers_page import OffersPage
from gui.profile_page import ProfilePage
from gui.progress_page import ProgressPage
from gui.progress_widgets import (
    TOAST_GAP_MS,
    CelebrationOverlay,
    SidebarProgress,
    get_game_mode,
    show_xp_gain,
)
from gui.quality_page import QualityPage
from gui.quiz_page import QuizPage
from gui.skills_page import SkillsPage
from gui.search_page import SearchPage
from gui.settings_page import SettingsPage
from gui.sql_page import SqlPage
from gui.troubleshooting_page import TroubleshootingPage
from gui.theme import COLORS
from gui.widgets import show_message
from job.education import refresh_education_levels_safely
from job.followed_availability import count_alerts
from job.progress import build_progress, get_total_xp
from job.quiz import DEFAULT_MODE
from job.quiz_generation import prepare_quiz_caches
from job.schedule import save_scheduled_search
from job.skill_cache import refresh_detected_skills_safely
from job.statistics import warm_up_scores
from storage.backup import run_due_backup
from storage.database import get_database_version
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, une page est signalée dans les journaux pour en chercher la cause.
SLOW_PAGE_SECONDS = 1.0

# Relecture des points : un gain s'affiche peu après l'action, sans que les pages
# aient à le signaler. Le total se lit en quelques millisecondes.
PROGRESS_CHECK_MS = 1500

SCORE_WARM_UP_DELAY_MS = 15000

# Liens internes du pied de menu, ouverts dans l'application
LEGAL_LINK = "#mentions-legales"
LICENSE_LINK = "#licence"

# Clés de navigation qui ouvrent la page des offres avec des filtres prédéfinis
# Distincts des noms de page : « applications » ouvre la page Candidatures.
OFFER_PRESETS = ("offers", "new_offers", "applied_offers", "follow_ups")

# Pages dont le calcul, coûteux, ne dépend que de la base et du jour : elles ne se
# recalculent pas à chaque passage si rien n'a changé. Journaux et Git lisent des
# fichiers hors base et restent recalculés à chaque fois.
DATA_ONLY_PAGES = (
    "offers",
    "quiz",
    "skills",
    "certifications",
    "market",
    "challenges",
    "aptitude",
    "troubleshooting",
    "ladder",
    "sql",
    "circuit",
    "devops",
    "quality",
)


class MainWindow(QMainWindow):
    """Affiche le menu latéral et la page sélectionnée."""

    # Thème choisi dans les paramètres : light ou dark
    theme_requested = Signal(str)
    text_scale_requested = Signal(int)

    def __init__(self, pDatabaseFile, pTitle):
        """Construit la fenêtre et son contenu."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.title = pTitle

        # Créés par create_sidebar, appelée à chaque construction du contenu
        self.status_bar = None
        self.status_dot = None
        self.status_label = None
        self.progress_box = None

        self.setWindowTitle(pTitle)
        # En dessous, les cartes se chevauchent. Sur un petit écran ou un téléphone,
        # le tableau de bord web s'adapte à la largeur disponible.
        self.setMinimumSize(1180, 760)

        # Dernière progression vue : un écart déclenche « +XP » et célébrations.
        self.last_progress = None
        self.last_xp = None
        self.progress_failed = False

        self.build_content()

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.check_progress)
        self.progress_timer.start(PROGRESS_CHECK_MS)
        QTimer.singleShot(0, self.check_progress)

        # Offres récentes notées d'avance, une fois la fenêtre ouverte et les
        # tâches du démarrage passées : Historique et Offres s'ouvrent ensuite vite.
        QTimer.singleShot(
            SCORE_WARM_UP_DELAY_MS,
            lambda: threading.Thread(
                target=warm_up_scores, args=(pDatabaseFile,), daemon=True
            ).start(),
        )

        # Les comptes d'offres par thème sont longs à calculer : faits d'avance,
        # la page Révision s'ouvre aussitôt. Sans attente ni effet sur l'interface.
        threading.Thread(
            target=prepare_quiz_caches, args=(pDatabaseFile,), daemon=True
        ).start()

        # Compétences des nouvelles offres repérées une fois pour toutes : la
        # page Offres les lit au lieu de les chercher à chaque affichage.
        threading.Thread(
            target=refresh_detected_skills_safely, args=(pDatabaseFile,), daemon=True
        ).start()
        threading.Thread(
            target=refresh_education_levels_safely, args=(pDatabaseFile,), daemon=True
        ).start()

        # Une sauvegarde par jour au plus, sans attendre qu'elle soit finie.
        threading.Thread(
            target=run_due_backup, args=(pDatabaseFile, datetime.now()), daemon=True
        ).start()

    def build_content(self):
        """Construit le menu latéral et les pages.

        Appelée de nouveau après un changement de thème : les icônes et les
        cartes colorées sont dessinées à la construction.
        """
        vDatabaseFile = self.database_file
        self.page_labels = {}

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setIconSize(QSize(20, 20))

        self.pages = QStackedWidget()
        self.page_rows = {}
        self.page_keys = {}
        self.refreshed_versions = {}

        self.home_page = HomePage(vDatabaseFile)
        self.search_page = SearchPage(pDatabaseFile=vDatabaseFile)
        self.offers_page = OffersPage(vDatabaseFile)
        self.applications_page = ApplicationsPage(vDatabaseFile)
        self.quiz_page = QuizPage(vDatabaseFile)
        self.skills_page = SkillsPage(vDatabaseFile)

        # L'ordre d'ajout fixe l'ordre du menu ; la clé sert à navigate().
        self.add_page("home", "Accueil", "house", self.home_page)
        self.progress_page = ProgressPage(vDatabaseFile)
        self.add_page("progress", "Progression", "award", self.progress_page)
        self.add_page("search", "Recherche", "search", self.search_page)
        self.add_page("offers", "Offres", "briefcase", self.offers_page)
        self.add_page("applications", "Candidatures", "send", self.applications_page)
        self.add_page("profile", "Profil", "user", ProfilePage(vDatabaseFile))
        self.add_page("quiz", "Révision", "graduation-cap", self.quiz_page)
        self.add_page("skills", "Compétences", "target", self.skills_page)
        self.add_page(
            "certifications",
            "Certifications",
            "shield",
            CertificationsPage(vDatabaseFile),
        )
        self.market_page = MarketPage(vDatabaseFile)
        self.market_page.exam_requested.connect(self.start_skills_exam)
        self.add_page("market", "Mon marché", "banknote", self.market_page)
        self.add_page("challenges", "Défis", "trophy", ChallengesPage(vDatabaseFile))
        self.add_page(
            "aptitude",
            "Tests de recrutement",
            "timer",
            AptitudePage(vDatabaseFile),
        )
        self.add_page(
            "troubleshooting",
            "Pannes à résoudre",
            "wrench",
            TroubleshootingPage(vDatabaseFile),
        )
        self.add_page("ladder", "Automate", "cpu", LadderPage(vDatabaseFile))
        self.add_page("git", "Git", "git-branch", GitPage(vDatabaseFile))
        self.add_page("sql", "SQL", "database", SqlPage(vDatabaseFile))
        self.add_page("devops", "Maven et Docker", "server", DevopsPage(vDatabaseFile))
        self.add_page(
            "circuit", "Schémas électriques", "zap", CircuitPage(vDatabaseFile)
        )
        self.add_page("history", "Historique", "history", HistoryPage(vDatabaseFile))
        self.add_page("quality", "Qualité", "list-checks", QualityPage(vDatabaseFile))
        self.add_page("logs", "Journaux", "terminal", LogsPage(vDatabaseFile))

        self.settings_page = SettingsPage(vDatabaseFile)
        self.add_page("settings", "Paramètres", "settings", self.settings_page)

        # Les pages ne se connaissent pas : elles émettent des signaux et la fenêtre
        # décide de la suite. Pour suivre l'effet d'un clic, partir de ces connexions.
        self.settings_page.theme_requested.connect(self.theme_requested)
        self.settings_page.text_scale_requested.connect(self.text_scale_requested)
        self.settings_page.data_reset.connect(self.show_reset_result)
        self.settings_page.game_mode_changed.connect(self.check_progress)

        self.home_page.navigation_requested.connect(self.navigate)
        self.home_page.offer_requested.connect(self.show_search_results)
        self.applications_page.offer_requested.connect(self.show_search_results)
        self.offers_page.detail_panel.exam_requested.connect(self.start_offer_exam)
        self.offers_page.detail_panel.missing_exam_requested.connect(
            self.start_missing_skills_exam
        )
        self.skills_page.revise_requested.connect(self.revise_theme)
        self.skills_page.generation_requested.connect(self.prepare_questions)
        self.search_page.show_offers_requested.connect(self.show_search_results)
        self.search_page.search_started.connect(self.on_search_started)
        self.search_page.search_ended.connect(self.on_search_ended)
        self.search_page.schedule_requested.connect(self.save_scheduled_search)

        vCentral = QWidget()

        vLayout = QHBoxLayout(vCentral)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(0)
        vLayout.addWidget(self.create_sidebar(self.title))
        vLayout.addWidget(self.pages, 1)

        self.setCentralWidget(vCentral)

        self.navigation.currentRowChanged.connect(self.show_page)
        self.navigation.setCurrentRow(0)

        self.add_shortcuts()

    def add_shortcuts(self):
        """Ajoute les raccourcis : Ctrl+1 à 9 pour les pages, Ctrl+F, Échap."""
        for vRow in range(min(9, self.navigation.count())):
            QShortcut(
                QKeySequence(f"Ctrl+{vRow + 1}"),
                self,
                lambda pRow=vRow: self.navigation.setCurrentRow(pRow),
            )

        QShortcut(QKeySequence.StandardKey.Find, self, self.search_offers)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.hide_offer_detail)

    def search_offers(self):
        """Ouvre les offres, le curseur dans le champ de recherche."""
        self.navigate("offers")
        self.offers_page.filters_bar.search_edit.setFocus()
        self.offers_page.filters_bar.search_edit.selectAll()

    def hide_offer_detail(self):
        """Masque la fiche de l'offre au profit du tableau, sur la page Offres."""
        if (
            self.pages.currentWidget() is self.offers_page
            and not self.offers_page.detail_panel.isHidden()
        ):
            self.offers_page.toggle_detail()

    def create_sidebar(self, pTitle):
        """Construit le menu latéral : marque, navigation et état."""
        vLogo = QLabel()
        vLogo.setPixmap(create_logo_icon().pixmap(44, 44))
        vLogo.setFixedSize(44, 44)

        vName = QLabel(pTitle)
        vName.setObjectName("brandName")

        vTagline = QLabel(TAGLINE)
        vTagline.setObjectName("brandTagline")
        vTagline.setWordWrap(True)

        vBrandTexts = QVBoxLayout()
        vBrandTexts.setSpacing(2)
        vBrandTexts.addWidget(vName)
        vBrandTexts.addWidget(vTagline)

        vBrand = QHBoxLayout()
        vBrand.setSpacing(12)
        vBrand.addWidget(vLogo)
        vBrand.addLayout(vBrandTexts, 1)

        vSeparator = QFrame()
        vSeparator.setObjectName("separator")

        self.progress_box = SidebarProgress()
        self.progress_box.clicked.connect(lambda: self.navigate("progress"))
        self.progress_box.setVisible(get_game_mode() != "off")

        if self.last_progress is not None:
            self.progress_box.set_progress(self.last_progress)

        self.status_dot = QLabel("●")

        self.status_label = QLabel()
        self.status_label.setObjectName("sidebarStatus")

        # Visible seulement pendant une recherche, pour la suivre depuis une autre page
        self.status_bar = QWidget()
        self.status_bar.setVisible(False)

        vStatus = QHBoxLayout(self.status_bar)
        vStatus.setContentsMargins(0, 0, 0, 0)
        vStatus.addWidget(self.status_dot)
        vStatus.addWidget(self.status_label, 1)

        rSidebar = QWidget()
        rSidebar.setObjectName("sidebar")
        rSidebar.setFixedWidth(240)

        vLayout = QVBoxLayout(rSidebar)
        vLayout.setContentsMargins(16, 22, 16, 18)
        vLayout.setSpacing(16)
        vLayout.addLayout(vBrand)
        vLayout.addWidget(vSeparator)
        vLayout.addWidget(self.progress_box)
        vLayout.addWidget(self.navigation, 1)
        vLayout.addWidget(self.create_footer_links())
        vLayout.addWidget(self.status_bar)

        return rSidebar

    def create_footer_links(self):
        """Construit les liens du pied de menu, identiques à ceux du web."""
        rLinks = QFrame()
        rLinks.setObjectName("sidebarLinks")

        vLayout = QVBoxLayout(rLinks)
        vLayout.setContentsMargins(0, 10, 0, 0)
        vLayout.setSpacing(2)

        for vTarget, vLabel, vIcon in (
            (LEGAL_LINK, "Mentions légales", "file-text"),
            (CONTACT_URL, "Me contacter", "linkedin"),
            (REPOSITORY_URL, "Code source", "github"),
            (LICENSE_LINK, f"Licence {LICENSE_NAME}", "scale"),
        ):
            vButton = QPushButton(get_icon(vIcon, COLORS["muted"], 16), vLabel)
            vButton.setObjectName("sidebarLink")
            vButton.setCursor(Qt.CursorShape.PointingHandCursor)
            vButton.clicked.connect(
                lambda _=False, pTarget=vTarget: self.open_footer_link(pTarget)
            )
            vLayout.addWidget(vButton)

        return rLinks

    def open_footer_link(self, pTarget):
        """Ouvre mentions et licence dans l'application, le contact au navigateur."""
        if pTarget == LEGAL_LINK:
            show_legal_notice(self)
        elif pTarget == LICENSE_LINK:
            show_license(self)
        else:
            QDesktopServices.openUrl(QUrl(pTarget))

    def check_progress(self):
        """Relit les points ; un gain s'affiche, un niveau gagné se fête."""
        vMode = get_game_mode()
        self.progress_box.setVisible(vMode != "off")

        if vMode == "off":
            return

        try:
            vXp = get_total_xp(self.database_file)

            if vXp == self.last_xp and self.last_progress is not None:
                return

            vProgress = build_progress(self.database_file)

        except Exception:
            # Journalisé une fois : la relecture reprend d'elle-même ensuite.
            if not self.progress_failed:
                logger.exception("Progression non relue")
                self.progress_failed = True
            return

        self.progress_failed = False
        vPrevious = self.last_progress
        self.last_progress = vProgress
        self.last_xp = get_total_xp(self.database_file)
        self.progress_box.set_progress(vProgress, pAnimate=vPrevious is not None)

        if self.pages.currentWidget() is self.progress_page:
            self.progress_page.show_progress(vProgress)

        # Premier calcul : la base de référence, sans fête pour l'historique.
        if vPrevious is None:
            return

        self.celebrate(vPrevious, vProgress, vMode)

    def celebrate(self, pPrevious, pProgress, pMode):
        """Montre les points gagnés, les quêtes réussies et un nouveau niveau."""
        vGain = pProgress["xp"] - pPrevious["xp"]
        vDelay = 0

        if vGain > 0:
            show_xp_gain(self, self.progress_box, f"+{vGain} XP")
            vDelay += TOAST_GAP_MS

        vDoneBefore = {vQuest["id"] for vQuest in pPrevious["quests"] if vQuest["done"]}

        for vQuest in pProgress["quests"]:
            if vQuest["done"] and vQuest["id"] not in vDoneBefore:
                logger.info("Quête réussie affichée : %s", vQuest["label"])
                show_xp_gain(
                    self,
                    self.progress_box,
                    f"Quête réussie : {vQuest['label']}",
                    vDelay,
                )
                vDelay += TOAST_GAP_MS

        vUnlockedBefore = {
            vItem["id"] for vItem in pPrevious["achievements"] if vItem["unlocked"]
        }

        for vItem in pProgress["achievements"]:
            if vItem["unlocked"] and vItem["id"] not in vUnlockedBefore:
                show_xp_gain(
                    self,
                    self.progress_box,
                    f"Trophée obtenu : {vItem['title']}",
                    vDelay,
                )
                vDelay += TOAST_GAP_MS

        if pProgress["level"] > pPrevious["level"]:
            logger.info(
                "Niveau %s atteint : %s", pProgress["level"], pProgress["title"]
            )

            if pMode == "full":
                CelebrationOverlay(
                    self,
                    f"Niveau {pProgress['level']}",
                    pProgress["title"],
                    f"Prochain titre : {pProgress['next_title']}",
                )
            else:
                show_xp_gain(
                    self,
                    self.progress_box,
                    f"Niveau {pProgress['level']} : {pProgress['title']}",
                    vDelay,
                )

    def add_page(self, pKey, pLabel, pIcon, pPage):
        """Ajoute une page et son entrée dans le menu latéral."""
        vItem = QListWidgetItem(
            get_icon(pIcon, COLORS["muted"], 20, pSelectedColor=COLORS["on_primary"]),
            pLabel,
        )

        self.page_rows[pKey] = self.pages.count()
        self.page_keys[self.pages.count()] = pKey
        self.page_labels[self.pages.count()] = pLabel
        self.navigation.addItem(vItem)
        self.pages.addWidget(pPage)

    def navigate(self, pKey):
        """Affiche une page, ou la page des offres avec un préréglage de filtres."""
        vKey = pKey

        if pKey in OFFER_PRESETS:
            self.offers_page.apply_preset(pKey)
            vKey = "offers"

        self.navigation.setCurrentRow(self.page_rows[vKey])

    def rebuild(self, pPage, pRestyle=None):
        """Reconstruit le contenu dans la même fenêtre, sans la fermer.

        L'affichage est suspendu pendant la reconstruction pour éviter tout
        scintillement ; setCentralWidget détruit l'ancien contenu. pRestyle
        applique un nouveau thème entre la destruction et la reconstruction.
        """
        self.setUpdatesEnabled(False)

        try:
            if pRestyle is not None:
                # Ancien contenu détruit avant le nouveau style : sinon Qt recalcule
                # le style de chaque widget des pages, pour les jeter juste après.
                shiboken6.delete(self.takeCentralWidget())
                pRestyle()

            self.build_content()
            self.navigate(pPage)

        finally:
            self.setUpdatesEnabled(True)

    def show_reset_result(self, pMessage):
        """Recharge toutes les pages après une réinitialisation des données."""
        self.rebuild("settings")
        show_message(self.settings_page.data_panel.reset_message, pMessage)

    def save_scheduled_search(self, pSources, pCriteria):
        """Enregistre la recherche du planificateur et l'indique sur la page."""
        try:
            save_scheduled_search(self.database_file, pSources, pCriteria)

        except Exception:
            logger.exception("Échec de l'enregistrement de la recherche planifiée")

            self.search_page.set_status(
                "error", "La recherche planifiée n'a pas pu être enregistrée."
            )

        else:
            self.search_page.set_status(
                "success",
                "Recherche planifiée enregistrée",
                "Activez-la et choisissez sa fréquence dans les Paramètres.",
            )
            self.settings_page.refresh_schedule()

    def show_search_results(self, pKeys, pDescription):
        """Ouvre la page des offres restreinte aux résultats d'une recherche."""
        self.offers_page.apply_preset("offers", pKeys, pDescription)
        self.navigation.setCurrentRow(self.page_rows["offers"])

    def start_offer_exam(self, pOffer):
        """Ouvre la page Révision sur l'examen blanc d'une offre."""
        self.navigate("quiz")
        self.quiz_page.start_offer_exam(pOffer)

    def start_missing_skills_exam(self, pOffer):
        """Ouvre la page Révision sur l'examen des compétences manquantes d'une offre."""
        self.navigate("quiz")
        self.quiz_page.start_missing_skills_exam(pOffer)

    def start_skills_exam(self, pSkills):
        """Ouvre la page Révision sur l'examen des compétences prioritaires."""
        self.navigate("quiz")
        self.quiz_page.start_skills_exam(pSkills)

    def revise_theme(self, pThemeKey):
        """Ouvre la page Révision sur un thème, en répétition espacée."""
        self.navigate("quiz")
        self.quiz_page.start(pThemeKey, DEFAULT_MODE)

    def prepare_questions(self, pThemeLabel):
        """Ouvre la page Révision et prépare la demande de questions d'un thème."""
        self.navigate("quiz")
        self.quiz_page.import_panel.prepare_priority(pThemeLabel)

    def show_page(self, pIndex):
        """Affiche la page choisie et rafraîchit ses données si elle le permet."""
        self.pages.setCurrentIndex(pIndex)
        self.setWindowTitle(f"{self.page_labels[pIndex]} · {self.title}")

        vPage = self.pages.currentWidget()
        vKey = self.page_keys[pIndex]

        if hasattr(vPage, "refresh") and (
            vKey not in DATA_ONLY_PAGES
            or self.refreshed_versions.get(vKey) != self.get_data_version()
        ):
            vStart = time.perf_counter()
            vPage.refresh()
            vDuration = time.perf_counter() - vStart

            if vDuration > SLOW_PAGE_SECONDS:
                logger.warning("Page lente : %s en %.1f s", vKey, vDuration)

            if vKey in DATA_ONLY_PAGES:
                self.refreshed_versions[vKey] = self.get_data_version()

        self.update_alerts()

    def get_data_version(self):
        """Retourne ce qui oblige une page à se recalculer : la base et le jour."""
        vVersion = get_database_version(self.database_file)

        # Sans empreinte lisible, la page est toujours recalculée.
        rVersion = (vVersion, date.today()) if vVersion else object()

        return rVersion

    def update_alerts(self):
        """Affiche le nombre d'actions en attente à côté de « Candidatures »."""
        try:
            vAlerts = count_alerts(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de compter les alertes du menu")
            return

        vItem = self.navigation.item(self.page_rows["applications"])
        vItem.setText(
            f"Candidatures ({vAlerts['total']})" if vAlerts["total"] else "Candidatures"
        )
        vItem.setToolTip(vAlerts["text"] if vAlerts["total"] else "")

    def on_search_started(self):
        """Signale la recherche en cours et bloque le changement de thème."""
        self.status_dot.setStyleSheet(f"color: {COLORS['warning']};")
        self.status_label.setText("Recherche en cours")
        self.status_bar.setVisible(True)
        self.settings_page.set_actions_enabled(False)

    def on_search_ended(self):
        """Masque l'état et réautorise le changement de thème."""
        self.status_bar.setVisible(False)
        self.settings_page.set_actions_enabled(True)

    def closeEvent(self, pEvent):
        """Diffère la fermeture tant qu'une recherche est en cours.

        Détruire un QThread actif fait planter l'application : la recherche est
        arrêtée et la fenêtre se ferme d'elle-même à la fin de la source en cours.
        """
        if self.search_page.is_running():
            self.search_page.search_ended.connect(self.close)
            self.search_page.stop_search()

            pEvent.ignore()
        else:
            pEvent.accept()
