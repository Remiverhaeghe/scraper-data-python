"""Page du bac à sable Git : niveaux, commandes simulées et graphe des commits"""

from datetime import datetime
from html import escape

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import (
    TileButton,
    add_tile_group,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.git_levels import (
    build_level_list,
    build_level_view,
    group_levels,
    run_level_command,
)
from job.git_sandbox import SUPPORTED_COMMANDS
from utils.logger import get_logger
from utils.markdown import render_markdown

logger = get_logger(__name__)

LIST_COLUMNS = 3


def format_level(pLevel):
    """Retourne le détail d'un niveau dans la liste : son meilleur résultat."""

    rText = (
        f"Réussi en {pLevel['best']} commande(s), référence {pLevel['par']}"
        if pLevel["best"]
        else f"{pLevel['par']} commande(s) attendue(s)"
    )

    return rText


def create_graph_widget():
    """Crée une zone d'affichage de graphe SVG sur fond blanc."""

    rWidget = QSvgWidget()
    rWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    rWidget.setStyleSheet("background: #ffffff; border-radius: 8px;")

    return rWidget


def load_graph(pWidget, pSvg):
    """Affiche un graphe SVG à sa taille d'origine."""

    pWidget.load(QByteArray(pSvg.encode("utf-8")))
    pWidget.setFixedSize(pWidget.renderer().defaultSize())


class GitPage(QWidget):
    """Liste des niveaux et niveau en cours, joué commande par commande."""

    def __init__(self, pDatabaseFile):
        """Construit la liste et le niveau ; les niveaux sont lus par refresh."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.level_id = None
        self.history = []
        self.level_buttons = {}
        self.next_id = None
        self.view = {}

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(14)

        create_page_header(
            vLayout,
            "Bac à sable Git",
            "Des commandes Git simulées et leur effet sur le graphe des commits, "
            "niveau par niveau",
            pIcon="git-branch",
        )

        self.list_card, vListLayout = create_card(
            "Les niveaux",
            "Atteindre l'objectif, si possible en peu de commandes",
            "list-checks",
            "git-levels",
        )
        self.list_layout = QGridLayout()
        self.list_layout.setSpacing(8)
        vListLayout.addLayout(self.list_layout)

        vLayout.addWidget(self.list_card)
        vLayout.addWidget(self.create_level_card())
        vLayout.addWidget(self.create_help_card())
        vLayout.addStretch(1)

    def create_level_card(self):
        """Construit la présentation, les deux graphes, la saisie et l'historique."""
        self.level_card, vLayout = create_card()

        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.meta_label = QLabel()
        self.meta_label.setObjectName("cardSubtitle")
        self.intro_label = QLabel()
        self.intro_label.setWordWrap(True)

        self.graph_widget = create_graph_widget()
        self.goal_widget = create_graph_widget()
        self.server_widget = create_graph_widget()
        self.goal_server_widget = create_graph_widget()
        # Graphes du serveur, et leurs titres, masqués dans un niveau sans origin
        self.server_parts = []

        vGraphs = QHBoxLayout()

        for vTitle, vWidget, vServerTitle, vServerWidget in (
            ("Votre dépôt", self.graph_widget, "Serveur", self.server_widget),
            (
                "Objectif",
                self.goal_widget,
                "Serveur attendu",
                self.goal_server_widget,
            ),
        ):
            vColumn = QVBoxLayout()

            for vText, vGraph in ((vTitle, vWidget), (vServerTitle, vServerWidget)):
                vLabel = QLabel(vText)
                vLabel.setObjectName("cardSubtitle")
                vColumn.addWidget(vLabel)
                vColumn.addWidget(vGraph)

            self.server_parts += [vLabel, vServerWidget]
            vColumn.addStretch(1)
            vGraphs.addLayout(vColumn)

        vGraphs.addStretch(1)

        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("git commit")
        self.command_edit.returnPressed.connect(self.run_command)
        self.run_button = create_button(
            "Exécuter", "terminal", "primaryButton", COLORS["on_primary"]
        )
        self.run_button.clicked.connect(self.run_command)
        self.undo_button = create_button("Annuler", "history")
        self.undo_button.clicked.connect(self.undo)
        vRestartButton = create_button("Recommencer", "trash-2")
        vRestartButton.clicked.connect(self.restart)

        vCommandRow = QHBoxLayout()
        vCommandRow.addWidget(self.command_edit, 1)
        vCommandRow.addWidget(self.run_button)
        vCommandRow.addWidget(self.undo_button)
        vCommandRow.addWidget(vRestartButton)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.history_label = QLabel()
        self.history_label.setObjectName("cardSubtitle")
        self.history_label.setWordWrap(True)

        self.hint_button = create_button("Afficher un indice", "sparkles")
        self.hint_button.clicked.connect(self.show_hint)
        self.solution_button = create_button("Afficher la solution", "lock")
        self.solution_button.clicked.connect(self.show_solution)
        self.next_button = create_button(
            "Niveau suivant", "arrow-right", "primaryButton", COLORS["on_primary"]
        )
        self.next_button.clicked.connect(self.open_next_level)

        vHelpRow = QHBoxLayout()
        vHelpRow.addWidget(self.hint_button)
        vHelpRow.addWidget(self.solution_button)
        vHelpRow.addStretch(1)
        vHelpRow.addWidget(self.next_button)

        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setObjectName("cardSubtitle")

        for vWidget in (self.title_label, self.meta_label, self.intro_label):
            vLayout.addWidget(vWidget)

        vLayout.addLayout(vGraphs)
        vLayout.addLayout(vCommandRow)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.history_label)
        vLayout.addLayout(vHelpRow)
        vLayout.addWidget(self.help_label)
        self.level_card.hide()

        return self.level_card

    def create_help_card(self):
        """Construit l'aide-mémoire des commandes prises en charge."""
        vCard, vLayout = create_card(
            "Commandes disponibles",
            "Seul l'historique est simulé : aucun fichier n'est touché",
        )
        vLabel = QLabel(
            "<br>".join(
                f"<b>{escape(vSyntax)}</b> : {escape(vRole)}"
                for vSyntax, vRole in SUPPORTED_COMMANDS
            )
        )
        vLabel.setTextFormat(Qt.TextFormat.RichText)
        vLabel.setWordWrap(True)
        vLayout.addWidget(vLabel)

        return vCard

    def refresh(self):
        """Relit les résultats et reconstruit la liste des niveaux."""
        try:
            vLevels = build_level_list(self.database_file)

        except Exception:
            logger.exception("Impossible de charger les niveaux Git")
            return

        clear_layout(self.list_layout)
        self.level_buttons = {}

        vRow = 0

        for vGroup in group_levels(vLevels):
            vTiles = []

            for vLevel in vGroup["levels"]:
                vTile = TileButton(
                    vLevel["title"], format_level(vLevel), vGroup["icon"]
                )
                vTile.set_done(bool(vLevel["best"]))
                vTile.setChecked(vLevel["id"] == self.level_id)
                vTile.clicked.connect(lambda pId=vLevel["id"]: self.open_level(pId))
                self.level_buttons[vLevel["id"]] = vTile
                vTiles.append(vTile)

            vRow = add_tile_group(
                self.list_layout,
                vRow,
                f"{vGroup['label']} · {vGroup['done']} / {len(vTiles)} réussi(s)",
                vGroup["icon"],
                vTiles,
                LIST_COLUMNS,
            )

        if self.level_id:
            self.show_level()

    def open_level(self, pLevelId):
        """Ouvre un niveau depuis son état de départ."""
        self.level_id = pLevelId
        self.history = []
        self.command_edit.clear()
        show_message(self.message_label, "")
        self.help_label.clear()
        self.refresh()

    def show_level(self):
        """Affiche le niveau courant et le graphe après les commandes saisies."""
        vView = build_level_view(self.level_id, self.history)

        for vId, vButton in self.level_buttons.items():
            vButton.setChecked(vId == self.level_id)

        self.title_label.setText(vView["title"])
        self.meta_label.setText(
            f"{vView['series']} · solution de référence en {vView['par']} commande(s)"
        )
        self.intro_label.setText(render_markdown(vView["intro"]))
        load_graph(self.graph_widget, vView["graph"])
        load_graph(self.goal_widget, vView["goal"])

        if vView["server"]:
            load_graph(self.server_widget, vView["server"])
            load_graph(self.goal_server_widget, vView["goal_server"])

        for vWidget in self.server_parts:
            vWidget.setVisible(bool(vView["server"]))
        self.history_label.setText(
            "Commandes : " + " · ".join(vView["history"]) if vView["history"] else ""
        )
        self.command_edit.setEnabled(not vView["done"])
        self.run_button.setEnabled(not vView["done"])
        self.undo_button.setEnabled(bool(vView["history"]) and not vView["done"])
        self.next_button.setVisible(vView["done"] and vView["next_id"] is not None)
        self.next_id = vView["next_id"]
        self.view = vView
        self.level_card.show()

    def run_command(self):
        """Joue la commande saisie sur le dépôt simulé."""
        vHistory, vMessage, vTone = run_level_command(
            self.database_file,
            self.level_id,
            self.history,
            self.command_edit.text(),
            datetime.now(),
        )

        if vHistory != self.history:
            self.command_edit.clear()

        self.history = vHistory

        if vTone == "success":
            self.refresh()
        else:
            self.show_level()

        show_message(self.message_label, vMessage, None if vTone == "info" else vTone)

    def undo(self):
        """Retire la dernière commande jouée."""
        self.history = self.history[:-1]
        show_message(self.message_label, "")
        self.show_level()

    def restart(self):
        """Remet le niveau dans son état de départ."""
        self.open_level(self.level_id)

    def show_hint(self):
        """Affiche l'indice du niveau."""
        self.help_label.setText(f"Indice : {self.view['hint']}")

    def show_solution(self):
        """Affiche la solution de référence du niveau."""
        self.help_label.setText("Solution : " + " · ".join(self.view["solution"]))

    def open_next_level(self):
        """Ouvre le niveau suivant."""
        if self.next_id:
            self.open_level(self.next_id)
