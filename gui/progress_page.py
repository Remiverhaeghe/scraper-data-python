"""Page Progression : niveau, quêtes du jour et de la semaine, points gagnés"""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gui.chart import BarChart
from gui.theme import ACCENTS, COLORS
from gui.widgets import (
    StatisticCard,
    clear_layout,
    create_card,
    create_icon_label,
    create_page_header,
    create_scroll_content,
)
from job.progress import build_progress
from utils.logger import get_logger

logger = get_logger(__name__)


def create_quest_row(pQuest):
    """Construit la ligne d'une quête : case, libellé, barre d'avancée et points."""

    vAccent = "green" if pQuest["done"] else ("purple" if pQuest["weekly"] else "blue")
    vColor, vBackground = ACCENTS[vAccent]

    vIcon = create_icon_label(
        (
            "circle-check"
            if pQuest["done"]
            else ("calendar" if pQuest["weekly"] else "target")
        ),
        vColor,
        20,
    )

    vLabel = QLabel(("Semaine · " if pQuest["weekly"] else "") + pQuest["label"])
    vLabel.setStyleSheet(
        f"color: {COLORS['muted']}; text-decoration: line-through;"
        if pQuest["done"]
        else f"color: {COLORS['text']}; font-weight: 600;"
    )

    vBar = QProgressBar()
    vBar.setMaximum(pQuest["target"])
    vBar.setValue(pQuest["progress"])
    vBar.setFormat(f"{pQuest['progress']} / {pQuest['target']}")
    vBar.setFixedHeight(18)
    vBar.setStyleSheet(
        f"QProgressBar {{ background: {vBackground}; border: none; "
        "border-radius: 9px; text-align: center; }"
        f"QProgressBar::chunk {{ background: {vColor}; border-radius: 9px; }}"
    )

    vXp = QLabel(f"+{pQuest['xp']} XP")
    vXp.setStyleSheet(f"color: {vColor}; font-weight: 700;")

    rRow = QWidget()
    vLayout = QHBoxLayout(rRow)
    vLayout.setContentsMargins(0, 0, 0, 0)
    vLayout.setSpacing(12)
    vLayout.addWidget(vIcon)
    vLayout.addWidget(vLabel, 2)
    vLayout.addWidget(vBar, 1)
    vLayout.addWidget(vXp)

    return rRow


class ProgressPage(QWidget):
    """Montre le niveau atteint, les quêtes en cours et la façon de gagner des points."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh la remplit."""
        super().__init__()

        self.database_file = pDatabaseFile

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Progression",
            "Chaque action utile à votre recherche rapporte des points",
            pIcon="award",
        )

        vColor, vBackground = ACCENTS["blue"]

        self.level_label = QLabel()
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_label.setFixedSize(84, 84)
        self.level_label.setStyleSheet(
            f"background: {vColor}; color: {COLORS['on_primary']}; "
            "border-radius: 42px; font-size: 30px; font-weight: 800;"
        )

        self.title_label = QLabel()
        self.title_label.setStyleSheet(
            f"color: {vColor}; font-size: 22px; font-weight: 800;"
        )

        self.next_label = QLabel()
        self.next_label.setObjectName("cardSubtitle")

        self.level_bar = QProgressBar()
        self.level_bar.setFixedHeight(22)
        self.level_bar.setStyleSheet(
            f"QProgressBar {{ background: {COLORS['surface']}; border: none; "
            "border-radius: 11px; text-align: center; font-weight: 600; }"
            f"QProgressBar::chunk {{ background: {vColor}; border-radius: 11px; }}"
        )

        vTexts = QVBoxLayout()
        vTexts.setSpacing(6)
        vTexts.addWidget(self.title_label)
        vTexts.addWidget(self.next_label)
        vTexts.addWidget(self.level_bar)

        vBanner = QWidget()
        vBanner.setObjectName("levelBanner")
        vBanner.setStyleSheet(
            f"QWidget#levelBanner {{ background: {vBackground}; border-radius: 16px; }}"
        )
        vBannerLayout = QHBoxLayout(vBanner)
        vBannerLayout.setContentsMargins(24, 20, 24, 20)
        vBannerLayout.setSpacing(22)
        vBannerLayout.addWidget(self.level_label)
        vBannerLayout.addLayout(vTexts, 1)

        self.cards = {
            "xp": StatisticCard("Points au total", "sparkles", "blue"),
            "today_xp": StatisticCard("Points aujourd'hui", "zap", "green"),
            "streak": StatisticCard("Jours de série", "flame", "amber"),
            "best_streak": StatisticCard("Meilleure série", "trophy", "purple"),
        }
        vCards = QGridLayout()
        vCards.setSpacing(16)

        for vIndex, vCard in enumerate(self.cards.values()):
            vCards.addWidget(vCard, 0, vIndex)

        vQuestCard, self.quests_layout = create_card(
            "Quêtes",
            "Trois quêtes par jour, choisies selon votre situation, et une pour la "
            "semaine. Une série perdue ne fait jamais perdre de points.",
            pIcon="target",
            pOpen=True,
        )

        vHistoryCard, vHistoryLayout = create_card(
            "Points des 14 derniers jours", pIcon="history", pKey="progress-history"
        )
        self.chart = BarChart()
        vHistoryLayout.addWidget(self.chart)

        vRulesCard, self.rules_layout = create_card(
            "Comment gagner des points",
            "Les actions qui font avancer la recherche d'emploi rapportent le plus",
            pIcon="list-checks",
            pKey="progress-rules",
        )

        vLayout.addWidget(vBanner)
        vLayout.addLayout(vCards)
        vLayout.addWidget(vQuestCard)
        vLayout.addWidget(vHistoryCard)
        vLayout.addWidget(vRulesCard)
        vLayout.addStretch(1)

    def refresh(self):
        """Relit la progression et met la page à jour."""
        try:
            vProgress = build_progress(self.database_file)

        except Exception:
            logger.exception("Progression non calculée")
            self.title_label.setText("La progression n'a pas pu être calculée.")
            return

        self.show_progress(vProgress)

    def show_progress(self, pProgress):
        """Affiche une progression déjà calculée."""
        self.level_label.setText(str(pProgress["level"]))
        self.title_label.setText(f"Niveau {pProgress['level']} · {pProgress['title']}")
        self.next_label.setText(
            f"Encore {pProgress['xp_for_level'] - pProgress['xp_in_level']} XP pour "
            f"devenir {pProgress['next_title']}"
        )
        self.level_bar.setMaximum(pProgress["xp_for_level"])
        self.level_bar.setValue(pProgress["xp_in_level"])
        self.level_bar.setFormat(
            f"{pProgress['xp_in_level']} / {pProgress['xp_for_level']} XP"
        )

        for vKey, vCard in self.cards.items():
            vCard.set_value(pProgress[vKey])

        clear_layout(self.quests_layout)

        for vQuest in pProgress["quests"]:
            self.quests_layout.addWidget(create_quest_row(vQuest))

        self.chart.set_series(
            [
                date.fromisoformat(vDay["day"]).strftime("%d/%m")
                for vDay in pProgress["history"]
            ],
            [
                (
                    "Points",
                    ACCENTS["blue"][0],
                    [vDay["xp"] for vDay in pProgress["history"]],
                )
            ],
            pEmptyText="Aucun point ces 14 derniers jours : une révision suffit pour commencer",
        )

        clear_layout(self.rules_layout)

        for vRule in pProgress["rules"]:
            vRow = QHBoxLayout()
            vLabel = QLabel(vRule["label"])
            vXp = QLabel(f"+{vRule['xp']} XP")
            vXp.setStyleSheet(f"color: {ACCENTS['green'][0]}; font-weight: 700;")
            vRow.addWidget(vLabel, 1)
            vRow.addWidget(vXp)
            vHolder = QWidget()
            vHolder.setLayout(vRow)
            vRow.setContentsMargins(0, 0, 0, 0)
            self.rules_layout.addWidget(vHolder)
