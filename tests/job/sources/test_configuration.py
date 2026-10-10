"""Tests de construction de la configuration des sources d'emploi"""

from types import SimpleNamespace

import pytest

from job.sources.configuration import build_job_config
from job.sources.france_travail.source import build_params
from job.sources.greenhouse.config import GreenhouseConfig
from job.sources.registry import SOURCES


# Vérifie la conversion du mot-clé vers le paramètre France Travail
def test_build_france_travail_params():
    vJobConfig = SimpleNamespace(keyword="Python")

    rParams = build_params(vJobConfig)

    assert rParams == {"motsCles": "Python"}


# Vérifie l'absence de paramètre lorsque aucun mot-clé n'est fourni
def test_build_france_travail_params_without_keyword():
    vJobConfig = SimpleNamespace(keyword=None)

    rParams = build_params(vJobConfig)

    assert rParams == {}


def build_arguments(pSources):
    """Construit des arguments minimaux pour la configuration Jobs."""

    rArguments = SimpleNamespace(
        max_items=None,
        delay=0.0,
        timeout=10,
        max_pages=None,
        keyword=None,
        location=None,
        max_distance_km=None,
        contract=None,
        min_salary=None,
        max_salary=None,
        remote=None,
        min_remote_days=None,
        metro_required=None,
        max_metro_distance_km=None,
        education=None,
        skills=None,
        missions=None,
        exclude_keywords=None,
        sources=pSources,
    )

    return rArguments


# Vérifie que toutes les sources du registre sont désactivées par défaut
def test_build_job_config_without_sources():
    rConfig = build_job_config(build_arguments(None))

    assert set(rConfig.sources) == set(SOURCES)

    assert all(not vSource.enabled for vSource in rConfig.sources.values())


# Vérifie qu'une source activée charge ses paramètres via le registre
def test_build_job_config_loads_enabled_source(monkeypatch):
    monkeypatch.setattr(
        "job.sources.greenhouse.source.load_config",
        lambda: GreenhouseConfig(board="test-board"),
    )

    rConfig = build_job_config(build_arguments(["greenhouse"]))

    assert rConfig.sources["greenhouse"].enabled is True
    assert rConfig.sources["greenhouse"].mode == "api"
    assert rConfig.sources["greenhouse"].parameters == {"board": "test-board"}
    assert rConfig.sources["remotive"].enabled is False


# Vérifie qu'une configuration manquante bloque la construction
def test_build_job_config_fails_when_source_config_is_missing(monkeypatch):
    monkeypatch.delenv("GREENHOUSE_BOARD", raising=False)

    with pytest.raises(ValueError, match="GREENHOUSE_BOARD"):
        build_job_config(build_arguments(["greenhouse"]))


# Vérifie qu'une source indisponible ne peut pas être sélectionnée
def test_build_job_config_rejects_unavailable_source():
    with pytest.raises(ValueError, match="indisponible"):
        build_job_config(build_arguments(["france-travail"]))
