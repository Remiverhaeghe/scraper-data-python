"""Page Maven et Docker : corriger un pom.xml ou un Dockerfile, lancer les commandes"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    StatisticCard,
    TileButton,
    add_tile_group,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    show_message,
)
from job.devops_levels import (
    build_devops_overview,
    get_level_view,
    reset_level,
    run_level_command,
)
from job.progress import XP_RULES
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
CONSOLE_STYLE = (
    "QPlainTextEdit { background: #0f172a; color: #e2e8f0; border-radius: 8px; }"
)
USEFUL_COMMANDS = {
    "maven": "mvn compile · mvn test · mvn package · mvn clean package · "
    "mvn dependency:tree",
    "docker": "docker build -t NOM . · docker run -d --name N -p HÔTE:CONTENEUR "
    "IMAGE · docker ps -a · docker logs N · docker rm -f N · "
    "curl http://localhost:PORT/",
}


def create_code_editor(pReadOnly=False):
    """Crée une zone de texte à police fixe, en lecture seule pour la console."""

    rEditor = QPlainTextEdit()
    rEditor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    rEditor.setReadOnly(pReadOnly)
    rEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    if pReadOnly:
        rEditor.setStyleSheet(CONSOLE_STYLE)

    return rEditor


class DevopsPage(QWidget):
    """Niveaux Maven et Docker, joués dans une console simulée."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit la progression."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.level = None
        self.tiles = {}

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Maven et Docker",
            "Corrigez un pom.xml ou un Dockerfile, puis lancez les commandes dans une "
            "console simulée : rien n'est exécuté sur la machine",
            pIcon="server",
        )

        self.passed_card = StatisticCard("Niveaux réussis", "server", "blue")
        vCards = QHBoxLayout()
        vCards.addWidget(self.passed_card)
        vCards.addStretch(3)

        self.choice_card, vChoiceLayout = create_card(
            "Choisir un niveau",
            f"Chaque niveau réussi rapporte {XP_RULES['devops_level'][1]} XP",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.level_card, vLevelLayout = create_card(
            "Niveau", pIcon="terminal", pOpen=True
        )
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.goal_label = QLabel()
        self.goal_label.setWordWrap(True)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("cardSubtitle")
        self.file_label = QLabel()
        self.file_label.setObjectName("fieldLabel")
        self.editor = create_code_editor()
        self.editor.setMinimumHeight(260)

        self.commands_label = QLabel()
        self.commands_label.setWordWrap(True)
        self.commands_label.setObjectName("cardSubtitle")
        self.command_edit = QLineEdit()
        self.command_edit.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.command_edit.setPlaceholderText("Commande, puis Entrée")
        self.command_edit.setMaxLength(300)
        self.command_edit.returnPressed.connect(self.run_command)
        vRunButton = create_button("Exécuter", "terminal", "primaryButton", "#FFFFFF")
        vRunButton.clicked.connect(self.run_command)
        vCommandRow = QHBoxLayout()
        vCommandRow.addWidget(self.command_edit, 1)
        vCommandRow.addWidget(vRunButton)

        self.console = create_code_editor(True)
        self.console.setMinimumHeight(280)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.RichText)

        vHintButton = create_button("Indice", pObjectName="linkButton")
        vHintButton.clicked.connect(lambda: self.hint_label.setVisible(True))
        vSolutionButton = create_button("Voir la solution", pObjectName="linkButton")
        vSolutionButton.clicked.connect(self.show_solution)
        vResetButton = create_button("Recommencer", pObjectName="linkButton")
        vResetButton.clicked.connect(self.reset)
        vBackButton = create_button("Choisir un autre niveau", pObjectName="linkButton")
        vBackButton.clicked.connect(self.show_choices)
        vButtons = QHBoxLayout()

        for vButton in (vHintButton, vSolutionButton, vResetButton, vBackButton):
            vButtons.addWidget(vButton)

        vButtons.addStretch()

        for vWidget in (
            self.title_label,
            self.goal_label,
            self.hint_label,
            self.file_label,
            self.editor,
            self.commands_label,
        ):
            vLevelLayout.addWidget(vWidget)

        vLevelLayout.addLayout(vCommandRow)
        vLevelLayout.addWidget(self.console)
        vLevelLayout.addWidget(self.status_label)
        vLevelLayout.addLayout(vButtons)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.level_card)
        vLayout.addStretch()

        self.level_card.hide()

    def refresh(self):
        """Relit les niveaux réussis et remplit les tuiles par série."""

        try:
            vOverview = build_devops_overview(self.database_file)

        except Exception:
            logger.exception("Progression Maven et Docker non lue")
            show_message(
                self.message_label, "La progression n'a pas pu être lue.", "danger"
            )
            return

        self.passed_card.set_value(f"{vOverview['passed']} / {vOverview['total']}")
        clear_layout(self.tiles_layout)
        self.tiles = {}
        vRow = 0

        for vSeries in vOverview["series"]:
            vTiles = []

            for vLevel in vSeries["rows"]:
                vTile = TileButton(
                    vLevel["title"],
                    vLevel["goal"],
                    vSeries["icon"],
                    "green" if vLevel["passed"] else "blue",
                    (
                        "Réussi"
                        if vLevel["passed"]
                        else ("Commencé" if vLevel["started"] else "")
                    ),
                )
                vTile.set_done(vLevel["passed"])
                vTile.clicked.connect(lambda pId=vLevel["id"]: self.open_level(pId))
                self.tiles[vLevel["id"]] = vTile
                vTiles.append(vTile)

            vRow = add_tile_group(
                self.tiles_layout,
                vRow,
                f"{vSeries['label']} · {vSeries['done']} / {len(vTiles)} réussi(s)",
                vSeries["icon"],
                vTiles,
                TILE_COLUMNS,
            )

    def open_level(self, pLevelId):
        """Affiche un niveau là où on l'avait laissé : fichier et console."""

        vView = get_level_view(self.database_file, pLevelId)
        self.level = vView["level"]
        self.title_label.setText(self.level["title"])
        self.goal_label.setText(self.level["goal"])
        self.hint_label.setText(f"Indice : {self.level['hint']}")
        self.hint_label.hide()
        self.file_label.setText(vView["file_name"])
        self.editor.setPlainText(vView["file"])
        self.commands_label.setText(
            f"Commandes utiles : {USEFUL_COMMANDS[self.level['tool']]}"
        )
        self.console.setPlainText("\n".join(vView["console"]))
        self.show_status(vView["passed"], False, "")
        self.choice_card.hide()
        self.level_card.show()
        self.command_edit.setFocus()

    def show_status(self, pReached, pFirst, pMessage):
        """Affiche l'état de l'objectif sous la console."""

        if pReached:
            vXp = f" · +{XP_RULES['devops_level'][1]} XP" if pFirst else ""
            self.status_label.setText(
                f"<b>Objectif atteint{vXp}</b><br>{self.level['explanation']}"
            )
        else:
            self.status_label.setText(pMessage)

    def run_command(self):
        """Exécute la commande saisie et ajoute sa sortie à la console."""

        if self.level is None:
            return

        vCommand = self.command_edit.text()

        try:
            vRun = run_level_command(
                self.database_file,
                self.level["id"],
                self.editor.toPlainText(),
                vCommand,
            )

        except Exception:
            logger.exception("Commande Maven ou Docker non exécutée")
            show_message(
                self.status_label, "La commande n'a pas pu être exécutée.", "danger"
            )
            return

        if vCommand.strip():
            self.console.appendPlainText(
                "\n".join([f"$ {vCommand.strip()}"] + vRun["lines"])
            )
            self.command_edit.clear()

        self.show_status(vRun["reached"], vRun["first"], vRun["message"])

        if vRun["first"]:
            self.refresh()

    def show_solution(self):
        """Remplace le fichier par la solution et propose les commandes à lancer."""

        self.editor.setPlainText(self.level["solution"])
        self.hint_label.setText(
            "Commandes de la solution : " + " · ".join(self.level["commands"])
        )
        self.hint_label.show()

    def reset(self):
        """Remet le niveau à son départ."""

        reset_level(self.database_file, self.level["id"])
        self.open_level(self.level["id"])

    def show_choices(self):
        """Revient au choix d'un niveau."""

        self.level_card.hide()
        self.choice_card.show()
        self.refresh()
