"""Éditeur de schéma : palette de composants, placement sur la grille et câblage

On clique sur une icône de la palette pour poser le composant dans la première
case libre, on le déplace à la souris, puis on relie deux bornes en cliquant sur
l'une puis sur l'autre. La géométrie et le tracé des fils sont ceux du dessin de
la correction (job/schema_drawing.py) : le schéma construit lui ressemble.
"""

import re

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS
from gui.widgets import create_button
from job.schema_drawing import (
    GRID_COLUMNS,
    GRID_ROWS,
    CELL_HEIGHT,
    CELL_WIDTH,
    CORRIDOR_OFFSET,
    LABEL_GAP,
    LANE_COUNT,
    MARGIN,
    SYMBOL_OFFSET,
    WIRE_COLOR,
    get_exit,
    get_origin,
    route_wire,
    wrap_label,
)
from job.schema_library import COMPONENTS, HEIGHT, WIDTH, build_icon

PORT_RADIUS = 6
PALETTE_COLUMNS = 4
ICON_SIZE = 44
VIEW_HEIGHT = 520
PATH_COMMAND = re.compile(r"([MVH])([-\d.]+)(?:,([-\d.]+))?")


def build_path(pPath):
    """Convertit un tracé SVG « M x,y V y H x » en chemin Qt."""

    rPath = QPainterPath()
    vX = vY = 0.0

    for vCommand, vFirst, vSecond in PATH_COMMAND.findall(pPath):
        if vCommand == "M":
            vX, vY = float(vFirst), float(vSecond)
            rPath.moveTo(vX, vY)
            continue

        if vCommand == "V":
            vY = float(vFirst)
        else:
            vX = float(vFirst)

        rPath.lineTo(vX, vY)

    return rPath


def build_icon_pixmap(pType):
    """Retourne l'icône de palette d'un type de composant."""

    rPixmap = QPixmap(WIDTH, HEIGHT)
    rPixmap.fill(QColor("#ffffff"))
    vPainter = QPainter(rPixmap)
    QSvgRenderer(QByteArray(build_icon(pType).encode("utf-8"))).render(vPainter)
    vPainter.end()

    return rPixmap


class PortItem(QGraphicsEllipseItem):
    """Borne cliquable d'un composant posé."""

    def __init__(self, pComponent, pName, pPosition):
        """Crée la borne pName à sa place sur le symbole du composant."""
        super().__init__(
            pPosition[0] - PORT_RADIUS,
            pPosition[1] - PORT_RADIUS,
            2 * PORT_RADIUS,
            2 * PORT_RADIUS,
            pComponent,
        )

        self.component = pComponent
        self.name = pName
        self.center = QPointF(*pPosition)
        self.set_active(False)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{pComponent.label} : borne {pName}")

    def set_active(self, pActive):
        """Met la borne en évidence quand elle attend sa seconde extrémité."""
        self.setPen(QPen(QColor(COLORS["primary"]), 2))
        self.setBrush(QBrush(QColor(COLORS["danger"] if pActive else "#ffffff")))

    def mousePressEvent(self, pEvent):
        """Transmet le clic à l'éditeur, qui relie les bornes deux à deux."""
        self.component.editor.select_port(self)
        pEvent.accept()


class ComponentItem(QGraphicsSvgItem):
    """Composant posé sur la grille, déplaçable de case en case."""

    def __init__(self, pEditor, pInstance, pRenderer):
        """Crée le symbole, son nom et ses bornes ; pInstance vaut (id, type, nom)."""
        super().__init__()

        self.editor = pEditor
        self.instance_id, self.type, self.label = pInstance
        self.cell = (0, 0)
        self.setSharedRenderer(pRenderer)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        for vIndex, vLine in enumerate(wrap_label(self.label)):
            vText = QGraphicsSimpleTextItem(vLine, self)
            vText.setBrush(QBrush(QColor("#334155")))
            vText.setPos(WIDTH + LABEL_GAP, HEIGHT / 2 - 20 + vIndex * 14)

        self.ports = {
            vName: PortItem(self, vName, vPosition)
            for vName, vPosition in COMPONENTS[self.type].ports
        }

    def boundingRect(self):
        """Étend la zone du composant à ses bornes, qui débordent du symbole."""
        return QRectF(-PORT_RADIUS, -PORT_RADIUS, WIDTH + 2 * PORT_RADIUS, HEIGHT + 12)

    def paint(self, pPainter, _pOption, _pWidget=None):
        """Dessine le symbole sur fond blanc, encadré quand il est sélectionné."""
        pPainter.fillRect(QRectF(0, 0, WIDTH, HEIGHT), QColor("#ffffff"))
        self.renderer().render(pPainter, QRectF(0, 0, WIDTH, HEIGHT))

        if self.isSelected():
            pPainter.setPen(QPen(QColor(COLORS["primary"]), 1.5, Qt.PenStyle.DashLine))
            pPainter.drawRect(QRectF(-4, -4, WIDTH + 8, HEIGHT + 8))

    def itemChange(self, pChange, pValue):
        """Aimante le composant sur une case libre et redessine ses fils."""
        if pChange == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            vCell = self.editor.nearest_free_cell(pValue, self)

            if vCell is None:
                return QPointF(*get_origin(*self.cell))

            self.cell = vCell

            return QPointF(*get_origin(*vCell))

        if pChange == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.editor.redraw_wires()

        return super().itemChange(pChange, pValue)


class WireItem(QGraphicsPathItem):
    """Fil reliant deux bornes, sélectionnable pour être supprimé."""

    def __init__(self, pStart, pEnd, pLane):
        """Crée le fil entre deux bornes, décalé selon son couloir."""
        super().__init__()

        self.start = pStart
        self.end = pEnd
        self.lane = pLane
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(-1)
        self.redraw()

    def redraw(self):
        """Recalcule le tracé à partir de la position actuelle des deux bornes."""
        vStart = self.start.scenePos() + self.start.center
        vEnd = self.end.scenePos() + self.end.center
        vOriginA = self.start.component.pos()
        vOriginB = self.end.component.pos()

        self.setPath(
            build_path(
                route_wire(
                    ((vStart.x(), vStart.y()), get_exit(self.start.center.y())),
                    ((vEnd.x(), vEnd.y()), get_exit(self.end.center.y())),
                    max(vOriginA.x(), vOriginB.x()) - SYMBOL_OFFSET + CORRIDOR_OFFSET,
                    self.lane,
                )
            )
        )
        self.setPen(
            QPen(
                QColor(COLORS["danger"] if self.isSelected() else WIRE_COLOR),
                3 if self.isSelected() else 2.5,
            )
        )

    def itemChange(self, pChange, pValue):
        """Redessine le fil quand il est sélectionné ou désélectionné."""
        if pChange == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.redraw()

        return super().itemChange(pChange, pValue)

    def describe(self):
        """Retourne la liaison au format de la réponse : [id, borne, id, borne]."""
        return [
            self.start.component.instance_id,
            self.start.name,
            self.end.component.instance_id,
            self.end.name,
        ]


class SchemaView(QGraphicsView):
    """Vue de la scène, qui supprime la sélection avec la touche Suppr."""

    delete_requested = Signal()

    def keyPressEvent(self, pEvent):
        """Supprime les éléments sélectionnés avec Suppr ou Retour arrière."""
        if pEvent.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            return

        super().keyPressEvent(pEvent)


class SchemaEditor(QWidget):
    """Construction d'un schéma à partir d'une palette de composants."""

    def __init__(self, pPalette, pLimits=None):
        """Crée la palette, la grille et les boutons d'édition.

        pLimits donne le nombre d'exemplaires permis par type, un par défaut.
        """
        super().__init__()

        self.limits = {vType: (pLimits or {}).get(vType, 1) for vType in pPalette}
        self.components = {}
        self.wires = []
        self.pending_port = None
        self.renderers = {
            vType: QSvgRenderer(QByteArray(build_icon(vType).encode("utf-8")))
            for vType in pPalette
        }

        self.scene = QGraphicsScene(
            0,
            0,
            2 * MARGIN + GRID_COLUMNS * CELL_WIDTH,
            2 * MARGIN + GRID_ROWS * CELL_HEIGHT,
        )
        self.scene.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.view = SchemaView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setMinimumHeight(VIEW_HEIGHT)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.delete_requested.connect(self.delete_selection)

        self.palette_buttons = {}
        vPalette = QGridLayout()
        vPalette.setSpacing(6)

        for vIndex, vType in enumerate(pPalette):
            vButton = QToolButton()
            vButton.setIcon(QIcon(build_icon_pixmap(vType)))
            vButton.setIconSize(build_icon_pixmap(vType).size() * ICON_SIZE / HEIGHT)
            vButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            vButton.setToolTip(f"Placer : {COMPONENTS[vType].label}")
            vButton.setMinimumWidth(110)
            vButton.clicked.connect(
                lambda _=False, pType=vType: self.add_component(pType)
            )
            self.palette_buttons[vType] = vButton
            vPalette.addWidget(vButton, *divmod(vIndex, PALETTE_COLUMNS))

        self.help_label = QLabel(
            "Cliquez sur une icône pour poser le composant, déplacez-le à la souris, "
            "puis cliquez sur une borne et sur une autre pour les relier."
        )
        self.help_label.setObjectName("cardSubtitle")
        self.help_label.setWordWrap(True)

        self.delete_button = create_button("Supprimer la sélection", "trash-2")
        self.delete_button.clicked.connect(self.delete_selection)
        vClearButton = create_button("Tout effacer", "history")
        vClearButton.clicked.connect(self.clear)

        vActions = QHBoxLayout()
        vActions.addWidget(self.delete_button)
        vActions.addWidget(vClearButton)
        vActions.addStretch(1)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(self.help_label)
        vLayout.addLayout(vPalette)
        vLayout.addWidget(self.view)
        vLayout.addLayout(vActions)
        self.refresh_palette()

    def refresh_palette(self):
        """Met à jour chaque bouton : exemplaires posés, et grisé une fois au plafond."""
        for vType, vButton in self.palette_buttons.items():
            vCount = self.count_type(vType)
            vText = COMPONENTS[vType].label

            if self.limits[vType] > 1:
                vText += f" ({vCount}/{self.limits[vType]})"

            vButton.setText(vText)
            vButton.setEnabled(vCount < self.limits[vType])

    def count_type(self, pType):
        """Retourne le nombre d'exemplaires d'un type déjà posés."""
        rCount = sum(vItem.type == pType for vItem in self.components.values())

        return rCount

    def new_instance(self, pType):
        """Retourne (identifiant, nom) du prochain exemplaire d'un type.

        Un type unique garde son type pour identifiant ; sinon les exemplaires
        sont numérotés, en réutilisant le plus petit numéro libre.
        """
        vLabel = COMPONENTS[pType].label

        if self.limits[pType] == 1:
            return (pType, vLabel)

        vNumber = 1

        while f"{pType}-{vNumber}" in self.components:
            vNumber += 1

        rInstance = (f"{pType}-{vNumber}", f"{vLabel} {vNumber}")

        return rInstance

    def nearest_free_cell(self, pPosition, pItem=None):
        """Retourne la case la plus proche d'une position, ou None si elle est prise."""
        vColumn = round((pPosition.x() - MARGIN - SYMBOL_OFFSET) / CELL_WIDTH)
        vRow = round((pPosition.y() - MARGIN) / CELL_HEIGHT)
        rCell = (
            min(max(vColumn, 0), GRID_COLUMNS - 1),
            min(max(vRow, 0), GRID_ROWS - 1),
        )

        if any(
            vItem.cell == rCell
            for vItem in self.components.values()
            if vItem is not pItem
        ):
            rCell = None

        return rCell

    def first_free_cell(self):
        """Retourne la première case libre, colonne par colonne, ou None.

        Une chaîne se construit ainsi de haut en bas, comme on la dessine.
        """
        vTaken = {vItem.cell for vItem in self.components.values()}

        rCell = next(
            (
                (vColumn, vRow)
                for vColumn in range(GRID_COLUMNS)
                for vRow in range(GRID_ROWS)
                if (vColumn, vRow) not in vTaken
            ),
            None,
        )

        return rCell

    def add_component(self, pType, pCell=None):
        """Pose un exemplaire d'un type dans une case libre ; retourne son identifiant."""
        vCell = pCell or self.first_free_cell()

        if self.count_type(pType) >= self.limits[pType] or vCell is None:
            return None

        vId, vLabel = self.new_instance(pType)
        vItem = ComponentItem(self, (vId, pType, vLabel), self.renderers[pType])
        vItem.cell = vCell
        self.components[vId] = vItem
        self.scene.addItem(vItem)
        vItem.setPos(QPointF(*get_origin(*vCell)))
        self.refresh_palette()

        return vId

    def select_port(self, pPort):
        """Retient une première borne, puis relie la seconde ; un même clic annule."""
        if self.pending_port is None:
            self.pending_port = pPort
            pPort.set_active(True)
            return

        vFirst = self.pending_port
        self.pending_port = None
        vFirst.set_active(False)

        if vFirst is pPort or vFirst.component is pPort.component:
            return

        vKey = frozenset(
            (
                (vFirst.component.instance_id, vFirst.name),
                (pPort.component.instance_id, pPort.name),
            )
        )

        if any(
            frozenset(
                (
                    (vWire.start.component.instance_id, vWire.start.name),
                    (vWire.end.component.instance_id, vWire.end.name),
                )
            )
            == vKey
            for vWire in self.wires
        ):
            return

        vWire = WireItem(vFirst, pPort, len(self.wires) % LANE_COUNT)
        self.wires.append(vWire)
        self.scene.addItem(vWire)

    def redraw_wires(self):
        """Redessine tous les fils après le déplacement d'un composant."""
        for vWire in self.wires:
            vWire.redraw()

    def remove_wire(self, pWire):
        """Retire un fil de la scène et de la liste."""
        self.wires.remove(pWire)
        self.scene.removeItem(pWire)

    def remove_component(self, pId):
        """Retire un composant, ses fils, et le rend de nouveau disponible."""
        vItem = self.components.pop(pId)

        for vWire in [
            vWire
            for vWire in self.wires
            if vItem in (vWire.start.component, vWire.end.component)
        ]:
            self.remove_wire(vWire)

        if self.pending_port is not None and self.pending_port.component is vItem:
            self.pending_port = None

        self.scene.removeItem(vItem)
        self.refresh_palette()

    def delete_selection(self):
        """Supprime les composants et les fils sélectionnés."""
        for vItem in self.scene.selectedItems():
            if isinstance(vItem, WireItem) and vItem in self.wires:
                self.remove_wire(vItem)
            elif (
                isinstance(vItem, ComponentItem)
                and vItem.instance_id in self.components
            ):
                self.remove_component(vItem.instance_id)

    def clear(self):
        """Retire tous les composants et tous les fils."""
        for vId in list(self.components):
            self.remove_component(vId)

    def load_answer(self, pAnswer):
        """Remplace le schéma par un schéma enregistré, identifiants et cases compris."""
        self.clear()

        for vItem in (pAnswer or {}).get("components", []):
            vType = vItem.get("type")

            if vType not in self.limits or self.count_type(vType) >= self.limits[vType]:
                continue

            vId = vItem["id"]
            vSuffix = vId.rsplit("-", 1)[-1] if "-" in vId else ""
            vLabel = COMPONENTS[vType].label + (
                f" {vSuffix}" if vSuffix.isdigit() else ""
            )
            vComponent = ComponentItem(
                self, (vId, vType, vLabel), self.renderers[vType]
            )
            vComponent.cell = (vItem["x"], vItem["y"])
            self.components[vId] = vComponent
            self.scene.addItem(vComponent)
            vComponent.setPos(QPointF(*get_origin(*vComponent.cell)))

        for vIdA, vPortA, vIdB, vPortB in (pAnswer or {}).get("wires", []):
            vStart = self.components.get(vIdA)
            vEnd = self.components.get(vIdB)

            if vStart and vEnd and vPortA in vStart.ports and vPortB in vEnd.ports:
                vWire = WireItem(
                    vStart.ports[vPortA],
                    vEnd.ports[vPortB],
                    len(self.wires) % LANE_COUNT,
                )
                self.wires.append(vWire)
                self.scene.addItem(vWire)

        self.refresh_palette()

    def get_answer(self):
        """Retourne le schéma construit, au format attendu par la correction."""
        return {
            "components": [
                {"id": vId, "type": vItem.type, "x": vItem.cell[0], "y": vItem.cell[1]}
                for vId, vItem in self.components.items()
            ],
            "wires": [vWire.describe() for vWire in self.wires],
        }
