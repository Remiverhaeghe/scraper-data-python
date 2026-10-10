"""Page d'accueil : synthèse des offres, du suivi et de la dernière exécution"""

from datetime import datetime, timedelta

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from config import NEW_OFFER_DAYS
from gui.widgets import StatisticCard, create_page_header
from job.presentation import EXECUTION_STATUS_LABELS, describe_search
from storage.history_repository import get_history
from storage.job_offers import FOLLOW_UP_STATUSES, count_offers
from utils.logger import get_logger

logger = get_logger(__name__)


def load_statistics(pDatabaseFile, pNow=None):
    """Calcule les indicateurs affichés sur l'accueil."""

    vNow = pNow if pNow is not None else datetime.now()

    vLastExecutions = get_history(pDatabaseFile, pLimit=1)

    rStatistics = {
        "offers": count_offers(pDatabaseFile, pHideIgnored=True),
        "new_offers": count_offers(
            pDatabaseFile,
            pSeenSince=vNow - timedelta(days=NEW_OFFER_DAYS),
            pHideIgnored=True,
        ),
        "applications": sum(
            count_offers(pDatabaseFile, pStatus=vStatus)
            for vStatus in FOLLOW_UP_STATUSES
        ),
        "follow_ups": count_offers(pDatabaseFile, pFollowUpBefore=vNow),
        "last_execution": vLastExecutions[0] if vLastExecutions else None,
    }

    return rStatistics


def describe_execution(pEntry):
    """Résume une exécution en une phrase."""

    if pEntry is None:
        rDescription = "Aucune recherche lancée pour le moment."
    else:
        vStatus = EXECUTION_STATUS_LABELS.get(pEntry.status, pEntry.status)
        vSearch = describe_search(pEntry.parameters)

        rDescription = (
            f"Dernière exécution le {pEntry.started_at:%d/%m/%Y à %H:%M}"
            f"{f' ({vSearch})' if vSearch else ''} : "
            f"{pEntry.item_count} offre(s) en {pEntry.duration_seconds:.1f} s, "
            f"{vStatus.lower()}."
        )

    return rDescription


class HomePage(QWidget):
    """Affiche les indicateurs principaux de l'application."""

    def __init__(self, pDatabaseFile):
        """Construit la page avec ses cartes statistiques."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(32, 28, 32, 28)

        create_page_header(
            vLayout, "Accueil", "Vue d'ensemble des offres et de vos candidatures"
        )

        self.cards = {
            "offers": StatisticCard("Offres actives en base"),
            "new_offers": StatisticCard(
                f"Nouvelles offres ({NEW_OFFER_DAYS} derniers jours)"
            ),
            "applications": StatisticCard("Candidatures en cours"),
            "follow_ups": StatisticCard("Relances à faire"),
        }

        vGrid = QGridLayout()
        vGrid.setSpacing(16)

        for vIndex, vCard in enumerate(self.cards.values()):
            vGrid.addWidget(vCard, 0, vIndex)

        vLayout.addLayout(vGrid)
        vLayout.addSpacing(20)

        self.execution_label = QLabel()
        self.execution_label.setObjectName("pageSubtitle")

        vLayout.addWidget(self.execution_label)
        vLayout.addStretch()

    def refresh(self):
        """Relit les indicateurs en base."""
        try:
            vStatistics = load_statistics(self.database_file)

        except Exception:
            logger.exception("Impossible de charger les statistiques de l'accueil")

            self.execution_label.setText("Les statistiques sont indisponibles.")

        else:
            for vName, vCard in self.cards.items():
                vCard.set_value(vStatistics[vName])

            self.execution_label.setText(
                describe_execution(vStatistics["last_execution"])
            )
