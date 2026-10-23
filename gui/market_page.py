"""Page Mon marché : demande et salaires par compétence et par ville"""

from datetime import datetime

from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    StatisticCard,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.market import (
    CITY_COLUMNS,
    MARKET_DAYS,
    SKILL_COLUMNS,
    build_market,
    build_market_cells,
)
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

    def __init__(self, pDatabaseFile):
        """Construit la page ; les données sont chargées par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile

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

        vSkillsCard, vSkillsLayout = create_card(
            "Compétences les plus demandées",
            "Médiane affichée à partir de trois salaires",
        )
        self.skills_table = create_table(SKILL_COLUMNS)
        vSkillsLayout.addWidget(self.skills_table)
        vLayout.addWidget(vSkillsCard)

        vCitiesCard, vCitiesLayout = create_card("Villes qui recrutent le plus")
        self.cities_table = create_table(CITY_COLUMNS)
        vCitiesLayout.addWidget(self.cities_table)
        vLayout.addWidget(vCitiesCard)

    def refresh(self):
        """Recalcule le marché à partir des offres en base."""
        try:
            vMarket = build_market(self.database_file, datetime.now())

        except Exception:
            logger.exception("Impossible de calculer le marché")

            return

        for vName, vCard in self.cards.items():
            vCard.set_value(vMarket[vName])

        # Sans salaire visé, la carte renvoie vers les Paramètres.
        if vMarket["target"] is None:
            self.cards["target"].set_value("À régler")

        fill_table(self.skills_table, vMarket["skills"], pWithMine=True)
        fill_table(self.cities_table, vMarket["cities"])
        self.cities_table.setToolTip(
            f"{vMarket['unknown_city_count']} offre(s) sans ville ne sont pas classées"
        )
