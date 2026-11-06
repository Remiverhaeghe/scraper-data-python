"""Page de l'atelier Excel : formules en français sur une feuille d'usine"""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
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
from job.excel_formula import MAX_FORMULA_LENGTH
from job.excel_levels import (
    build_excel_overview,
    get_level,
    run_level,
    save_attempt,
)
from job.progress import XP_RULES
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
SHEET_HEIGHT = 300
CELLS_HEIGHT = 200


def create_sheet_table(pHeight):
    """Crée un tableau en lecture seule, en-têtes de lignes visibles."""

    rTable = QTableWidget(0, 0)
    rTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    rTable.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    rTable.setMinimumHeight(pHeight)

    return rTable


def fill_sheet(pTable, pGrid, pCells):
    """Affiche la feuille : cibles surlignées, en vert ou en rouge après essai."""

    vStates = {vCell["cell"]: vCell["ok"] for vCell in pCells}
    vTargets = set(pGrid["targets"])
    vBold = QFont()
    vBold.setBold(True)

    pTable.clear()
    pTable.setColumnCount(len(pGrid["columns"]))
    pTable.setHorizontalHeaderLabels(pGrid["columns"])
    pTable.setRowCount(len(pGrid["rows"]))
    pTable.setVerticalHeaderLabels(
        [str(vIndex) for vIndex in range(1, len(pGrid["rows"]) + 1)]
    )

    for vRowIndex, vRow in enumerate(pGrid["rows"]):
        for vColumnIndex, vText in enumerate(vRow):
            vItem = QTableWidgetItem(vText)
            vName = f"{pGrid['columns'][vColumnIndex]}{vRowIndex + 1}"

            if vRowIndex == 0:
                vItem.setFont(vBold)

            if vName in vTargets:
                vColor = {True: "success_light", False: "danger_light"}.get(
                    vStates.get(vName), "primary_light"
                )
                vItem.setBackground(QBrush(QColor(COLORS[vColor])))
                vItem.setForeground(QBrush(QColor(COLORS["heading"])))

            elif vText[:1].isdigit() or vText[:1] == "-":
                vItem.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )

            pTable.setItem(vRowIndex, vColumnIndex, vItem)


def fill_cells(pTable, pCells):
    """Affiche, cellule par cellule, la valeur obtenue et la valeur attendue."""

    pTable.clear()
    pTable.setColumnCount(3)
    pTable.setHorizontalHeaderLabels(["Cellule", "Votre valeur", "Attendu"])
    pTable.verticalHeader().hide()
    pTable.setRowCount(len(pCells))

    for vRowIndex, vCell in enumerate(pCells):
        for vColumnIndex, vText in enumerate(
            (vCell["cell"], vCell["value"], vCell["expected"])
        ):
            vItem = QTableWidgetItem(vText)

            if vColumnIndex == 1:
                vItem.setForeground(
                    QBrush(QColor(COLORS["success" if vCell["ok"] else "danger"]))
                )

            pTable.setItem(vRowIndex, vColumnIndex, vItem)


class ExcelPage(QWidget):
    """Niveaux de formules : références, conditions, recherches, textes et dates."""

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
            "Atelier Excel",
            "Des formules d'Excel en français sur les tableaux d'une usine, "
            "recopiées comme avec la poignée et comparées au résultat attendu",
            pIcon="sheet",
        )

        self.passed_card = StatisticCard("Niveaux réussis", "sheet", "green")
        vCards = QHBoxLayout()
        vCards.addWidget(self.passed_card)
        vCards.addStretch(3)

        self.choice_card, vChoiceLayout = create_card(
            "Choisir un niveau",
            f"Chaque niveau réussi rapporte {XP_RULES['excel_level'][1]} XP ; "
            "les noms de fonctions et le point-virgule sont ceux d'Excel en français",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.level_card, vLevelLayout = create_card("Niveau", pIcon="sheet", pOpen=True)
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.goal_label = QLabel()
        self.goal_label.setWordWrap(True)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("cardSubtitle")

        self.sheet_table = create_sheet_table(SHEET_HEIGHT)

        vFormulaLabel = QLabel("fx")
        vFormulaLabel.setObjectName("fieldLabel")
        self.cell_label = QLabel()
        self.cell_label.setObjectName("fieldLabel")
        self.editor = QLineEdit()
        self.editor.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.editor.setMaxLength(MAX_FORMULA_LENGTH)
        self.editor.setToolTip("Entrée pour valider")
        self.editor.returnPressed.connect(self.run_formula)

        vFormulaBar = QHBoxLayout()
        vFormulaBar.addWidget(self.cell_label)
        vFormulaBar.addWidget(vFormulaLabel)
        vFormulaBar.addWidget(self.editor, 1)

        vRunButton = create_button(
            "Valider", "circle-check", "primaryButton", "#FFFFFF"
        )
        vRunButton.setToolTip("Entrée")
        vRunButton.clicked.connect(self.run_formula)
        vHintButton = create_button("Indice", pObjectName="linkButton")
        vHintButton.clicked.connect(lambda: self.hint_label.setVisible(True))
        vSolutionButton = create_button("Voir la solution", pObjectName="linkButton")
        vSolutionButton.clicked.connect(self.show_solution)
        vBackButton = create_button("Choisir un autre niveau", pObjectName="linkButton")
        vBackButton.clicked.connect(self.show_choices)

        vButtons = QHBoxLayout()

        for vButton in (vRunButton, vHintButton, vSolutionButton, vBackButton):
            vButtons.addWidget(vButton)

        vButtons.addStretch()

        self.verdict_label = QLabel()
        self.verdict_label.setWordWrap(True)
        self.verdict_label.setTextFormat(Qt.TextFormat.RichText)
        self.cells_table = create_sheet_table(CELLS_HEIGHT)

        vLevelLayout.addWidget(self.title_label)
        vLevelLayout.addWidget(self.goal_label)
        vLevelLayout.addWidget(self.sheet_table)
        vLevelLayout.addLayout(vFormulaBar)
        vLevelLayout.addWidget(self.hint_label)
        vLevelLayout.addLayout(vButtons)
        vLevelLayout.addWidget(self.verdict_label)
        vLevelLayout.addWidget(self.cells_table)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.level_card)
        vLayout.addStretch()

        self.level_card.hide()

    def refresh(self):
        """Relit les niveaux réussis, puis remplit les tuiles."""

        try:
            vOverview = build_excel_overview(self.database_file)

        except Exception:
            logger.exception("Progression de l'atelier Excel non lue")
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
                    "sheet",
                    "green",
                    "Réussi" if vLevel["passed"] else "",
                )
                vTile.set_done(vLevel["passed"])
                vTile.clicked.connect(
                    lambda pLevel=vLevel: self.open_level(
                        pLevel["id"], pLevel["formula"]
                    )
                )
                self.tiles[vLevel["id"]] = vTile
                vTiles.append(vTile)

            vRow = add_tile_group(
                self.tiles_layout,
                vRow,
                f"{vSeries['label']} · {vSeries['done']} / {len(vTiles)} réussi(s)",
                "sheet",
                vTiles,
                TILE_COLUMNS,
            )

    def open_level(self, pLevelId, pFormula):
        """Affiche un niveau, sa feuille et la dernière formule essayée."""

        self.level = get_level(pLevelId)
        self.title_label.setText(self.level["title"])
        self.goal_label.setText(self.level["goal"])
        self.hint_label.setText(f"Indice : {self.level['hint']}")
        self.hint_label.hide()
        self.cell_label.setText(self.level["cell"])
        self.editor.setText(pFormula)
        self.show_run(run_level(self.level, ""), False, False)
        self.choice_card.hide()
        self.level_card.show()
        self.editor.setFocus()

    def run_formula(self):
        """Recopie la formule, l'enregistre, puis affiche verdict et feuille."""

        if self.level is None:
            return

        vFormula = self.editor.text().strip()
        vRun = run_level(self.level, vFormula)
        vFirst = False

        if vRun["cells"]:
            try:
                vFirst = save_attempt(
                    self.database_file, self.level["id"], vFormula, vRun["passed"]
                )

            except Exception:
                logger.exception("Formule Excel non enregistrée")

        self.show_run(vRun, True, vFirst)

        if vFirst:
            self.refresh()

    def show_run(self, pRun, pTried, pFirst):
        """Affiche la feuille calculée, le verdict et le détail des cellules."""

        fill_sheet(self.sheet_table, pRun["grid"], pRun["cells"])
        fill_cells(self.cells_table, pRun["cells"])
        self.cells_table.setVisible(bool(pRun["cells"]))
        self.verdict_label.setText(self.format_verdict(pRun, pFirst) if pTried else "")

    def format_verdict(self, pRun, pFirst):
        """Retourne le verdict en texte riche : explication, ou écart et conseils."""

        if pRun["passed"]:
            vXp = f" · +{XP_RULES['excel_level'][1]} XP" if pFirst else ""

            return (
                f'<h3 style="color: {COLORS["success"]};">Niveau réussi{vXp}</h3>'
                f"{escape(self.level['explanation'])}"
            )

        vLines = [
            f'<span style="color: {COLORS["danger"]}; font-weight: 600;">'
            f"{escape(pRun['message'])}</span>"
        ] + [f"Conseil : {escape(vAdvice)}" for vAdvice in pRun["advice"]]

        rHtml = "<br>".join(vLines)

        return rHtml

    def show_solution(self):
        """Remplace la formule par la solution du niveau."""

        self.editor.setText(self.level["solution"])

    def show_choices(self):
        """Revient au choix d'un niveau."""

        self.level_card.hide()
        self.choice_card.show()
        self.refresh()
