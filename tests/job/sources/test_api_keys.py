"""Tests du chargement des clés d'API depuis l'environnement"""

import pytest

from job.sources.findwork.config import load_config as load_findwork_config
from job.sources.jooble.config import load_config as load_jooble_config


@pytest.mark.parametrize(
    "pLoadConfig, pVariable",
    [
        (load_jooble_config, "JOOBLE_API_KEY"),
        (load_findwork_config, "FINDWORK_API_KEY"),
    ],
)
def test_missing_key_is_reported_by_name(monkeypatch, pLoadConfig, pVariable):
    """Vérifie qu'une clé absente est signalée par le nom de sa variable."""

    monkeypatch.delenv(pVariable, raising=False)

    with pytest.raises(ValueError, match=pVariable):
        pLoadConfig()


@pytest.mark.parametrize(
    "pLoadConfig, pVariable",
    [
        (load_jooble_config, "JOOBLE_API_KEY"),
        (load_findwork_config, "FINDWORK_API_KEY"),
    ],
)
def test_key_is_loaded(monkeypatch, pLoadConfig, pVariable):
    """Vérifie le chargement de la clé lorsqu'elle est renseignée."""

    monkeypatch.setenv(pVariable, "cle-de-test")

    assert pLoadConfig().api_key == "cle-de-test"
