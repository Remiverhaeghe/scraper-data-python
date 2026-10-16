"""Zones de réponse de la révision, selon le type de question (job/quiz_types.py)"""

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPen
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QWidget,
)

from gui.schema_editor import SchemaEditor
from gui.theme import COLORS
from job.quiz_types import BLANK, DEFAULT_TOLERANCE, format_number

MARKER_RADIUS = 9


class ClickableSvgWidget(QSvgWidget):
    """Schéma SVG qui, une fois armé, signale le point cliqué et le marque.

    Le point est rendu dans les coordonnées du dessin SVG d'origine, quelle que
    soit la taille d'affichage : c'est dans ces coordonnées que sont décrites
    les zones des questions.
    """

    clicked = Signal(float, float)

    def __init__(self):
        """Crée un schéma non cliquable, sans point marqué."""
        super().__init__()

        self.clickable = False
        self.point = None

    def set_clickable(self, pClickable, pKeepPoint=False):
        """Active ou non le clic ; le point marqué est effacé, sauf pKeepPoint."""
        self.clickable = pClickable

        if not pKeepPoint:
            self.point = None

        self.setCursor(
            Qt.CursorShape.CrossCursor if pClickable else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def to_drawing(self, pPosition):
        """Convertit une position du widget en coordonnées du dessin SVG."""
        vSize = self.renderer().defaultSize()

        rPoint = (
            pPosition.x() * vSize.width() / max(self.width(), 1),
            pPosition.y() * vSize.height() / max(self.height(), 1),
        )

        return rPoint

    def mousePressEvent(self, pEvent):
        """Retient le point cliqué, en coordonnées du dessin, et le signale."""
        if not self.clickable:
            super().mousePressEvent(pEvent)
            return

        self.point = pEvent.position()
        self.update()
        self.clicked.emit(*self.to_drawing(self.point))

    def paintEvent(self, pEvent):
        """Dessine le schéma, puis le point choisi par-dessus."""
        super().paintEvent(pEvent)

        if self.point is None:
            return

        vPainter = QPainter(self)
        vPainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        vPainter.setPen(QPen(QColor(COLORS["danger"]), 3))
        vPainter.drawEllipse(QPointF(self.point), MARKER_RADIUS, MARKER_RADIUS)
        vPainter.end()


def create_text_answer(pQuestion, pOnSubmit):
    """Crée le champ de saisie d'un calcul ou d'un code à compléter."""
    rEdit = QLineEdit()
    rEdit.returnPressed.connect(pOnSubmit)

    if pQuestion["type"] == "saisie":
        rEdit.setPlaceholderText(f"Ce qui remplace {BLANK}")
        rEdit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    else:
        vUnit = pQuestion.get("unit", "")
        rEdit.setPlaceholderText(f"Votre résultat, par exemple 2,5 {vUnit}")
        rEdit.setToolTip(
            f"Tolérance "
            f"{format_number(pQuestion.get('tolerance', DEFAULT_TOLERANCE))} %"
            + (f", préfixes m, k, µ… acceptés devant {vUnit}" if vUnit else "")
        )

    return rEdit


def create_order_answer(pQuestion):
    """Crée la liste à réordonner par glisser-déposer."""
    rList = QListWidget()
    rList.setDragDropMode(QListWidget.DragDropMode.InternalMove)
    rList.setToolTip("Glissez les éléments pour les remettre dans l'ordre")

    for vIndex, vItem in pQuestion["shuffled"]:
        vListItem = QListWidgetItem(vItem)
        vListItem.setData(Qt.ItemDataRole.UserRole, vIndex)
        rList.addItem(vListItem)

    rList.setFixedHeight(rList.sizeHintForRow(0) * rList.count() + 8)

    return rList


def create_pairs_answer(pQuestion):
    """Crée une liste déroulante par élément ; retourne (conteneur, listes)."""
    rContainer = QWidget()
    vGrid = QGridLayout(rContainer)
    vGrid.setContentsMargins(0, 0, 0, 0)
    vCombos = []

    for vRow, (vLeft, _) in enumerate(pQuestion["pairs"]):
        vCombo = QComboBox()
        vCombo.addItem("Choisir…", None)

        for vIndex, vRight in pQuestion["shuffled"]:
            vCombo.addItem(vRight, vIndex)

        vGrid.addWidget(QLabel(vLeft), vRow, 0)
        vGrid.addWidget(vCombo, vRow, 1)
        vCombos.append(vCombo)

    rAnswer = (rContainer, vCombos)

    return rAnswer


def add_answer_widgets(pQuestion, pLayout, pGroup, pOnSubmit):
    """Ajoute à pLayout la zone de réponse du type ; retourne les widgets à lire.

    pGroup regroupe les boutons d'un QCM, chacun identifié par l'indice
    d'origine de son choix ; pOnSubmit valide la réponse depuis un champ texte.
    """

    vType = pQuestion["type"]

    if vType in ("numerique", "saisie"):
        rWidgets = [create_text_answer(pQuestion, pOnSubmit)]
    elif vType == "ordre":
        rWidgets = [create_order_answer(pQuestion)]
    elif vType == "construction":
        rWidgets = [
            SchemaEditor(pQuestion["shuffled"], pQuestion.get("palette_limits"))
        ]
    elif vType == "zone":
        vHint = QLabel("Cliquez sur le schéma à l'endroit demandé, puis validez.")
        vHint.setObjectName("cardSubtitle")
        rWidgets = [vHint]
    elif vType == "association":
        vContainer, rWidgets = create_pairs_answer(pQuestion)
        pLayout.addWidget(vContainer)

        return rWidgets
    else:
        rWidgets = []

        for vIndex, vChoice in pQuestion["shuffled"]:
            vButton = QRadioButton(vChoice)
            pGroup.addButton(vButton, vIndex)
            rWidgets.append(vButton)

    for vWidget in rWidgets:
        pLayout.addWidget(vWidget)

    return rWidgets


def read_response(pQuestion, pWidgets, pGroup, pPoint):
    """Retourne la réponse saisie selon le type, ou None si elle est incomplète.

    pPoint est le point cliqué sur le schéma d'une question « zone ».
    """

    vType = pQuestion["type"]

    if vType in ("numerique", "saisie"):
        rResponse = pWidgets[0].text().strip() or None
    elif vType == "ordre":
        rResponse = [
            pWidgets[0].item(vRow).data(Qt.ItemDataRole.UserRole)
            for vRow in range(pWidgets[0].count())
        ]
    elif vType == "association":
        rResponse = [vCombo.currentData() for vCombo in pWidgets]
        rResponse = None if None in rResponse else rResponse
    elif vType == "zone":
        rResponse = list(pPoint) if pPoint else None
    elif vType == "construction":
        rResponse = pWidgets[0].get_answer()
        rResponse = rResponse if rResponse["components"] else None
    else:
        rResponse = pGroup.checkedId()
        rResponse = None if rResponse < 0 else rResponse

    return rResponse
