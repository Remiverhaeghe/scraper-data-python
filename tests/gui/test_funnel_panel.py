"""Tests de l'entonnoir des candidatures"""

from PySide6.QtWidgets import QLabel, QProgressBar

from gui.funnel_panel import EMPTY_TEXT, FunnelPanel


def build_funnel(pCounts):
    """Construit les étapes de l'entonnoir à partir de leurs nombres."""

    rFunnel = [
        {"label": vLabel, "count": vCount, "share": 0, "conversion": None}
        for vLabel, vCount in zip(
            ("Envoyées", "Réponses", "Entretiens", "Acceptées"), pCounts
        )
    ]

    return rFunnel


def test_empty_funnel_shows_a_message_instead_of_empty_bars(qt_application):
    """Vérifie le message sans candidature, puis les barres dès la première."""

    vPanel = FunnelPanel()
    vPanel.set_funnel(build_funnel((0, 0, 0, 0)))

    assert not vPanel.findChildren(QProgressBar)
    assert any(vLabel.text() == EMPTY_TEXT for vLabel in vPanel.findChildren(QLabel))

    vPanel.set_funnel(build_funnel((3, 1, 0, 0)))
    qt_application.processEvents()

    assert len(vPanel.findChildren(QProgressBar)) == 4
