"""Tests de la carte du domicile"""

import requests

import gui.home_location_panel as home_location_panel
from gui.home_location_panel import HomeLocationPanel
from storage.database import initialize_database

HOME = {"address": "59000 Lille", "label": "Lille", "latitude": 50.6, "longitude": 3}


def test_home_is_saved_then_offers_are_located(qt_application, tmp_path, monkeypatch):
    """Vérifie l'enregistrement, le placement des offres et leur bilan."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = HomeLocationPanel(vDatabaseFile)
    vStarted = []

    monkeypatch.setattr(home_location_panel, "save_home", lambda *pArgs: HOME)
    monkeypatch.setattr(
        home_location_panel.threading,
        "Thread",
        lambda target, daemon: vStarted.append(target)
        or type("Thread", (), {"start": lambda self: None})(),
    )
    monkeypatch.setattr(
        home_location_panel,
        "locate_all_offers",
        lambda *pArgs: {"located": 4, "lookups": 2, "unknown": 0},
    )

    vPanel.address_edit.setText("59000 Lille")
    vPanel.save()

    assert vPanel.message_label.text().startswith("Lieu reconnu : Lille.")

    vStarted[0]()

    assert vPanel.message_label.text().startswith("4 offre(s) placée(s)")


def test_home_errors_and_clearing(qt_application, tmp_path, monkeypatch):
    """Vérifie les messages d'une adresse introuvable, d'un échec et d'un effacement."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = HomeLocationPanel(vDatabaseFile)

    def refuse(*_pArgs):
        raise ValueError("Adresse introuvable.")

    def disconnect(*_pArgs):
        raise requests.ConnectionError("hors ligne")

    for vSave, vExpected in (
        (refuse, "Adresse introuvable."),
        (disconnect, "Le géocodeur est injoignable : vérifiez la connexion."),
        (lambda *pArgs: None, "Domicile effacé."),
    ):
        monkeypatch.setattr(home_location_panel, "save_home", vSave)
        vPanel.save()

        assert vPanel.message_label.text() == vExpected

    vPanel.show_located(None)

    assert "pas pu être placées" in vPanel.message_label.text()

    monkeypatch.setattr(home_location_panel, "load_home", lambda *pArgs: HOME)
    vPanel.refresh()

    assert vPanel.address_edit.text() == "59000 Lille"


def test_location_failure_is_reported(qt_application, tmp_path, monkeypatch):
    """Vérifie qu'un échec du placement est signalé par le bilan None."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = HomeLocationPanel(vDatabaseFile)
    vReports = []
    vPanel.offers_located.connect(vReports.append)

    def fail(*_pArgs):
        raise OSError("disque")

    monkeypatch.setattr(home_location_panel, "locate_all_offers", fail)
    vPanel.run_location()

    assert vReports == [None]


def test_alert_radius_is_saved(qt_application, tmp_path, monkeypatch):
    """Vérifie le rayon des alertes, refusé tant que le domicile est inconnu."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPanel = HomeLocationPanel(vDatabaseFile)
    vPanel.refresh()

    assert not vPanel.radius_combo.isEnabled()

    vPanel.save_radius()

    assert vPanel.message_label.text() == "Le rayon n'a pas pu être enregistré."

    vSaved = []
    monkeypatch.setattr(
        home_location_panel, "load_home", lambda *pArgs: {**HOME, "alert_radius_km": 25}
    )
    monkeypatch.setattr(
        home_location_panel, "save_alert_radius", lambda *pArgs: vSaved.append(pArgs[1])
    )
    vPanel.refresh()

    assert vPanel.radius_combo.currentData() == 25

    vPanel.radius_combo.setCurrentIndex(vPanel.radius_combo.findData(50))
    vPanel.save_radius()

    assert vSaved == [50]
    assert vPanel.message_label.text() == "Rayon des alertes enregistré."
