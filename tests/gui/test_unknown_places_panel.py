"""Tests du panneau des lieux introuvables"""

import requests

import gui.unknown_places_panel as unknown_places_panel
from gui.unknown_places_panel import UnknownPlacesPanel


def test_place_is_resolved_or_explained(qt_application, tmp_path, monkeypatch):
    """Vérifie la ligne d'un lieu, la commune associée, puis le géocodeur injoignable."""

    vPlaces = [{"key": "atlantis", "example": "Atlantis", "count": 3}]
    monkeypatch.setattr(
        unknown_places_panel, "list_unknown_places", lambda pDatabaseFile: vPlaces
    )
    monkeypatch.setattr(
        unknown_places_panel,
        "resolve_place",
        lambda pDatabaseFile, pKey, pCommune: vPlaces.clear() or "Roubaix",
    )
    vPanel = UnknownPlacesPanel(tmp_path / "scraper.db")
    vPlaced = []
    vPanel.placed.connect(lambda: vPlaced.append(True))

    vPanel.refresh()
    vPanel.resolve("atlantis", "Roubaix")

    assert "associé à Roubaix" in vPanel.message_label.text()
    assert vPlaced == [True]
    assert vPanel.rows_layout.count() == 1

    def fail(*_pArgs):
        raise requests.ConnectionError("hors ligne")

    monkeypatch.setattr(unknown_places_panel, "resolve_place", fail)
    vPanel.resolve("atlantis", "Roubaix")

    assert "ne répond pas" in vPanel.message_label.text()
