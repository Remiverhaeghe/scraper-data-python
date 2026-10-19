"""Tests des composants partagés : carte repliable et tuile cliquable"""

from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel

from gui.widgets import CardHeader, TileButton, create_card


def test_collapsible_card_remembers_state(qt_application):
    """Vérifie que la carte se replie par son titre et garde cet état."""

    vCard, vLayout = create_card("Niveaux", "Sous-titre", "list-checks", "test")
    vLayout.addWidget(QLabel("Contenu"))
    vContent = vLayout.parentWidget()

    assert not vContent.isHidden()

    vCard.findChild(CardHeader).clicked.emit()

    assert vContent.isHidden()
    assert QSettings().value("collapsed/test", False, type=bool)

    _, vOtherLayout = create_card("Niveaux", pKey="test")

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


def test_untitled_card_is_not_collapsible(qt_application):
    """Vérifie qu'une carte sans titre n'a pas d'en-tête et garde son layout."""

    vCard, vLayout = create_card()

    assert vCard.findChild(CardHeader) is None
    assert vLayout.parentWidget() is vCard


def test_card_title_stays_a_label(qt_application):
    """Vérifie que le titre reste un QLabel « cardTitle » modifiable."""

    vCard, _ = create_card("Candidatures")
    vTitle = vCard.findChild(QLabel, "cardTitle")

    vTitle.setText("Candidatures (3)")

    assert vTitle.text() == "Candidatures (3)"
