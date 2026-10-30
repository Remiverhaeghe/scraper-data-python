"""Page du simulateur d'automate : écrire un programme ladder, le tester, le voir agir"""

from html import escape

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.ladder_machine import MachineView
from gui.theme import COLORS
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
from job.ladder import LadderError, parse_program, render_svg
from job.ladder_game import (
    CYCLE_SECONDS,
    Simulator,
    build_ladder_overview,
    get_level,
    get_names,
    get_sensor_names,
    render_chronogram,
    run_level,
    save_attempt,
)
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
CYCLE_MILLISECONDS = int(CYCLE_SECONDS * 1000)

# Le dessin ladder est redessiné tous les N cycles : assez pour suivre à l'œil
DRAW_EVERY = 3


def show_svg(pWidget, pSvg):
    """Affiche un SVG à sa taille naturelle dans un QSvgWidget."""

    pWidget.load(QByteArray(pSvg.encode("utf-8")))
    vSize = pWidget.renderer().defaultSize()
    pWidget.setFixedSize(vSize)


def format_result(pPassed, pText):
    """Retourne une vérification en texte riche : verte réussie, rouge sinon."""

    vColor = COLORS["success"] if pPassed else COLORS["danger"]
    vState = "réussi" if pPassed else "à revoir"

    rHtml = f'<span style="color: {vColor}; font-weight: 600;">{vState}</span> · {escape(pText)}'

    return rHtml


class LadderPage(QWidget):
    """Niveaux d'automatisme : marche-arrêt, temporisation, comptage, Grafcet."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit la progression."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.level = None
        self.simulator = None
        self.input_buttons = {}

        self.timer = QTimer(self)
        self.timer.setInterval(CYCLE_MILLISECONDS)
        self.timer.timeout.connect(self.step)

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Simulateur d'automate",
            "Écrivez un programme en ladder, vérifiez-le sur un scénario de test, "
            "puis pilotez la machine à la souris",
            pIcon="cpu",
        )

        self.passed_card = StatisticCard("Niveaux réussis", "cpu", "blue")
        vCards = QHBoxLayout()
        vCards.addWidget(self.passed_card)
        vCards.addStretch(3)

        self.choice_card, vChoiceLayout = create_card(
            "Choisir un niveau",
            "Du plus simple au plus complet : chaque niveau réussi rapporte 25 XP",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.level_card, vLevelLayout = create_card("Niveau", pIcon="cpu", pOpen=True)
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.goal_label = QLabel()
        self.goal_label.setWordWrap(True)
        self.variables_label = QLabel()
        self.variables_label.setWordWrap(True)
        self.variables_label.setTextFormat(Qt.TextFormat.RichText)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("cardSubtitle")

        self.editor = QPlainTextEdit()
        self.editor.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.editor.setMinimumHeight(180)
        self.editor.textChanged.connect(self.draw_program)

        self.ladder_view = QSvgWidget()
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)

        vCheckButton = create_button(
            "Vérifier", "circle-check", "primaryButton", "#FFFFFF"
        )
        vCheckButton.clicked.connect(self.check_program)
        vHintButton = create_button("Indice", pObjectName="linkButton")
        vHintButton.clicked.connect(lambda: self.hint_label.setVisible(True))
        vSolutionButton = create_button("Voir la solution", pObjectName="linkButton")
        vSolutionButton.clicked.connect(self.show_solution)
        vBackButton = create_button("Choisir un autre niveau", pObjectName="linkButton")
        vBackButton.clicked.connect(self.show_choices)

        vButtons = QHBoxLayout()

        for vButton in (vCheckButton, vHintButton, vSolutionButton, vBackButton):
            vButtons.addWidget(vButton)

        vButtons.addStretch()

        self.results_label = QLabel()
        self.results_label.setWordWrap(True)
        self.results_label.setTextFormat(Qt.TextFormat.RichText)
        self.chart_view = QSvgWidget()

        vSimulationTitle = QLabel("Simulation : appuyez sur les boutons de la machine")
        vSimulationTitle.setObjectName("fieldLabel")
        self.machine_view = MachineView()
        self.inputs_layout = QHBoxLayout()
        self.run_button = create_button("Lancer la simulation", "timer")
        self.run_button.clicked.connect(self.toggle_simulation)

        vEditorColumn = QVBoxLayout()
        vEditorColumn.addWidget(self.editor)
        vEditorColumn.addWidget(self.error_label)
        vEditorColumn.addLayout(vButtons)

        vTop = QHBoxLayout()
        vTop.setSpacing(24)
        vTop.addLayout(vEditorColumn, 1)
        vTop.addWidget(self.ladder_view, 0, Qt.AlignmentFlag.AlignTop)

        vLevelLayout.addWidget(self.title_label)
        vLevelLayout.addWidget(self.goal_label)
        vLevelLayout.addWidget(self.variables_label)
        vLevelLayout.addWidget(self.hint_label)
        vLevelLayout.addLayout(vTop)
        vLevelLayout.addWidget(self.results_label)
        vLevelLayout.addWidget(self.chart_view)
        vLevelLayout.addWidget(vSimulationTitle)
        vLevelLayout.addWidget(self.machine_view)
        vLevelLayout.addLayout(self.inputs_layout)
        vLevelLayout.addWidget(self.run_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.level_card)
        vLayout.addStretch()

        self.level_card.hide()

    def refresh(self):
        """Relit les niveaux réussis et remplit les tuiles."""
        try:
            vOverview = build_ladder_overview(self.database_file)

        except Exception:
            logger.exception("Progression du simulateur d'automate non lue")
            show_message(
                self.message_label, "La progression n'a pas pu être lue.", "danger"
            )
            return

        self.passed_card.set_value(f"{vOverview['passed']} / {len(vOverview['rows'])}")
        clear_layout(self.tiles_layout)

        for vIndex, vRow in enumerate(vOverview["rows"]):
            vTile = TileButton(
                f"{vIndex + 1}. {vRow['title']}",
                vRow["goal"],
                "cpu",
                "green" if vRow["passed"] else "blue",
                "Réussi" if vRow["passed"] else "",
            )
            vTile.set_done(vRow["passed"])
            vTile.clicked.connect(
                lambda pRow=vRow: self.open_level(pRow["id"], pRow["program"])
            )
            self.tiles_layout.addWidget(
                vTile, vIndex // TILE_COLUMNS, vIndex % TILE_COLUMNS
            )

    def open_level(self, pLevelId, pProgram):
        """Affiche un niveau avec le dernier programme essayé."""
        self.stop_simulation()
        self.level = get_level(pLevelId)

        self.title_label.setText(self.level["title"])
        self.goal_label.setText(self.level["goal"])
        self.variables_label.setText(
            "<br>".join(
                f"<b>{escape(vVariable['name'])}</b> "
                f"({'entrée' if vVariable['kind'] == 'input' else 'sortie'}) : "
                f"{escape(vVariable['label'])}"
                for vVariable in self.level["variables"]
            )
        )
        self.hint_label.setText(f"Indice : {self.level['hint']}")
        self.hint_label.hide()
        self.results_label.clear()
        self.chart_view.hide()
        self.editor.setPlainText(pProgram)

        self.build_input_buttons()
        self.choice_card.hide()
        self.level_card.show()

    def build_input_buttons(self):
        """Crée un bouton par entrée de l'opérateur ; les capteurs suivent la machine."""
        clear_layout(self.inputs_layout)
        self.input_buttons = {}
        vSensors = get_sensor_names(self.level)

        for vVariable in self.level["variables"]:
            if vVariable["kind"] != "input" or vVariable["name"] in vSensors:
                continue

            vButton = QPushButton(vVariable["name"])
            vButton.setToolTip(vVariable["label"])
            vButton.setCheckable(vVariable.get("control") == "switch_nc")

            if vButton.isCheckable():
                vButton.setText(f"Déclencher {vVariable['name']}")

            self.input_buttons[vVariable["name"]] = vButton
            self.inputs_layout.addWidget(vButton)

        self.inputs_layout.addStretch()

    def read_operator_inputs(self):
        """Applique au simulateur l'état des boutons de l'opérateur."""
        for vVariable in self.level["variables"]:
            vButton = self.input_buttons.get(vVariable["name"])

            if vButton is None:
                continue

            vPressed = (
                vButton.isChecked() if vButton.isCheckable() else vButton.isDown()
            )
            vControl = vVariable.get("control")

            # Bouton à ouverture et contact de défaut : 1 au repos, 0 actionnés
            self.simulator.set_input(
                vVariable["name"],
                not vPressed if vControl in ("button_nc", "switch_nc") else vPressed,
            )

    def parse_editor(self):
        """Retourne les barreaux de l'éditeur, ou None en affichant l'erreur."""
        try:
            rRungs = parse_program(
                self.editor.toPlainText(), set(get_names(self.level, "input"))
            )

        except LadderError as vException:
            show_message(self.error_label, str(vException), "danger")
            return None

        show_message(self.error_label, "")

        return rRungs

    def draw_program(self):
        """Redessine le ladder à chaque modification du programme."""
        if self.level is None:
            return

        vRungs = self.parse_editor()

        if vRungs is not None:
            show_svg(self.ladder_view, render_svg(vRungs))

    def check_program(self):
        """Exécute le scénario de test et affiche chaque vérification."""
        vProgram = self.editor.toPlainText()
        vRun = run_level(self.level, vProgram)

        if vRun["error"]:
            show_message(self.error_label, vRun["error"], "danger")
            return

        try:
            vFirst = save_attempt(
                self.database_file, self.level["id"], vProgram, vRun["passed"]
            )

        except Exception:
            logger.exception("Programme d'automate non enregistré")
            vFirst = False

        vLines = [
            format_result(vCheck["passed"], f"{vCheck['at']:g} s : {vCheck['message']}")
            for vCheck in vRun["checks"]
        ] + [format_result(False, vMessage) for vMessage in vRun["violations"]]

        self.results_label.setText(
            (
                "<h3>Niveau réussi" + (" · +25 XP" if vFirst else "") + "</h3>"
                if vRun["passed"]
                else "<h3>Pas encore : regardez les vérifications en rouge</h3>"
            )
            + "<br>".join(vLines)
        )
        show_svg(
            self.chart_view,
            render_chronogram(
                vRun["signals"], vRun["samples"], set(get_names(self.level, "input"))
            ),
        )
        self.chart_view.show()

        if vFirst:
            self.refresh()

    def show_solution(self):
        """Remplace le programme par la solution commentée du niveau."""
        self.editor.setPlainText(self.level["solution"])

    def toggle_simulation(self):
        """Lance ou arrête la simulation interactive."""
        if self.timer.isActive():
            self.stop_simulation()
            return

        vRungs = self.parse_editor()

        if vRungs is None:
            return

        self.simulator = Simulator(self.level, vRungs)
        self.run_button.setText("Arrêter la simulation")
        self.timer.start()

    def stop_simulation(self):
        """Arrête la simulation interactive."""
        self.timer.stop()
        self.run_button.setText("Lancer la simulation")

    def step(self):
        """Un cycle d'automate : boutons, programme, machine, puis dessin."""
        self.read_operator_inputs()
        self.simulator.step()
        self.machine_view.set_state(
            self.level, dict(self.simulator.values), dict(self.simulator.machine)
        )

        if self.simulator.cycle % DRAW_EVERY == 0:
            show_svg(
                self.ladder_view,
                render_svg(self.simulator.rungs, self.simulator.values),
            )

    def show_choices(self):
        """Revient au choix d'un niveau."""
        self.stop_simulation()
        self.level_card.hide()
        self.choice_card.show()
        self.refresh()

    def hideEvent(self, pEvent):  # pylint: disable=invalid-name
        """Arrête la simulation quand on quitte la page."""
        self.stop_simulation()
        super().hideEvent(pEvent)
