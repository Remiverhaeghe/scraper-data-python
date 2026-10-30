"""Page Progression : niveau, quêtes du jour et de la semaine, points gagnés"""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
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
from job.achievements import HEATMAP_WEEKS, get_heat_level, sort_achievements
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


TROPHY_COLUMNS = 4

# Taille d'une case de la carte d'activité, et espace entre deux cases
HEAT_CELL = 14
HEAT_GAP = 3


def create_trophy_tile(pAchievement):
    """Construit la tuile d'un trophée : obtenu en couleur, à venir grisé avec son avancée."""

    vUnlocked = pAchievement["unlocked"]
    vColor, vBackground = (
        ACCENTS["amber"] if vUnlocked else (COLORS["muted"], COLORS["surface_alt"])
    )

    rTile = QFrame()
    rTile.setObjectName("trophyTile")
    rTile.setStyleSheet(
        f"QFrame#trophyTile {{ background: {vBackground}; border-radius: 12px; }}"
    )

    vTitle = QLabel(pAchievement["title"])
    vTitle.setWordWrap(True)
    vTitle.setStyleSheet(
        f"color: {vColor if vUnlocked else COLORS['text']}; font-weight: 700;"
    )

    vDescription = QLabel(pAchievement["description"])
    vDescription.setObjectName("cardSubtitle")
    vDescription.setWordWrap(True)

    if vUnlocked:
        vState = "Obtenu le " + date.fromisoformat(
            pAchievement["unlocked_on"]
        ).strftime("%d/%m/%Y")
    elif pAchievement["hidden"]:
        vState = ""
    else:
        vState = f"{pAchievement['progress']} / {pAchievement['target']}"

    vStateLabel = QLabel(vState)
    vStateLabel.setObjectName("cardSubtitle")

    vTop = QHBoxLayout()
    vTop.setSpacing(8)
    vTop.addWidget(create_icon_label(pAchievement["icon"], vColor, 22))
    vTop.addWidget(vTitle, 1)

    vLayout = QVBoxLayout(rTile)
    vLayout.setContentsMargins(12, 10, 12, 10)
    vLayout.setSpacing(4)
    vLayout.addLayout(vTop)
    vLayout.addWidget(vDescription)
    vLayout.addWidget(vStateLabel)

    return rTile


class Heatmap(QWidget):
    """Carte d'activité : une case par jour, une colonne par semaine, plus foncée
    quand la journée a rapporté plus de points."""

    def __init__(self):
        """Crée une carte vide ; set_days la remplit."""
        super().__init__()

        self.days = []
        self.setFixedHeight(7 * (HEAT_CELL + HEAT_GAP) + 4)

    def set_days(self, pDays):
        """Remplace les jours affichés : dicts {day, xp}, xp à None pour un jour futur."""
        self.days = pDays
        self.setToolTip(
            "Plus la case est foncée, plus la journée a rapporté de points. "
            f"Total sur la période : {sum(vDay['xp'] or 0 for vDay in pDays)} XP"
        )
        self.update()

    def paintEvent(self, _pEvent):  # pylint: disable=invalid-name
        """Dessine les cases, du lundi en haut au dimanche en bas."""
        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vPainter.setPen(Qt.PenStyle.NoPen)
        vGreen = QColor(ACCENTS["green"][0])

        for vIndex, vDay in enumerate(self.days):
            if vDay["xp"] is None:
                continue

            vLevel = get_heat_level(vDay["xp"])
            vColor = QColor(COLORS["border"]) if not vLevel else QColor(vGreen)

            if vLevel:
                vColor.setAlphaF(0.25 + 0.1875 * vLevel)

            vPainter.setBrush(vColor)
            vPainter.drawRoundedRect(
                vIndex // 7 * (HEAT_CELL + HEAT_GAP),
                vIndex % 7 * (HEAT_CELL + HEAT_GAP),
                HEAT_CELL,
                HEAT_CELL,
                3,
                3,
            )

        vPainter.end()


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

        vTrophyCard, vTrophyLayout = create_card(
            "Trophées",
            "Certains restent cachés jusqu'à leur obtention",
            pIcon="award",
            pKey="progress-trophies",
            pOpen=True,
        )
        self.trophy_count_label = vTrophyCard.findChild(QLabel, "cardTitle")
        self.trophy_grid = QGridLayout()
        self.trophy_grid.setSpacing(12)
        vTrophyLayout.addLayout(self.trophy_grid)

        vPlayerCard, vPlayerLayout = create_card(
            "Carte joueur",
            f"Records et points gagnés jour par jour sur {HEATMAP_WEEKS} semaines",
            pIcon="user",
            pKey="progress-player",
        )
        self.heatmap = Heatmap()
        self.records_layout = QGridLayout()
        self.records_layout.setSpacing(12)
        vPlayerLayout.addWidget(self.heatmap)
        vPlayerLayout.addLayout(self.records_layout)

        vLayout.addWidget(vBanner)
        vLayout.addLayout(vCards)
        vLayout.addWidget(vQuestCard)
        vLayout.addWidget(vTrophyCard)
        vLayout.addWidget(vPlayerCard)
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

        vAchievements = pProgress["achievements"]
        self.trophy_count_label.setText(
            f"Trophées · {pProgress['achievement_count']} sur {len(vAchievements)}"
        )
        clear_layout(self.trophy_grid)

        # Les trophées obtenus d'abord, les plus récents en tête
        vSorted = sort_achievements(vAchievements)

        for vIndex, vAchievement in enumerate(vSorted):
            self.trophy_grid.addWidget(
                create_trophy_tile(vAchievement),
                vIndex // TROPHY_COLUMNS,
                vIndex % TROPHY_COLUMNS,
            )

        self.heatmap.set_days(pProgress["player"]["heatmap"])
        clear_layout(self.records_layout)

        for vIndex, vRecord in enumerate(pProgress["player"]["records"]):
            vValue = QLabel(str(vRecord["value"]))
            vValue.setStyleSheet(
                f"color: {ACCENTS['blue'][0]}; font-size: 18px; font-weight: 800;"
            )
            vLabel = QLabel(vRecord["label"])
            vLabel.setObjectName("cardSubtitle")
            vHolder = QWidget()
            vRecordLayout = QVBoxLayout(vHolder)
            vRecordLayout.setContentsMargins(0, 0, 0, 0)
            vRecordLayout.setSpacing(0)
            vRecordLayout.addWidget(vValue)
            vRecordLayout.addWidget(vLabel)
            self.records_layout.addWidget(vHolder, vIndex // 3, vIndex % 3)

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
