"""Page du bac à sable SQL : requêtes sur une base d'atelier, en MySQL ou SQL Server"""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
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
from job.progress import XP_RULES
from job.sql_levels import (
    build_schema,
    build_sql_overview,
    get_level,
    pick,
    run_level,
    save_attempt,
    save_dialect,
)
from job.sql_sandbox import DIALECTS, MAX_ROWS, format_value
from utils.logger import get_logger

logger = get_logger(__name__)

TILE_COLUMNS = 3
TABLE_HEIGHT = 260


def create_result_table():
    """Crée un tableau de résultat en lecture seule."""

    rTable = QTableWidget(0, 0)
    rTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    rTable.verticalHeader().hide()
    rTable.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    rTable.setMinimumHeight(TABLE_HEIGHT)

    return rTable


def fill_result_table(pTable, pResult):
    """Remplace le contenu d'un tableau par les colonnes et lignes d'un résultat."""

    pTable.clear()
    pTable.setColumnCount(len(pResult["columns"]))
    pTable.setHorizontalHeaderLabels(pResult["columns"])
    pTable.setRowCount(len(pResult["rows"]))

    for vRowIndex, vRow in enumerate(pResult["rows"]):
        for vColumn, vValue in enumerate(vRow):
            pTable.setItem(vRowIndex, vColumn, QTableWidgetItem(format_value(vValue)))


def describe_result(pResult):
    """Retourne la légende d'un résultat : lignes lues ou modifiées."""

    vParts = []

    if pResult["changed"] is not None:
        vParts.append(f"{pResult['changed']} ligne(s) modifiée(s)")

    vParts.append(
        f"{MAX_ROWS} premières lignes"
        if pResult["truncated"]
        else f"{len(pResult['rows'])} ligne(s)"
    )

    rText = " · ".join(vParts)

    return rText


def format_schema(pSchema):
    """Retourne les tables de la base en texte riche : nom, rôle et colonnes."""

    rHtml = "<br>".join(
        f"<b>{escape(vTable['name'])}</b> ({escape(', '.join(vTable['columns']))})"
        f" : {escape(vTable['label'])}"
        for vTable in pSchema
    )

    return rHtml


class SqlPage(QWidget):
    """Niveaux de requêtes, des bases aux fonctions de fenêtre et aux modifications."""

    def __init__(self, pDatabaseFile):
        """Construit la page ; refresh lit la progression."""
        super().__init__()

        self.database_file = pDatabaseFile
        self.level = None
        self.dialect = None
        self.tiles = {}

        vLayout = QVBoxLayout(create_scroll_content(self))
        vLayout.setContentsMargins(32, 28, 32, 28)
        vLayout.setSpacing(18)

        create_page_header(
            vLayout,
            "Bac à sable SQL",
            "Des requêtes sur la base d'une usine, en MySQL ou en SQL Server, "
            "comparées au résultat attendu",
            pIcon="database",
        )

        self.passed_card = StatisticCard("Niveaux réussis", "database", "blue")
        self.dialect_combo = QComboBox()

        for vKey, vLabel in DIALECTS.items():
            self.dialect_combo.addItem(vLabel, vKey)

        self.dialect_combo.currentIndexChanged.connect(self.change_dialect)
        vDialectLabel = QLabel("Dialecte")
        vDialectLabel.setObjectName("fieldLabel")

        vCards = QHBoxLayout()
        vCards.addWidget(self.passed_card)
        vCards.addStretch(2)
        vCards.addWidget(vDialectLabel)
        vCards.addWidget(self.dialect_combo)

        self.choice_card, vChoiceLayout = create_card(
            "Choisir un niveau",
            f"Chaque niveau réussi rapporte {XP_RULES['sql_level'][1]} XP ; "
            "la base est recréée à chaque requête, rien n'est abîmé",
            pIcon="list-checks",
            pOpen=True,
        )
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(12)
        vChoiceLayout.addLayout(self.tiles_layout)

        self.level_card, vLevelLayout = create_card(
            "Niveau", pIcon="database", pOpen=True
        )
        self.title_label = QLabel()
        self.title_label.setObjectName("offerTitle")
        self.goal_label = QLabel()
        self.goal_label.setWordWrap(True)
        self.schema_label = QLabel(format_schema(build_schema()))
        self.schema_label.setWordWrap(True)
        self.schema_label.setTextFormat(Qt.TextFormat.RichText)
        self.schema_label.setObjectName("cardSubtitle")
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("cardSubtitle")

        self.editor = QPlainTextEdit()
        self.editor.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.editor.setMinimumHeight(160)
        QShortcut(QKeySequence("Ctrl+Return"), self.editor, self.run_query)

        vRunButton = create_button(
            "Exécuter", "circle-check", "primaryButton", "#FFFFFF"
        )
        vRunButton.setToolTip("Ctrl+Entrée")
        vRunButton.clicked.connect(self.run_query)
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

        self.result_caption = QLabel("Votre résultat")
        self.result_caption.setObjectName("fieldLabel")
        self.result_table = create_result_table()
        self.expected_caption = QLabel("Résultat attendu")
        self.expected_caption.setObjectName("fieldLabel")
        self.expected_table = create_result_table()

        vResultColumn = QVBoxLayout()
        vResultColumn.addWidget(self.result_caption)
        vResultColumn.addWidget(self.result_table)
        vExpectedColumn = QVBoxLayout()
        vExpectedColumn.addWidget(self.expected_caption)
        vExpectedColumn.addWidget(self.expected_table)
        vTables = QHBoxLayout()
        vTables.setSpacing(24)
        vTables.addLayout(vResultColumn, 1)
        vTables.addLayout(vExpectedColumn, 1)

        vLevelLayout.addWidget(self.title_label)
        vLevelLayout.addWidget(self.goal_label)
        vLevelLayout.addWidget(self.schema_label)
        vLevelLayout.addWidget(self.hint_label)
        vLevelLayout.addWidget(self.editor)
        vLevelLayout.addLayout(vButtons)
        vLevelLayout.addWidget(self.verdict_label)
        vLevelLayout.addLayout(vTables)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")

        vLayout.addLayout(vCards)
        vLayout.addWidget(self.message_label)
        vLayout.addWidget(self.choice_card)
        vLayout.addWidget(self.level_card)
        vLayout.addStretch()

        self.level_card.hide()

    def refresh(self):
        """Relit le dialecte et les niveaux réussis, puis remplit les tuiles."""

        try:
            vOverview = build_sql_overview(self.database_file)

        except Exception:
            logger.exception("Progression du bac à sable SQL non lue")
            show_message(
                self.message_label, "La progression n'a pas pu être lue.", "danger"
            )
            return

        self.dialect = vOverview["dialect"]
        self.dialect_combo.blockSignals(True)
        self.dialect_combo.setCurrentIndex(self.dialect_combo.findData(self.dialect))
        self.dialect_combo.blockSignals(False)
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
                    "database",
                    "green" if vLevel["passed"] else "blue",
                    "Réussi" if vLevel["passed"] else "",
                )
                vTile.set_done(vLevel["passed"])
                vTile.clicked.connect(
                    lambda pLevel=vLevel: self.open_level(pLevel["id"], pLevel["query"])
                )
                self.tiles[vLevel["id"]] = vTile
                vTiles.append(vTile)

            vRow = add_tile_group(
                self.tiles_layout,
                vRow,
                f"{vSeries['label']} · {vSeries['done']} / {len(vTiles)} réussi(s)",
                "database",
                vTiles,
                TILE_COLUMNS,
            )

    def change_dialect(self):
        """Enregistre le dialecte choisi et met à jour le niveau ouvert."""

        self.dialect = self.dialect_combo.currentData()

        try:
            save_dialect(self.database_file, self.dialect)

        except Exception:
            logger.exception("Dialecte SQL non enregistré")

        if self.level is not None:
            self.show_level_texts()
            self.clear_results()

    def open_level(self, pLevelId, pQuery):
        """Affiche un niveau avec la dernière requête essayée."""

        self.level = get_level(pLevelId)
        self.show_level_texts()
        self.clear_results()
        self.editor.setPlainText(pQuery)
        self.choice_card.hide()
        self.level_card.show()
        self.editor.setFocus()

    def show_level_texts(self):
        """Affiche le titre, l'énoncé et l'indice du niveau dans le dialecte choisi."""

        self.title_label.setText(self.level["title"])
        self.goal_label.setText(self.level["goal"])
        self.hint_label.setText(f"Indice : {pick(self.level, 'hint', self.dialect)}")
        self.hint_label.hide()

    def clear_results(self):
        """Efface le verdict et les tableaux du niveau."""

        self.verdict_label.clear()
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.result_caption.setText("Votre résultat")
        self.expected_table.clear()
        self.expected_table.setRowCount(0)
        self.expected_table.setColumnCount(0)

    def run_query(self):
        """Exécute la requête, l'enregistre, puis affiche verdict et résultats."""

        if self.level is None:
            return

        vQuery = self.editor.toPlainText()
        vRun = run_level(self.level, vQuery, self.dialect)
        vFirst = False

        if not vRun["result"]["error"]:
            try:
                vFirst = save_attempt(
                    self.database_file, self.level["id"], vQuery, vRun["passed"]
                )

            except Exception:
                logger.exception("Requête SQL non enregistrée")

        self.verdict_label.setText(self.format_verdict(vRun, vFirst))
        fill_result_table(self.result_table, vRun["result"])
        self.result_caption.setText(
            f"Votre résultat · {describe_result(vRun['result'])}"
        )
        fill_result_table(self.expected_table, vRun["expected"])

        if vFirst:
            self.refresh()

    def format_verdict(self, pRun, pFirst):
        """Retourne le verdict en texte riche : explication, ou écart et conseils."""

        if pRun["passed"]:
            vXp = f" · +{XP_RULES['sql_level'][1]} XP" if pFirst else ""

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
        """Remplace la requête par la solution du niveau dans le dialecte choisi."""

        self.editor.setPlainText(pick(self.level, "solution", self.dialect))

    def show_choices(self):
        """Revient au choix d'un niveau."""

        self.level_card.hide()
        self.choice_card.show()
        self.refresh()
