"""Tests du panneau des employeurs industriels de la région"""

import gui.local_employers_panel as panel_module
from gui.local_employers_panel import LocalEmployersPanel
from job.companies import load_company_rules
from job.local_employers import LOCAL_EMPLOYERS_KEY
from storage.database import initialize_database
from storage.settings_repository import save_json_setting

EMPLOYERS = [
    {
        "siren": "1",
        "name": "ROQUETTE FRERES",
        "names": ["ROQUETTE FRERES"],
        "sector": "Agroalimentaire",
        "city": "Lestrem",
        "distance_km": 40,
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
    assert vPanel.table.item(1, 5).text() == "Suivi"
    assert vOpened[0].endswith("/entreprise/2") and "duckduckgo" in vOpened[1]

    vPanel.sector_combo.setCurrentIndex(vPanel.sector_combo.findData("Agroalimentaire"))

    assert vPanel.table.rowCount() == 1

    def failing_fetch(*_pArgs):
        raise ValueError("Le service public ne répond pas.")

    monkeypatch.setattr(panel_module, "fetch_local_employers", failing_fetch)
    vPanel.start_fetch()

    assert vPanel.message_label.text() == "Le service public ne répond pas."
    assert vPanel.update_button.isEnabled()
