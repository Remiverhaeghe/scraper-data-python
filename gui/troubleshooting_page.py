"""Page des pannes à résoudre : choix d'un scénario, mesures, réparation"""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    StatisticCard,
    TileButton,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.troubleshooting import (
    CHECK_PREFIX,
    REPAIR_PREFIX,
    build_overview,
    play,
    save_result,
)
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
BUTTON_HEIGHT = 36
STAR = "★"
EMPTY_STAR = "☆"

# Couleur de la tuile d'un scénario selon ses étoiles
STAR_ACCENTS = {0: "blue", 1: "purple", 2: "amber", 3: "green"}


def format_stars(pStars):
    """Retourne trois étoiles, pleines selon le score."""

    rText = STAR * pStars + EMPTY_STAR * (3 - pStars)

    return rText


def format_log_entry(pEntry):
    """Retourne une ligne du journal d'intervention en texte riche."""

    vMinutes = f" · {pEntry['minutes']} min" if pEntry["minutes"] else ""

    rHtml = f"<b>{escape(pEntry['label'])}</b>{vMinutes}<br>{escape(pEntry['result'])}"

    return rHtml


class TroubleshootingPage(QWidget):
    """Diagnostic de pannes : chaque mesure coûte du temps, chaque erreur aussi."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit les scores."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.scenario_id = None
        self.actions = []

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Pannes à résoudre",
            "Choisissez vos mesures, trouvez la cause : chaque mesure coûte du temps, "
            "chaque pièce changée pour rien aussi",
            pIcon="wrench",
        )

        self.cards = {
            "solved": StatisticCard("Pannes résolues", "wrench", "blue"),
            "stars": StatisticCard("Étoiles", "star", "amber"),
        }
        vCards = QHBoxLayout()
        vCards.setSpacing(16)

        for vCard in self.cards.values():
            vCards.addWidget(vCard)

        vCards.addStretch()

        self.choice_card, vChoiceLayout = create_card(
            "Choisir une panne",
            "Trois étoiles en trouvant la cause aussi vite qu'un technicien expérimenté, "
            "sans changer de pièce pour rien",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.game_card, vGameLayout = create_card(
            "Intervention", pIcon="wrench", pOpen=True
        )
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.title_label.setWordWrap(True)
        self.context_label = QLabel()
        self.context_label.setWordWrap(True)
        self.status_label = QLabel()
        self.status_label.setObjectName("cardSubtitle")

        self.checks_title = QLabel("Mesures et contrôles")
        self.checks_title.setObjectName("fieldLabel")
        self.checks_layout = QVBoxLayout()
        self.checks_layout.setSpacing(6)
        self.repairs_title = QLabel("Réparer")
        self.repairs_title.setObjectName("fieldLabel")
        self.repairs_layout = QVBoxLayout()
        self.repairs_layout.setSpacing(6)

        vActions = QVBoxLayout()
        vActions.addWidget(self.checks_title)
        vActions.addLayout(self.checks_layout)
        vActions.addWidget(self.repairs_title)
        vActions.addLayout(self.repairs_layout)
        vActions.addStretch()

        vLogTitle = QLabel("Journal d'intervention")
        vLogTitle.setObjectName("fieldLabel")
        self.log_layout = QVBoxLayout()
        self.log_layout.setSpacing(8)

        vLog = QVBoxLayout()
        vLog.addWidget(vLogTitle)
        vLog.addLayout(self.log_layout)
        vLog.addStretch()

        vColumns = QHBoxLayout()
        vColumns.setSpacing(24)
        vColumns.addLayout(vActions, 1)
        vColumns.addLayout(vLog, 1)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextFormat(Qt.TextFormat.RichText)

        self.again_button = create_button(
            "Rejouer cette panne", "wrench", "primaryButton", "#FFFFFF"
        )
        self.again_button.clicked.connect(lambda: self.start_scenario(self.scenario_id))
        vBackButton = create_button("Choisir une autre panne", pObjectName="linkButton")
        vBackButton.clicked.connect(self.show_choices)

        vButtons = QHBoxLayout()
        vButtons.addWidget(self.again_button)
        vButtons.addWidget(vBackButton)
        vButtons.addStretch()

        vGameLayout.addWidget(self.title_label)
        vGameLayout.addWidget(self.context_label)
        vGameLayout.addWidget(self.status_label)
        vGameLayout.addLayout(vColumns)
        vGameLayout.addWidget(self.result_label)
        vGameLayout.addLayout(vButtons)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.game_card)
        vLayout.addStretch()

        self.game_card.hide()

    def refresh(self):
        """Relit les meilleurs scores et remplit les tuiles."""
        try:
            vOverview = build_overview(self.database_file)

        except Exception:
            logger.exception("Scores des pannes non lus")
            show_message(
                self.message_label, "Les scores n'ont pas pu être lus.", "danger"
            )
            return

        self.cards["solved"].set_value(
            f"{vOverview['solved']} / {len(vOverview['rows'])}"
        )
        self.cards["stars"].set_value(
            f"{vOverview['stars']} / {vOverview['max_stars']}"
        )

        clear_layout(self.tiles_layout)

        for vIndex, vRow in enumerate(vOverview["rows"]):
            vTile = TileButton(
                vRow["title"],
                f"{vRow['domain']} · {vRow['symptom']}",
                "wrench",
                STAR_ACCENTS[vRow["stars"]],
                format_stars(vRow["stars"]) if vRow["attempts"] else "",
            )
            vTile.set_done(vRow["stars"] == 3)
            vTile.clicked.connect(lambda pId=vRow["id"]: self.start_scenario(pId))
            self.tiles_layout.addWidget(
                vTile, vIndex // TILE_COLUMNS, vIndex % TILE_COLUMNS
            )

    def start_scenario(self, pScenarioId):
        """Commence une intervention sur une panne, journal vide."""
        self.scenario_id = pScenarioId
        self.actions = []

        self.choice_card.hide()
        self.game_card.show()
        show_message(self.message_label, "")

        self.render(play(pScenarioId, self.actions))

    def act(self, pAction):
        """Joue une mesure ou une réparation, puis affiche le nouvel état."""
        self.actions.append(pAction)
        vState = play(self.scenario_id, self.actions)

        if vState["solved"]:
            try:
                vXp = save_result(self.database_file, vState)

            except Exception:
                logger.exception("Panne résolue non enregistrée")
                show_message(
                    self.message_label,
                    "Le résultat n'a pas pu être enregistré.",
                    "danger",
                )
                vXp = 0

            vState["xp"] = vXp
            self.refresh()

        self.render(vState)

    def render(self, pState):
        """Affiche le scénario, les actions encore possibles et le journal."""
        vScenario = pState["scenario"]

        self.title_label.setText(f"{vScenario['title']} · {vScenario['domain']}")
        self.context_label.setText(f"{vScenario['symptom']}\n\n{vScenario['machine']}")
        self.status_label.setText(
            f"Temps passé : {pState['minutes']} min · pièces changées pour rien : "
            f"{len(pState['wrong'])}"
        )

        for vLayout in (self.checks_layout, self.repairs_layout, self.log_layout):
            clear_layout(vLayout)

        if not pState["solved"]:
            for vCheck in vScenario["checks"]:
                if vCheck["id"] in pState["done"]:
                    continue

                vButton = create_button(
                    f"{vCheck['label']} · {vCheck['minutes']} min", "search"
                )
                vButton.clicked.connect(
                    lambda _=False, pId=vCheck["id"]: self.act(CHECK_PREFIX + pId)
                )
                vButton.setMinimumHeight(BUTTON_HEIGHT)
                self.checks_layout.addWidget(vButton)

            for vCause in vScenario["causes"]:
                if vCause["id"] in pState["wrong"]:
                    continue

                vButton = create_button(
                    f"{vCause['label']} · {vCause['minutes']} min", "wrench"
                )
                vButton.clicked.connect(
                    lambda _=False, pId=vCause["id"]: self.act(REPAIR_PREFIX + pId)
                )
                vButton.setMinimumHeight(BUTTON_HEIGHT)
                self.repairs_layout.addWidget(vButton)

        for vEntry in reversed(pState["log"]):
            vLabel = QLabel(format_log_entry(vEntry))
            vLabel.setTextFormat(Qt.TextFormat.RichText)
            vLabel.setWordWrap(True)
            self.log_layout.addWidget(vLabel)

        if not pState["log"]:
            vLabel = QLabel("Aucune action pour l'instant : par quoi commencez-vous ?")
            vLabel.setObjectName("cardSubtitle")
            self.log_layout.addWidget(vLabel)

        self.checks_title.setVisible(not pState["solved"])
        self.repairs_title.setVisible(not pState["solved"])
        self.result_label.setVisible(pState["solved"])
        self.again_button.setVisible(pState["solved"])

        if pState["solved"]:
            self.result_label.setText(
                f"<h3>{format_stars(pState['stars'])} {pState['score']} / 100 · "
                f"+{pState.get('xp', 0)} XP</h3>"
                + (
                    ""
                    if pState["proven"]
                    else "<p>Score plafonné : la réparation a été faite sans mesure "
                    "qui prouve la cause.</p>"
                )
                + f"<p>{escape(vScenario['explanation'])}</p>"
            )

    def show_choices(self):
        """Revient au choix d'une panne, avec les scores à jour."""
        self.game_card.hide()
        self.choice_card.show()
        self.refresh()
