"""Tests du point d'entrée de l'application"""

import pytest

import main


def test_main_initializes_database_and_starts_gui(monkeypatch):
    """Vérifie que main initialise la base, démarre la GUI et transmet son code."""

    vCalls = []

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base de données."""

        vCalls.append("initialize_database")

    def mock_run():
        """Simule l'exécution de l'interface graphique."""

        vCalls.append("run")

        return 0

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    monkeypatch.setattr(main, "run", mock_run)

    with pytest.raises(SystemExit) as vExit:
        main.main()

    assert vExit.value.code == 0

    assert vCalls == ["initialize_database", "run"]
