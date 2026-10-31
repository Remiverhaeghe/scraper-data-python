"""Carte du bilan de la saison : la semaine écoulée comparée à la précédente"""

from datetime import date

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.theme import COLORS
from gui.icons import get_icon
from gui.widgets import clear_layout, create_card

STATISTIC_COLUMNS = 3
MEDAL_SIZE = 28


def get_trend_color(pStatistic):
    """Retourne la couleur d'une évolution : vert en hausse, rouge en baisse."""

    if pStatistic["value"] > pStatistic["previous"]:
        return COLORS["success"]

    if pStatistic["value"] < pStatistic["previous"]:
        return COLORS["danger"]

    return COLORS["muted"]


def format_day(pDay):
    """Retourne un jour ISO au format 26/10."""

    rText = date.fromisoformat(pDay).strftime("%d/%m")

    return rText


class SeasonCard(QWidget):
    """Bilan de la semaine écoulée : médaille, chiffres et évolution, meilleur jour."""

    def __init__(self):
        """Construit la carte vide ; set_review la remplit."""
        super().__init__()

        vCard, vLayout = create_card(
            "Bilan de la saison",
            "La semaine écoulée, du lundi au dimanche, comparée à la précédente",
            pIcon="award",
            pKey="progress-season",
            pOpen=True,
        )
        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.medal_icon = QLabel()
        self.medal_label = QLabel()
        self.medal_label.setWordWrap(True)
        vMedal = QHBoxLayout()
        vMedal.addWidget(self.medal_icon)
        vMedal.addWidget(self.medal_label, 1)
        self.statistics_grid = QGridLayout()
        self.statistics_grid.setSpacing(12)
        self.best_day_label = QLabel()
        self.best_day_label.setObjectName("cardSubtitle")

        vLayout.addWidget(self.title_label)
        vLayout.addWidget(self.summary_label)
        vLayout.addLayout(vMedal)
        vLayout.addLayout(self.statistics_grid)
        vLayout.addWidget(self.best_day_label)

        vOuter = QVBoxLayout(self)
        vOuter.setContentsMargins(0, 0, 0, 0)
        vOuter.addWidget(vCard)

    def set_review(self, pReview):
        """Affiche le bilan, ou un message après une semaine sans activité."""
        clear_layout(self.statistics_grid)

        if pReview is None:
            self.title_label.setText("Pas de bilan cette semaine")
            self.summary_label.setText(
                "La semaine dernière s'est passée sans activité : une révision ou "
                "une candidature suffit pour que le prochain lundi ait son bilan."
            )
            self.medal_icon.hide()
            self.medal_label.hide()
            self.best_day_label.hide()
            return

        vRecord = " · record des huit dernières semaines" if pReview["record"] else ""
        self.title_label.setText(
            f"{pReview['title']} · du {format_day(pReview['start'])} au "
            f"{format_day(pReview['end'])}{vRecord}"
        )
        self.summary_label.setText(pReview["summary"])

        vMedal = pReview["medal"]
        self.medal_icon.setVisible(vMedal is not None)
        self.medal_label.setVisible(vMedal is not None)

        if vMedal:
            self.medal_icon.setPixmap(
                get_icon("award", vMedal["color"], MEDAL_SIZE).pixmap(
                    MEDAL_SIZE, MEDAL_SIZE
                )
            )
            self.medal_label.setText(f"<b>{vMedal['label']}</b>")

        for vIndex, vStatistic in enumerate(pReview["statistics"]):
            vTile = QLabel(
                f"<b style='font-size:18px'>{vStatistic['value']}</b> "
                f"{vStatistic['label']} <span style='color:"
                f"{get_trend_color(vStatistic)}'><b>{vStatistic['trend']}</b></span>"
            )
            vTile.setToolTip(f"{vStatistic['previous']} la semaine précédente")
            self.statistics_grid.addWidget(
                vTile, vIndex // STATISTIC_COLUMNS, vIndex % STATISTIC_COLUMNS
            )

        self.best_day_label.setText(
            f"Meilleur jour : le {format_day(pReview['best_day']['day'])}, "
            f"{pReview['best_day']['xp']} XP"
        )
        self.best_day_label.show()
