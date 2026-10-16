"""Tests de l'éditeur de schéma du bureau"""

from PySide6.QtCore import QPointF

from gui.schema_editor import SchemaEditor, build_path
from job.schema_drawing import CELL_HEIGHT, get_origin

PALETTE = ["reseau", "fusible", "moteur", "differentiel"]


def link(pEditor, pTypeA, pPortA, pTypeB, pPortB):
    """Relie deux bornes comme l'utilisateur : un clic sur chacune."""

    pEditor.select_port(pEditor.components[pTypeA].ports[pPortA])
    pEditor.select_port(pEditor.components[pTypeB].ports[pPortB])


def test_components_are_placed_wired_and_described(qt_application):
    """Vérifie la pose dans la grille, le câblage et la réponse produite."""

    vEditor = SchemaEditor(PALETTE)

    for vType in ("reseau", "fusible", "moteur"):
        vEditor.add_component(vType)

    assert not vEditor.palette_buttons["fusible"].isEnabled()
    assert vEditor.palette_buttons["differentiel"].isEnabled()
    assert [vItem.cell for vItem in vEditor.components.values()] == [
        (0, 0),
        (0, 1),
        (0, 2),
    ]

    vEditor.add_component("fusible")

    assert len(vEditor.components) == 3

    link(vEditor, "reseau", "sortie", "fusible", "1")
    link(vEditor, "fusible", "2", "moteur", "entrée")
    link(vEditor, "moteur", "entrée", "fusible", "2")
    vEditor.select_port(vEditor.components["moteur"].ports["entrée"])
    vEditor.select_port(vEditor.components["moteur"].ports["entrée"])

    assert vEditor.get_answer() == {
        "components": [
            {"id": "reseau", "type": "reseau", "x": 0, "y": 0},
            {"id": "fusible", "type": "fusible", "x": 0, "y": 1},
            {"id": "moteur", "type": "moteur", "x": 0, "y": 2},
        ],
        "wires": [
            ["reseau", "sortie", "fusible", "1"],
            ["fusible", "2", "moteur", "entrée"],
        ],
    }


def test_components_snap_to_free_cells_and_wires_follow(qt_application):
    """Vérifie l'aimantation sur une case libre et le fil redessiné."""

    vEditor = SchemaEditor(PALETTE)
    vEditor.add_component("reseau")
    vEditor.add_component("fusible")
    link(vEditor, "reseau", "sortie", "fusible", "1")
    vWire = vEditor.wires[0]
    vBefore = vWire.path().boundingRect()

    vEditor.components["fusible"].setPos(QPointF(*get_origin(2, 3)) + QPointF(9, 12))

    assert vEditor.components["fusible"].cell == (2, 3)
    assert vWire.path().boundingRect() != vBefore

    vEditor.components["fusible"].setPos(QPointF(*get_origin(0, 0)))

    assert vEditor.components["fusible"].cell == (2, 3)

    vEditor.components["fusible"].setPos(QPointF(-500, 10 * CELL_HEIGHT))

    assert vEditor.components["fusible"].cell == (0, 5)


def test_selection_is_deleted_and_palette_restored(qt_application):
    """Vérifie la suppression d'un fil, d'un composant et l'effacement complet."""

    vEditor = SchemaEditor(PALETTE)

    for vType in ("reseau", "fusible", "moteur"):
        vEditor.add_component(vType)

    link(vEditor, "reseau", "sortie", "fusible", "1")
    link(vEditor, "fusible", "2", "moteur", "entrée")

    vEditor.wires[0].setSelected(True)
    vEditor.delete_selection()

    assert len(vEditor.wires) == 1

    vEditor.components["fusible"].setSelected(True)
    vEditor.delete_selection()

    assert "fusible" not in vEditor.components and not vEditor.wires
    assert vEditor.palette_buttons["fusible"].isEnabled()

    vEditor.select_port(vEditor.components["moteur"].ports["entrée"])
    vEditor.clear()

    assert vEditor.get_answer() == {"components": [], "wires": []}
    assert vEditor.pending_port is None


def test_svg_path_is_converted_for_qt():
    """Vérifie la conversion d'un tracé à angles droits en chemin Qt."""

    vPath = build_path("M10,20 V40 H60 V80")

    assert vPath.elementCount() == 4
    assert (vPath.currentPosition().x(), vPath.currentPosition().y()) == (60, 80)


def test_identical_components_are_numbered_up_to_their_limit(qt_application):
    """Vérifie les exemplaires numérotés, le plafond de la palette et la renumérotation."""

    vEditor = SchemaEditor(["verin_double", "frl"], {"verin_double": 2})

    assert vEditor.palette_buttons["verin_double"].text() == "Vérin double effet (0/2)"
    assert vEditor.add_component("verin_double") == "verin_double-1"
    assert vEditor.add_component("verin_double") == "verin_double-2"
    assert vEditor.add_component("verin_double") is None
    assert not vEditor.palette_buttons["verin_double"].isEnabled()
    assert vEditor.components["verin_double-2"].label == "Vérin double effet 2"

    vEditor.add_component("frl")
    link(vEditor, "verin_double-1", "fond", "verin_double-2", "fond")
    vEditor.remove_component("verin_double-1")

    assert vEditor.palette_buttons["verin_double"].isEnabled()
    assert not vEditor.wires
    assert vEditor.add_component("verin_double") == "verin_double-1"
    assert [vItem["id"] for vItem in vEditor.get_answer()["components"]] == [
        "verin_double-2",
        "frl",
        "verin_double-1",
    ]
