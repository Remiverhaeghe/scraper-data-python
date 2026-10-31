"""Tests du panneau des employeurs industriels de la région"""

import gui.local_employers_panel as panel_module
from gui.local_employers_panel import LocalEmployersPanel
from job.companies import load_company_rules
from job.geocoding import HOME_KEY
from job.local_employers import LOCAL_EMPLOYERS_KEY
from job.spontaneous_applications import load_spontaneous
from storage.database import initialize_database
from storage.settings_repository import save_json_setting

EMPLOYERS = [
    {
        "siren": "1",
        "name": "ROQUETTE FRERES",
        "names": ["ROQUETTE FRERES"],
        "sector": "Agroalimentaire",
        "headcount": "1 000 à 1 999 salariés",
        "city": "Lestrem",
        "distance_km": 40,
        "latitude": 50.61,
        "longitude": 2.67,
        "page": "https://annuaire-entreprises.data.gouv.fr/entreprise/1",
    },
    {
        "siren": "2",
        "name": "ALSTOM TRANSPORT SA",
        "names": ["ALSTOM TRANSPORT SA", "ALSTOM"],
        "sector": "Matériel de transport",
        "city": "Petite-Forêt",
        "distance_km": 55,
        "page": "https://annuaire-entreprises.data.gouv.fr/entreprise/2",
    },
]


class ImmediateThread:
    """Fil simulé : la tâche s'exécute aussitôt, dans le test."""

    def __init__(self, target, daemon):
        self.target = target

    def start(self):
        self.target()


def test_employers_are_updated_filtered_and_followed(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie la mise à jour, le filtre par secteur, le suivi et l'erreur du service."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vOpened = []
    monkeypatch.setattr(panel_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(
        panel_module.QDesktopServices,
        "openUrl",
        lambda pUrl: vOpened.append(pUrl.toString()),
    )

    def fake_fetch(pDatabaseFile, _pNow):
        save_json_setting(
            pDatabaseFile,
            LOCAL_EMPLOYERS_KEY,
            {"updated_at": "2026-10-31T09:00:00", "employers": EMPLOYERS},
        )
        return 2

    monkeypatch.setattr(panel_module, "fetch_local_employers", fake_fetch)
    vPanel = LocalEmployersPanel(vDatabaseFile)
    vPanel.refresh()

    assert vPanel.status_label.text().startswith("Liste encore vide")

    vPanel.start_fetch()

    assert (
        vPanel.table.rowCount() == 2
        and vPanel.message_label.text() == "2 employeur(s) trouvé(s)."
    )

    vPanel.follow()

    assert vPanel.message_label.text() == "Choisissez d'abord un employeur."

    vPanel.table.selectRow(1)
    vPanel.follow()
    vPanel.open_page()
    vPanel.table.selectRow(1)
    vPanel.search_career_page()

    assert set(load_company_rules(vDatabaseFile)["preferred"]) == {
        "ALSTOM TRANSPORT SA",
        "ALSTOM",
    }
    assert vPanel.table.item(1, 6).text() == "Suivi"
    assert vOpened[0].endswith("/entreprise/2") and "duckduckgo" in vOpened[1]

    vPanel.sector_combo.setCurrentIndex(vPanel.sector_combo.findData("Agroalimentaire"))

    assert vPanel.table.rowCount() == 1

    def failing_fetch(*_pArgs):
        raise ValueError("Le service public ne répond pas.")

    monkeypatch.setattr(panel_module, "fetch_local_employers", failing_fetch)
    vPanel.start_fetch()

    assert vPanel.message_label.text() == "Le service public ne répond pas."
    assert vPanel.update_button.isEnabled()


def test_spontaneous_application_is_tracked_and_placed_on_the_map(
    qt_application, tmp_path
):
    """Vérifie l'envoi noté, le filtre des contactés et l'employeur choisi sur la carte."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_json_setting(
        vDatabaseFile,
        LOCAL_EMPLOYERS_KEY,
        {"updated_at": "2026-10-31T09:00:00", "employers": EMPLOYERS},
    )
    save_json_setting(
        vDatabaseFile,
        HOME_KEY,
        {"label": "Lille", "latitude": 50.63, "longitude": 3.06},
    )
    vPanel = LocalEmployersPanel(vDatabaseFile)
    vPanel.refresh()

    assert vPanel.table.item(0, 2).text() == "1 000 à 1 999 salariés"
    assert vPanel.map.home["label"] == "Lille"

    vPanel.record_status()

    assert vPanel.message_label.text() == "Choisissez d'abord un employeur."

    vPanel.map.employer_clicked.emit("1")
    vPanel.status_combo.setCurrentIndex(vPanel.status_combo.findData("sent"))
    vPanel.record_status()

    assert load_spontaneous(vDatabaseFile)["1"]["status"] == "sent"
    assert vPanel.table.item(0, 6).text().startswith("Envoyée · envoi du ")
    assert "1 candidature(s) spontanée(s), 0 à relancer" in vPanel.status_label.text()

    vPanel.contact_combo.setCurrentIndex(vPanel.contact_combo.findData("todo"))

    assert vPanel.table.rowCount() == 1
    assert vPanel.table.item(0, 0).text() == "ALSTOM TRANSPORT SA"

    vPanel.table.selectRow(0)
    save_json_setting(vDatabaseFile, LOCAL_EMPLOYERS_KEY, {"employers": []})
    vPanel.record_status()

    assert vPanel.message_label.text().startswith("Employeur absent")
