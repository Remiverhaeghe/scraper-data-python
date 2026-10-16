"""Tests des composants partagés : carte repliable et tuile cliquable"""

from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel, QPushButton

from gui.widgets import TileButton, create_collapsible_card


def test_collapsible_card_remembers_state(qt_application):
    """Vérifie que la carte se replie par son titre et garde cet état."""

    vCard, vLayout = create_collapsible_card(
        "Niveaux", "Sous-titre", "list-checks", "test"
    )
    vLayout.addWidget(QLabel("Contenu"))
    vContent = vLayout.parentWidget()

    assert not vContent.isHidden()

    vCard.findChild(QPushButton, "collapsibleTitle").click()

    assert vContent.isHidden()
    assert QSettings().value("collapsed/test", False, type=bool)

    _, vOtherLayout = create_collapsible_card("Niveaux", pKey="test")

    assert vOtherLayout.parentWidget().isHidden()


def test_tile_button_states_and_keyboard(qt_application):
    """Vérifie les états réussi et sélectionné, et l'ouverture au clavier."""

    vTile = TileButton("Titre", "Détail", "code", "amber", "★☆")
    vClicks = []
    vTile.clicked.connect(lambda: vClicks.append(True))

    assert not vTile.done
    assert not vTile.isChecked()

    vTile.set_done(True)
    vTile.setChecked(True)

    assert vTile.property("done")
    assert vTile.property("checked")
    assert vTile.badge_label.text() == "★☆"

    qt_application.sendEvent(
        vTile,
        QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
        ),
    )

    assert vClicks == [True]
