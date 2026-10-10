"""Tests de la configuration Greenhouse"""

from job.sources.greenhouse.config import GreenhouseConfig, load_config


def test_load_config(monkeypatch):
    """Vérifie le chargement correct de la configuration Greenhouse"""
    monkeypatch.setenv("GREENHOUSE_BOARD", "example-board")

    rConfig = load_config()

    assert isinstance(rConfig, GreenhouseConfig)

    assert rConfig.board == "example-board"


def test_load_config_without_board(monkeypatch):
    """Vérifie l'erreur lorsqu'aucun board Greenhouse n'est configuré"""
    monkeypatch.delenv("GREENHOUSE_BOARD", raising=False)

    try:
        load_config()
        assert False
    except ValueError as vException:
        assert str(vException) == (
            "Configuration Greenhouse incomplète : " "GREENHOUSE_BOARD"
        )
