"""Tests de la configuration Lever"""

from job.sources.lever.config import LeverConfig, load_config


def test_load_config(monkeypatch):
    """Vérifie le chargement correct de la configuration Lever"""
    monkeypatch.setenv("LEVER_SITE", "example-site")

    rConfig = load_config()

    assert isinstance(rConfig, LeverConfig)

    assert rConfig.site == "example-site"


def test_load_config_without_site(monkeypatch):
    """Vérifie l'erreur lorsqu'aucun site Lever n'est configuré"""
    monkeypatch.delenv("LEVER_SITE", raising=False)

    try:
        load_config()
        assert False
    except ValueError as vException:
        assert str(vException) == ("Configuration Lever incomplète : " "LEVER_SITE")
