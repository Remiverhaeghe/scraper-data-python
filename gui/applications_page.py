"""Page des candidatures : tableau de suivi par colonnes et taux de réponse"""

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    StatisticCard,
    clear_layout,
    create_card,
    create_page_header,
    create_scroll_content,
)
from job.application_tracking import (
    BOARD_STATUSES,
    build_application_statistics,
    build_board,
)
from job.presentation import STATUS_LABELS
from storage.job_applications import update_application_status
from utils.logger import get_logger

logger = get_logger(__name__)

STATISTIC_HEADERS = ["", "Envoyées", "Réponses", "Taux"]


class ApplicationsPage(QWidget):
    """Affiche les candidatures par étape et leurs statistiques de réponse."""

    # Offre à ouvrir dans la page Offres : couples (source, identifiant) et description
    offer_requested = Signal(object, str)
    application_changed = Signal()

    def __init__(self, pDatabaseFile):
        """Construit les chiffres clés, les colonnes et les tableaux, vides."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Candidatures",
            "Vos candidatures par étape, et les sources ou postes qui répondent le plus",
            pIcon="send",
        )

        self.statistic_cards = {
            "sent": StatisticCard("Candidatures envoyées", "send", "blue"),
            "answered": StatisticCard("Réponses reçues", "circle-check", "green"),
            "interviews": StatisticCard("Entretiens obtenus", "calendar", "amber"),
            "rate": StatisticCard("Taux de réponse", "sparkles", "purple"),
        }

        vStatistics = QHBoxLayout()
        vStatistics.setSpacing(16)

        for vCard in self.statistic_cards.values():
            vStatistics.addWidget(vCard)

        self.message_label = QLabel()
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.hide()

        vLayout.addLayout(vStatistics)
        vLayout.addWidget(self.message_label)
        vLayout.addLayout(self.create_board())
        vLayout.addLayout(self.create_statistic_tables())
        vLayout.addStretch()

    def create_board(self):
        """Construit les quatre colonnes du tableau de suivi."""
        self.board_columns = []

        rLayout = QHBoxLayout()
        rLayout.setSpacing(16)

        for _ in range(4):
            vCard, vCardLayout = create_card("")

            # Largeur fixée par la mise en page seule : les quatre colonnes restent
            # égales quelle que soit la longueur des titres.
            vCard.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )

            vCards = QVBoxLayout()
            vCards.setSpacing(10)

            vCardLayout.addLayout(vCards)
            vCardLayout.addStretch()

            self.board_columns.append((vCard, vCards))
            rLayout.addWidget(vCard, 1)

        return rLayout

    def create_statistic_tables(self):
        """Construit les tableaux de taux de réponse par dimension."""
        self.statistic_tables = []

        rLayout = QGridLayout()
        rLayout.setSpacing(16)

        for vColumn in range(3):
            vTable = QTableWidget(0, len(STATISTIC_HEADERS))
            vTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            vTable.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            vTable.verticalHeader().hide()
            vTable.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            vTable.setMinimumHeight(260)

            vCard, vCardLayout = create_card("")
            vCardLayout.addWidget(vTable, 1)

            self.statistic_tables.append((vCard, vTable))
            rLayout.addWidget(vCard, 0, vColumn)

        return rLayout

    def refresh(self):
        """Relit les candidatures et leurs statistiques."""
        try:
            vBoard = build_board(self.database_file, datetime.now())
            vStatistics = build_application_statistics(self.database_file)

        except Exception:
            logger.exception("Impossible de charger les candidatures")

            self.message_label.setText("Les candidatures n'ont pas pu être chargées.")
            self.message_label.show()
            return

        self.message_label.hide()

        for vKey, vCard in self.statistic_cards.items():
            vValue = vStatistics[vKey]

            if vKey == "rate":
                vValue = "-" if vValue is None else f"{vValue} %"

            vCard.set_value(vValue)

        self.show_board(vBoard)
        self.show_statistics(vStatistics["tables"])

    def show_board(self, pBoard):
        """Remplit chaque colonne avec ses cartes."""
        for (vCard, vCards), vColumn in zip(self.board_columns, pBoard):
            vCard.findChild(QLabel, "cardTitle").setText(
                f"{vColumn['label']} ({len(vColumn['cards'])})"
            )

            clear_layout(vCards)

            for vApplication in vColumn["cards"]:
                vCards.addWidget(self.create_board_card(vApplication))

            if not vColumn["cards"]:
                vEmpty = QLabel("Aucune candidature")
                vEmpty.setObjectName("cardSubtitle")
                vCards.addWidget(vEmpty)

    def create_board_card(self, pApplication):
        """Crée la carte d'une candidature : offre, dates et statut modifiable."""
        vTitle = QPushButton(pApplication["title"] or "Offre sans titre")
        vTitle.setObjectName("linkButton")
        vTitle.setToolTip("Ouvrir l'offre dans la page Offres")
        vTitle.clicked.connect(
            lambda: self.offer_requested.emit(
                [(pApplication["source"], pApplication["source_id"])],
                f"Candidature « {pApplication['title'] or 'offre sans titre'} »",
            )
        )

        vCompany = QLabel(
            " · ".join(
                vValue
                for vValue in (pApplication["company"], pApplication["source_label"])
                if vValue
            )
        )
        vCompany.setObjectName("cardSubtitle")

        vStatusCombo = QComboBox()

        for vStatus in BOARD_STATUSES:
            vStatusCombo.addItem(STATUS_LABELS[vStatus], vStatus)

        vStatusCombo.setCurrentIndex(vStatusCombo.findData(pApplication["status"]))
        vStatusCombo.setToolTip("« Clôturé » retire la candidature du tableau")
        vStatusCombo.currentIndexChanged.connect(
            lambda: self.change_status(pApplication, vStatusCombo.currentData())
        )

        rCard = QFrame()
        rCard.setObjectName("boardCard")

        vLayout = QVBoxLayout(rCard)
        vLayout.setContentsMargins(12, 10, 12, 10)
        vLayout.setSpacing(4)
        vLayout.addWidget(vTitle)
        vLayout.addWidget(vCompany)

        if pApplication["applied_label"]:
            vApplied = QLabel(f"Postulé le {pApplication['applied_label']}")
            vApplied.setObjectName("cardSubtitle")
            vLayout.addWidget(vApplied)

        if pApplication["follow_up_due"]:
            vFollowUp = QLabel(
                f"À relancer depuis le {pApplication['follow_up_label']}"
            )
            vFollowUp.setStyleSheet(f"color: {COLORS['warning']};")
            vLayout.addWidget(vFollowUp)

        vLayout.addWidget(vStatusCombo)

        return rCard

    def change_status(self, pApplication, pStatus):
        """Déplace une candidature dans la colonne de son nouveau statut."""
        try:
            update_application_status(
                self.database_file,
                pApplication["source"],
                pApplication["source_id"],
                pStatus,
            )

        except Exception:
            logger.exception("Échec du changement de statut de la candidature")

            self.message_label.setText("Le statut n'a pas pu être modifié.")
            self.message_label.show()

        else:
            self.refresh()
            self.application_changed.emit()

    def show_statistics(self, pTables):
        """Remplit les tableaux de taux de réponse."""
        for (vCard, vTable), (vTitle, vRows) in zip(self.statistic_tables, pTables):
            vCard.findChild(QLabel, "cardTitle").setText(vTitle)

            vTable.setHorizontalHeaderLabels(STATISTIC_HEADERS)
            vTable.setRowCount(len(vRows))

            for vRow, vValues in enumerate(vRows):
                for vColumn, vValue in enumerate(
                    (
                        vValues["label"],
                        vValues["sent"],
                        vValues["answered"],
                        f"{vValues['rate']} %",
                    )
                ):
                    vTable.setItem(vRow, vColumn, QTableWidgetItem(str(vValue)))
