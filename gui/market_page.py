"""Page Mon marché : demande et salaires par compétence et par ville"""

import threading
from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import ACCENTS, COLORS
from gui.widgets import (
    StatisticCard,
    create_button,
    create_card,
    create_icon_label,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.geocoding import get_home_department
from job.labour_market import (
    BMO_URL,
    OUTLOOK_LISTS,
    build_outlook,
    describe_outlook_row,
    refresh_labour_market,
)
from job.market import (
    CITY_COLUMNS,
    HISTORY_COLUMNS,
    MARKET_DAYS,
    REGION_COLUMNS,
    SKILL_COLUMNS,
    build_history_cells,
    build_market,
    build_market_cells,
    build_market_history,
    load_market_period,
)
from job.profile import load_profile
from utils.logger import get_logger

logger = get_logger(__name__)


def create_table(pColumns):
    """Crée un tableau en lecture seule, première colonne étirée."""

    rTable = QTableWidget(0, len(pColumns))
    rTable.setHorizontalHeaderLabels(pColumns)
    rTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    rTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    rTable.verticalHeader().hide()
    rTable.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    rTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    rTable.setMinimumHeight(320)

    return rTable


def fill_table(pTable, pRows, pWithMine=False):
    """Remplace les lignes d'un tableau par celles du marché."""

    pTable.setRowCount(len(pRows))

    for vRowIndex, vRow in enumerate(pRows):
        for vColumn, vText in enumerate(build_market_cells(vRow, pWithMine)):
            pTable.setItem(vRowIndex, vColumn, QTableWidgetItem(vText))


class MarketPage(QWidget):
    """Affiche le marché tiré des offres récentes : volumes et salaires."""

    # Fin du téléchargement de l'enquête, émise depuis le thread : réussite
    outlook_downloaded = Signal(bool)

    # Compétences prioritaires dont l'examen blanc est demandé
    exam_requested = Signal(list)

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.outlook_downloaded.connect(self.show_downloaded)

        vContent = create_scroll_content(self)
        vLayout = QVBoxLayout(vContent)
        vLayout.setContentsMargins(32, 18, 32, 18)
        vLayout.setSpacing(12)

        create_page_header(
            vLayout,
            "Mon marché",
            f"Offres en France des {MARKET_DAYS} derniers jours, hors stage, "
            "alternance et mission libre",
            pIcon="banknote",
        )

        self.cards = {
            "offer_count": StatisticCard("Offres analysées", "briefcase", "blue"),
            "salaried_count": StatisticCard("Avec un salaire", "banknote", "green"),
            "median": StatisticCard("Net mensuel médian", "scale", "amber"),
            "target": StatisticCard("Votre salaire visé", "target", "purple"),
        }

        vCards = QGridLayout()
        vCards.setSpacing(18)

        for vIndex, vCard in enumerate(self.cards.values()):
            vCards.addWidget(vCard, 0, vIndex)

        vLayout.addLayout(vCards)

        vPriorityCard, vPriorityLayout = create_card(
            "À travailler en priorité",
            "Compétences les plus demandées que vous n'avez pas évaluées, ou notées "
            "sous 5 : à réviser, ou à évaluer dans Profil",
            pIcon="target",
            pOpen=True,
        )
        self.priority_label = QLabel()
        self.priority_label.setWordWrap(True)
        vPriorityLayout.addWidget(self.priority_label)

        self.priority_skills = []
        self.exam_button = create_button(
            "Examen blanc sur ces compétences", "timer", pObjectName="primaryButton"
        )
        self.exam_button.clicked.connect(
            lambda: self.exam_requested.emit(self.priority_skills)
        )
        vPriorityLayout.addWidget(self.exam_button, 0, Qt.AlignmentFlag.AlignLeft)
        vLayout.addWidget(vPriorityCard)
        vLayout.addWidget(self.create_outlook_card())

        vHistoryCard, vHistoryLayout = create_card(
            "Évolution du marché",
            "Offres vues chaque mois, et celles qui citent une compétence de votre "
            "profil",
            pOpen=True,
        )
        self.history_chart = BarChart()
        self.history_chart.setMinimumHeight(200)
        self.history_table = create_table(HISTORY_COLUMNS)
        self.history_table.setMinimumHeight(140)
        vHistoryLayout.addWidget(self.history_chart)
        vHistoryLayout.addWidget(self.history_table)
        vLayout.addWidget(vHistoryCard)

        vSkillsCard, vSkillsLayout = create_card(
            "Compétences les plus demandées",
            "Médiane affichée à partir de trois salaires",
            pOpen=True,
        )
        self.skills_table = create_table(SKILL_COLUMNS)
        vSkillsLayout.addWidget(self.skills_table)
        vLayout.addWidget(vSkillsCard)

        vRegionsCard, vRegionsLayout = create_card("Régions qui recrutent le plus")
        self.regions_table = create_table(REGION_COLUMNS)
        vRegionsLayout.addWidget(self.regions_table)
        vLayout.addWidget(vRegionsCard)

        vCitiesCard, vCitiesLayout = create_card("Villes qui recrutent le plus")
        self.cities_table = create_table(CITY_COLUMNS)
        vCitiesLayout.addWidget(self.cities_table)
        vLayout.addWidget(vCitiesCard)
        vLayout.addStretch()

    def create_outlook_card(self):
        """Construit les métiers qui recrutent d'après l'enquête de France Travail."""
        vCard, vLayout = create_card(
            "Métiers qui recrutent (France Travail)",
            "Projets de recrutement déclarés chaque année par plus de 400 000 "
            "employeurs (enquête Besoins en Main-d'Œuvre)",
            pIcon="trophy",
            pOpen=True,
        )

        self.outlook_label = QLabel()
        self.outlook_label.setObjectName("cardSubtitle")
        self.outlook_label.setWordWrap(True)

        self.zone_combo = QComboBox()
        self.zone_combo.setToolTip("France entière, ou un département")
        self.zone_combo.activated.connect(lambda _: self.show_outlook())

        self.outlook_button = create_button("Télécharger l'enquête", "download")
        self.outlook_button.clicked.connect(self.download_outlook)

        vRow = QHBoxLayout()
        vRow.addWidget(self.zone_combo, 1)
        vRow.addWidget(self.outlook_button)

        self.outlook_lists = {}
        vGrid = QGridLayout()
        vGrid.setSpacing(18)

        for vIndex, (vKey, vTitle, vHelp, vIcon, vAccent) in enumerate(OUTLOOK_LISTS):
            vList = QLabel()
            vList.setWordWrap(True)
            vList.setTextFormat(Qt.TextFormat.RichText)
            vList.setOpenExternalLinks(True)
            self.outlook_lists[vKey] = (vTitle, vList)
            vGrid.addWidget(
                create_outlook_panel(vTitle, vHelp, vIcon, vAccent, vList),
                vIndex // 2,
                vIndex % 2,
            )

        vSource = QLabel(
            f"<a href='{BMO_URL}'>Détail par métier et bassin d'emploi sur le site "
            "de France Travail</a> · un clic sur un métier ouvre ses offres"
        )
        vSource.setObjectName("cardSubtitle")
        vSource.setOpenExternalLinks(True)

        vLayout.addWidget(self.outlook_label)
        vLayout.addLayout(vRow)
        vLayout.addLayout(vGrid)
        vLayout.addWidget(vSource)

        return vCard

    def show_outlook(self):
        """Affiche les métiers de la zone choisie ; vide sans enquête téléchargée."""
        vZone = self.zone_combo.currentData()

        if vZone is None:
            vZone = get_home_department(self.database_file)

        try:
            vOutlook = build_outlook(
                load_profile(self.database_file),
                None if vZone in (None, "france") else vZone,
            )

        except Exception:
            logger.exception("Métiers qui recrutent non calculés")
            vOutlook = None

        self.zone_combo.setVisible(vOutlook is not None)

        if vOutlook is None:
            self.outlook_label.setText(
                "Téléchargez l'enquête (deux années, environ 8 Mo) pour voir les "
                "métiers en hausse, ceux qui peinent à recruter et ceux proches de "
                "votre profil."
            )
            for _, vList in self.outlook_lists.values():
                vList.clear()
            return

        if not self.zone_combo.count():
            self.zone_combo.addItem("France entière", "france")

            for vCode, vName in vOutlook["departments"]:
                self.zone_combo.addItem(f"{vCode} · {vName}", vCode)

            vIndex = self.zone_combo.findData(vZone)
            self.zone_combo.setCurrentIndex(max(vIndex, 0))

        self.outlook_button.setText("Mettre à jour l'enquête")
        self.outlook_label.setText(
            f"Enquête {vOutlook['year']}"
            + (
                f", comparée à {vOutlook['previous_year']}"
                if vOutlook["previous_year"]
                else ""
            )
            + f" · {vOutlook['scope']}"
        )

        for vKey, (_, vList) in self.outlook_lists.items():
            vList.setText(
                "<br>".join(
                    f'<a href="{escape(vRow["link"])}" style="color: {COLORS["text"]};'
                    f' text-decoration: none;">{escape(vRow["label"])}</a><br>'
                    f'<small style="color: {COLORS["muted"]};">'
                    f"{escape(describe_outlook_row(vRow))}</small>"
                    for vRow in vOutlook[vKey]
                )
                or "Aucun métier pour cette zone."
            )

    def download_outlook(self):
        """Télécharge l'enquête en arrière-plan : une vingtaine de secondes."""
        self.outlook_button.setEnabled(False)
        self.outlook_label.setText("Téléchargement de l'enquête France Travail…")
        threading.Thread(target=self.run_outlook_download, daemon=True).start()

    def run_outlook_download(self):
        """Télécharge et résume l'enquête ; appelé dans un thread."""
        try:
            refresh_labour_market()
            vSuccess = True

        except Exception:
            logger.exception("Enquête France Travail non téléchargée")
            vSuccess = False

        self.outlook_downloaded.emit(vSuccess)

    def show_downloaded(self, pSuccess):
        """Réaffiche les métiers, ou explique l'échec du téléchargement."""
        self.outlook_button.setEnabled(True)
        self.show_outlook()

        if not pSuccess:
            show_message(
                self.outlook_label,
                "Téléchargement impossible : vérifiez la connexion et réessayez.",
                "danger",
            )

    def show_history(self, pHistory):
        """Affiche l'évolution du marché : graphique et tableau mois par mois."""
        self.history_chart.set_series(
            [vMonth["label"] for vMonth in pHistory],
            [
                (
                    "Offres",
                    COLORS["primary"],
                    [vMonth["offers"] for vMonth in pHistory],
                ),
                (
                    "Avec vos compétences",
                    COLORS["success"],
                    [vMonth["mine"] for vMonth in pHistory],
                ),
            ],
            pAxes=("Mois", "Offres vues"),
            pEmptyText="Aucune offre pour le moment",
        )
        self.history_table.setRowCount(len(pHistory))

        for vRowIndex, vMonth in enumerate(pHistory):
            for vColumn, vText in enumerate(build_history_cells(vMonth)):
                self.history_table.setItem(vRowIndex, vColumn, QTableWidgetItem(vText))

    def refresh(self):
        """Recalcule le marché à partir des offres en base."""
        try:
            vNow = datetime.now()
            vOffers = load_market_period(self.database_file, vNow)
            vMarket = build_market(self.database_file, vNow, pOffers=vOffers)
            vHistory = build_market_history(self.database_file, vNow, pOffers=vOffers)

        except Exception:
            logger.exception("Impossible de calculer le marché")

            return

        for vName, vCard in self.cards.items():
            vCard.set_value(vMarket[vName])

        # Sans salaire visé, la carte renvoie vers les Paramètres.
        if vMarket["target"] is None:
            self.cards["target"].set_value("À régler")

        self.priority_skills = [vSkill["name"] for vSkill in vMarket["priorities"]]
        self.exam_button.setEnabled(bool(self.priority_skills))
        self.priority_label.setText(
            "\n".join(
                f"{vSkill['name']} · {vSkill['label']}"
                for vSkill in vMarket["priorities"]
            )
            or "Toutes les compétences les plus demandées sont maîtrisées."
        )
        self.show_history(vHistory)
        self.show_outlook()
        fill_table(self.skills_table, vMarket["skills"], pWithMine=True)
        fill_table(self.regions_table, vMarket["regions"])
        self.regions_table.setToolTip(
            f"{vMarket['unknown_region_count']} offre(s) pas encore placée(s) sur la "
            "carte ne sont pas classées"
        )
        fill_table(self.cities_table, vMarket["cities"])
        self.cities_table.setToolTip(
            f"{vMarket['unknown_city_count']} offre(s) sans ville ne sont pas classées"
        )


def create_outlook_panel(pTitle, pHelp, pIcon, pAccent, pList):
    """Encadre une liste de métiers sur fond coloré, sous son icône et son titre."""

    vColor, vBackground = ACCENTS[pAccent]

    rPanel = QFrame()
    rPanel.setObjectName("outlookPanel")
    rPanel.setStyleSheet(
        f"QFrame#outlookPanel {{ background: {vBackground}; border-radius: 12px; }}"
    )

    vTitle = QLabel(pTitle)
    vTitle.setStyleSheet(f"color: {vColor}; font-weight: 600;")

    vHeader = QHBoxLayout()
    vHeader.setSpacing(8)
    vHeader.addWidget(create_icon_label(pIcon, vColor, 18))
    vHeader.addWidget(vTitle, 1)

    vHelp = QLabel(pHelp)
    vHelp.setObjectName("cardSubtitle")
    vHelp.setWordWrap(True)

    vLayout = QVBoxLayout(rPanel)
    vLayout.setContentsMargins(16, 14, 16, 14)
    vLayout.setSpacing(6)
    vLayout.addLayout(vHeader)
    vLayout.addWidget(vHelp)
    vLayout.addWidget(pList)
    # Contenu en haut du cadre, aligné sur la liste voisine plus longue
    vLayout.addStretch(1)

    return rPanel
