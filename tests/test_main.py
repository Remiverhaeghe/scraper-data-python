"""Tests du point d'entrée de l'application"""

import main


def test_main_initializes_database_and_starts_gui(monkeypatch):
    """Vérifie que main initialise la base puis démarre la GUI."""

    vCalls = []

    def mock_initialize_database(pDatabaseFile):
        """Simule l'initialisation de la base de données."""

        vCalls.append("initialize_database")

    class MockApplication:
        """Simule la fenêtre principale de l'application."""

        def __init__(self):
            vCalls.append("application")

        def run(self):
            """Simule le lancement de la boucle graphique."""

            vCalls.append("run")

    monkeypatch.setattr(main, "initialize_database", mock_initialize_database)

    monkeypatch.setattr(main, "ApplicationWindow", MockApplication)

    main.main()

    assert vCalls == ["initialize_database", "application", "run"]
