"""Page des schémas électriques : montages guidés et mode libre, câblés puis simulés"""

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.ladder_page import show_svg
from gui.schema_editor import SchemaEditor
from gui.theme import COLORS
from gui.widgets import (
    FlowLayout,
    StatisticCard,
    TileButton,
    align_spin_box,
    clear_layout,
    create_button,
    create_card,
    create_page_header,
    create_scroll_content,
    get_exports_folder,
    show_message,
)
from job.circuit import OPERABLE_DEFAULTS, PROTECTIONS, PUSH_BUTTONS, Circuit
from job.circuit_drawing import render_circuit
from job.circuit_levels import (
    FREE_LIMITS,
    build_circuit_overview,
    build_values,
    delete_schema,
    find_schema,
    get_controls,
    get_editable,
    get_level,
    get_solution,
    read_schema,
    run_level,
    save_attempt,
    save_schema,
)
from job.progress import XP_RULES
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3


def format_check(pCheck):
    """Retourne une vérification en texte riche : verte réussie, rouge avec le détail."""

    vColor = COLORS["success"] if pCheck["passed"] else COLORS["danger"]
    vState = "réussi" if pCheck["passed"] else "à revoir"
    vDetails = "".join(
        f"<br>&nbsp;&nbsp;{escape(vText)}" for vText in pCheck["details"]
    )

    rHtml = (
        f'<span style="color: {vColor}; font-weight: 600;">{vState}</span> · '
        f"{escape(pCheck['message'])}{vDetails}"
    )

    return rHtml


class CircuitPage(QWidget):
    """Montages à câbler et à manœuvrer, de la lampe au démarrage moteur."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit la progression."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.level = None
        self.editor = None
        self.limits = {}
        self.value_fields = {}
        self.free_values = {}
        self.circuit = None
        self.inputs = {}
        self.memory = None
        self.control_buttons = {}

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Schémas électriques",
            "Câblez un montage, puis manœuvrez-le : le simulateur calcule courants "
            "et tensions, allume les lampes et signale les défauts",
            pIcon="zap",
        )

        self.passed_card = StatisticCard("Montages réussis", "zap", "blue")
        self.schemas_card = StatisticCard("Schémas enregistrés", "file-text", "green")
        vCards = QHBoxLayout()
        vCards.addWidget(self.passed_card)
        vCards.addWidget(self.schemas_card)
        vCards.addStretch(2)

        self.choice_card, vChoiceLayout = create_card(
            "Choisir un montage",
            f"Chaque montage réussi rapporte {XP_RULES['circuit_level'][1]} XP ; "
            "le mode libre accepte tous les composants",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.work_card, vWorkLayout = create_card("Montage", pIcon="zap", pOpen=True)
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.goal_label = QLabel()
        self.goal_label.setWordWrap(True)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("cardSubtitle")
        self.editor_layout = QVBoxLayout()
        self.values_layout = QFormLayout()

        self.check_button = create_button(
            "Vérifier", "circle-check", "primaryButton", "#FFFFFF"
        )
        self.check_button.clicked.connect(self.check_level)
        vSimulateButton = create_button("Simuler", "zap")
        vSimulateButton.clicked.connect(self.start_simulation)
        self.hint_button = create_button("Indice", pObjectName="linkButton")
        self.hint_button.clicked.connect(lambda: self.hint_label.setVisible(True))
        self.solution_button = create_button(
            "Voir la solution", pObjectName="linkButton"
        )
        self.solution_button.clicked.connect(self.show_solution)
        vBackButton = create_button(
            "Choisir un autre montage", pObjectName="linkButton"
        )
        vBackButton.clicked.connect(self.show_choices)

        vButtons = QHBoxLayout()

        for vButton in (
            self.check_button,
            vSimulateButton,
            self.hint_button,
            self.solution_button,
            vBackButton,
        ):
            vButtons.addWidget(vButton)

        vButtons.addStretch()

        self.free_bar = QWidget()
        vFreeLayout = QHBoxLayout(self.free_bar)
        vFreeLayout.setContentsMargins(0, 0, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom du schéma")
        self.name_edit.setMaxLength(60)
        vSaveButton = create_button("Enregistrer", "download")
        vSaveButton.clicked.connect(self.save_free_schema)
        self.schemas_combo = QComboBox()
        self.schemas_combo.setMinimumWidth(200)
        vOpenButton = create_button("Ouvrir", "file-text")
        vOpenButton.clicked.connect(
            lambda: self.open_free(self.schemas_combo.currentText())
        )
        vDeleteButton = create_button("Supprimer", "trash-2")
        vDeleteButton.clicked.connect(self.delete_free_schema)
        vExportButton = create_button("Exporter en SVG", "upload")
        vExportButton.clicked.connect(self.export_svg)

        for vWidget in (
            self.name_edit,
            vSaveButton,
            self.schemas_combo,
            vOpenButton,
            vDeleteButton,
            vExportButton,
        ):
            vFreeLayout.addWidget(vWidget)

        vFreeLayout.addStretch()

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.results_label = QLabel()
        self.results_label.setWordWrap(True)
        self.results_label.setTextFormat(Qt.TextFormat.RichText)

        vSimulationTitle = QLabel(
            "Simulation : fils sous tension en rouge, état de chaque composant sous son nom"
        )
        vSimulationTitle.setObjectName("fieldLabel")
        self.controls_layout = FlowLayout()
        self.faults_label = QLabel()
        self.faults_label.setWordWrap(True)
        self.simulation_view = QSvgWidget()
        self.simulation_box = QWidget()
        vSimulationLayout = QVBoxLayout(self.simulation_box)
        vSimulationLayout.setContentsMargins(0, 0, 0, 0)
        vSimulationLayout.addWidget(vSimulationTitle)
        vSimulationLayout.addLayout(self.controls_layout)
        vSimulationLayout.addWidget(self.faults_label)
        vSimulationLayout.addWidget(self.simulation_view)

        vWorkLayout.addWidget(self.title_label)
        vWorkLayout.addWidget(self.goal_label)
        vWorkLayout.addWidget(self.hint_label)
        vWorkLayout.addLayout(self.editor_layout)
        vWorkLayout.addLayout(self.values_layout)
        vWorkLayout.addLayout(vButtons)
        vWorkLayout.addWidget(self.free_bar)
        vWorkLayout.addWidget(self.error_label)
        vWorkLayout.addWidget(self.results_label)
        vWorkLayout.addWidget(self.simulation_box)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.work_card)
        vLayout.addStretch()

        self.work_card.hide()

    def refresh(self):
        """Relit les montages réussis et les schémas enregistrés, puis remplit les tuiles."""

        try:
            vOverview = build_circuit_overview(self.database_file)

        except Exception:
            logger.exception("Progression des schémas électriques non lue")
            show_message(
                self.message_label, "La progression n'a pas pu être lue.", "danger"
            )
            return

        self.passed_card.set_value(f"{vOverview['passed']} / {len(vOverview['rows'])}")
        self.schemas_card.set_value(str(len(vOverview["schemas"])))
        self.schemas_combo.clear()
        self.schemas_combo.addItems(vOverview["schemas"])
        clear_layout(self.tiles_layout)
        vTiles = []

        for vIndex, vRow in enumerate(vOverview["rows"]):
            vTile = TileButton(
                f"{vIndex + 1}. {vRow['title']}",
                vRow["goal"],
                "zap",
                "green" if vRow["passed"] else "blue",
                "Réussi" if vRow["passed"] else "",
            )
            vTile.set_done(vRow["passed"])
            vTile.clicked.connect(lambda pRow=vRow: self.open_level(pRow["id"], pRow))
            vTiles.append(vTile)

        vFreeTile = TileButton(
            "Mode libre",
            "Tous les composants, schémas enregistrés et exportables",
            "pencil",
            "purple",
        )
        vFreeTile.clicked.connect(self.open_free)
        vTiles.append(vFreeTile)

        for vIndex, vTile in enumerate(vTiles):
            self.tiles_layout.addWidget(
                vTile, vIndex // TILE_COLUMNS, vIndex % TILE_COLUMNS
            )

    def build_editor(self, pLimits, pSchema):
        """Remplace l'éditeur par un éditeur de cette palette, chargé du schéma donné."""

        clear_layout(self.editor_layout)
        self.limits = pLimits
        self.editor = SchemaEditor(list(pLimits), pLimits)
        self.editor.load_answer(pSchema)
        self.editor_layout.addWidget(self.editor)

    def build_value_fields(self, pEditable, pValues):
        """Crée un champ par valeur réglable : résistance, tension de pile."""

        while self.values_layout.rowCount():
            self.values_layout.removeRow(0)

        self.value_fields = {}

        for vId, vLabel, (_, vMinimum, vMaximum, vUnit) in pEditable:
            vField = QDoubleSpinBox()
            vField.setRange(vMinimum, vMaximum)
            vField.setDecimals(1)
            vField.setSuffix(f" {vUnit}")
            vField.setValue(pValues.get(vId, vMinimum))
            align_spin_box(vField)
            self.value_fields[vId] = vField
            self.values_layout.addRow(vLabel, vField)

    def open_level(self, pLevelId, pRow=None):
        """Affiche un montage guidé, avec le dernier schéma essayé."""

        self.level = get_level(pLevelId)
        vRow = pRow or {}
        self.title_label.setText(self.level["title"])
        self.goal_label.setText(self.level["goal"])
        self.hint_label.setText(f"Indice : {self.level['hint']}")
        self.hint_label.hide()
        self.build_editor(self.level["palette"], vRow.get("schema"))
        vComponents = [
            {"id": vId, "type": vId.split("-")[0], "x": 0, "y": 0}
            for vId in self.level.get("editable", [])
        ]
        self.build_value_fields(
            get_editable(vComponents, self.level),
            build_values(
                vComponents,
                vRow.get("values"),
                self.level.get("values"),
                self.level.get("editable", []),
            ),
        )
        self.show_work(True)

    def open_free(self, pName=None):
        """Affiche le mode libre, vide ou avec un schéma enregistré."""

        self.level = None
        vSaved = find_schema(self.database_file, pName) if pName else None
        self.title_label.setText(pName or "Mode libre")
        self.goal_label.setText(
            "Posez les composants, reliez leurs bornes, réglez les valeurs puis "
            "simulez. Les contacts de relais suivent la bobine de relais, le contact "
            "du télérupteur suit sa bobine."
        )
        self.hint_label.hide()
        self.free_values = dict((vSaved or {}).get("values") or {})
        self.name_edit.setText(pName or "")
        self.build_editor(FREE_LIMITS, (vSaved or {}).get("schema"))
        self.build_value_fields([], {})
        self.show_work(False)

    def show_work(self, pLevel):
        """Affiche la carte de travail : boutons d'un niveau ou du mode libre."""

        self.check_button.setVisible(pLevel)
        self.hint_button.setVisible(pLevel)
        self.solution_button.setVisible(pLevel)
        self.free_bar.setVisible(not pLevel)
        self.results_label.clear()
        show_message(self.error_label, "")
        self.simulation_box.hide()
        self.choice_card.hide()
        self.work_card.show()

    def read_current(self):
        """Retourne (composants, fils, valeurs) du schéma, ou None en affichant l'erreur."""

        try:
            vComponents, vWires = read_schema(self.editor.get_answer(), self.limits)

        except ValueError as vError:
            show_message(self.error_label, str(vError), "danger")
            return None

        show_message(self.error_label, "")

        if self.level is None:
            self.free_values.update(
                {vId: vField.value() for vId, vField in self.value_fields.items()}
            )
            self.build_value_fields(
                get_editable(vComponents), build_values(vComponents, self.free_values)
            )
            vValues = build_values(vComponents, self.free_values)
        else:
            vValues = build_values(
                vComponents,
                {vId: vField.value() for vId, vField in self.value_fields.items()},
                self.level.get("values"),
                self.level.get("editable", []),
            )

        rCurrent = (vComponents, vWires, vValues)

        return rCurrent

    def check_level(self):
        """Joue les étapes du niveau, enregistre l'essai et montre l'état final."""

        vCurrent = self.read_current()

        if vCurrent is None:
            return

        vComponents, vWires, vValues = vCurrent
        vRun = run_level(self.level, vComponents, vWires, vValues)

        try:
            vFirst = save_attempt(
                self.database_file,
                self.level["id"],
                self.editor.get_answer(),
                vValues,
                vRun["passed"],
            )

        except Exception:
            logger.exception("Montage électrique non enregistré")
            vFirst = False

        vTitle = (
            "<h3>Montage réussi"
            + (f" · +{XP_RULES['circuit_level'][1]} XP" if vFirst else "")
            + f"</h3>{escape(self.level['explanation'])}<br><br>"
            if vRun["passed"]
            else "<h3>Pas encore : regardez les étapes en rouge</h3>"
        )
        self.results_label.setText(
            vTitle + "<br>".join(format_check(vCheck) for vCheck in vRun["checks"])
        )
        self.circuit = Circuit(vComponents, vWires, vValues)
        self.inputs = dict(vRun["inputs"])
        self.memory = vRun["result"]["memory"]
        self.build_controls(vComponents)
        self.render(vRun["result"])

        if vFirst:
            self.refresh()

    def start_simulation(self):
        """Simule le schéma depuis l'état de repos, avec un bouton par commande."""

        vCurrent = self.read_current()

        if vCurrent is None:
            return

        vComponents, vWires, vValues = vCurrent
        self.circuit = Circuit(vComponents, vWires, vValues)
        self.inputs = {}
        self.memory = None
        self.build_controls(vComponents)
        self.step()

    def build_controls(self, pComponents):
        """Crée un bouton par commande : maintenu pour un poussoir, à bascule sinon."""

        clear_layout(self.controls_layout)
        self.control_buttons = {}

        for vId, vType, vLabel in get_controls(pComponents):
            vButton = QPushButton(vLabel)

            if vType in PUSH_BUTTONS:
                vButton.pressed.connect(lambda pId=vId: self.operate(pId, True))
                vButton.released.connect(lambda pId=vId: self.operate(pId, False))
            else:
                vButton.setCheckable(True)
                vButton.setChecked(bool(self.inputs.get(vId, OPERABLE_DEFAULTS[vType])))
                vButton.toggled.connect(
                    lambda pChecked, pId=vId: self.operate(pId, pChecked)
                )

            self.control_buttons[vId] = vButton
            self.controls_layout.addWidget(vButton)

    def operate(self, pId, pValue):
        """Manœuvre une commande ; refermer une protection déclenchée la réarme."""

        if self.circuit is None:
            return

        self.inputs[pId] = pValue

        if pValue and self.circuit.types.get(pId) in PROTECTIONS and self.memory:
            self.memory["tripped"] = [
                vId for vId in self.memory.get("tripped", []) if vId != pId
            ]

        self.step()

    def step(self):
        """Recalcule le circuit pour l'état actuel des commandes et l'affiche."""

        vResult = self.circuit.simulate(self.inputs, self.memory)
        self.memory = vResult["memory"]
        self.render(vResult)

    def render(self, pResult):
        """Affiche le schéma simulé, l'état des commandes et les défauts."""

        vComponents = self.circuit.components
        vWires = self.editor.get_answer()["wires"]
        show_svg(self.simulation_view, render_circuit(vComponents, vWires, pResult))

        for vId, vButton in self.control_buttons.items():
            vLabel = next(
                vControl[2]
                for vControl in get_controls(vComponents)
                if vControl[0] == vId
            )
            vButton.setText(f"{vLabel} : {pResult['parts'][vId]['status']}")

        show_message(
            self.faults_label,
            " ".join(pResult["faults"]),
            "danger" if pResult["faults"] else "success",
        )
        self.simulation_box.show()

    def show_solution(self):
        """Charge la solution du niveau dans l'éditeur, valeurs comprises."""

        vComponents, vWires, vValues = get_solution(self.level)
        self.editor.load_answer({"components": vComponents, "wires": vWires})

        for vId, vField in self.value_fields.items():
            vField.setValue(vValues.get(vId, vField.value()))

    def save_free_schema(self):
        """Enregistre le schéma libre sous le nom saisi."""

        vCurrent = self.read_current()

        if vCurrent is None:
            return

        try:
            save_schema(
                self.database_file,
                self.name_edit.text(),
                self.editor.get_answer(),
                vCurrent[2],
            )

        except ValueError as vError:
            show_message(self.error_label, str(vError), "danger")
            return

        except Exception:
            logger.exception("Schéma électrique non enregistré")
            show_message(
                self.error_label, "Le schéma n'a pas pu être enregistré.", "danger"
            )
            return

        show_message(self.error_label, "Schéma enregistré.")
        self.refresh()
        self.schemas_combo.setCurrentText(" ".join(self.name_edit.text().split()))

    def delete_free_schema(self):
        """Supprime le schéma choisi dans la liste."""

        vName = self.schemas_combo.currentText()

        if vName:
            delete_schema(self.database_file, vName)
            show_message(self.error_label, f"Schéma « {vName} » supprimé.")
            self.refresh()

    def export_svg(self):
        """Enregistre le dessin du schéma dans un fichier SVG choisi."""

        vCurrent = self.read_current()

        if vCurrent is None:
            return

        vName = " ".join(self.name_edit.text().split()) or "schema"
        vPath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le schéma",
            str(Path(get_exports_folder()) / f"{vName}.svg"),
            "Image SVG (*.svg)",
        )

        if not vPath:
            return

        try:
            Path(vPath).write_text(
                render_circuit(vCurrent[0], vCurrent[1], pTitle=vName), encoding="utf-8"
            )

        except OSError:
            logger.exception("Export SVG du schéma impossible")
            show_message(
                self.error_label, "Le fichier n'a pas pu être écrit.", "danger"
            )
            return

        show_message(self.error_label, f"Schéma exporté : {vPath}")

    def show_choices(self):
        """Revient au choix d'un montage."""

        self.work_card.hide()
        self.choice_card.show()
        self.refresh()
