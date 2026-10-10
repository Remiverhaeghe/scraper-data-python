"""Tests de construction de la configuration des sources d'emploi"""

from types import SimpleNamespace

from job.sources.configuration import build_france_travail_params, build_job_config


# Vérifie la conversion du mot-clé vers le paramètre France Travail
def test_build_france_travail_params():
    vJobConfig = SimpleNamespace(keyword="Python")

    rParams = build_france_travail_params(vJobConfig)

    assert rParams == {"motsCles": "Python"}


# Vérifie l'absence de paramètre lorsque aucun mot-clé n'est fourni
def test_build_france_travail_params_without_keyword():
    vJobConfig = SimpleNamespace(keyword=None)

    rParams = build_france_travail_params(vJobConfig)

    assert rParams == {}


# Vérifie la construction d'une configuration sans source
def test_build_job_config_without_sources():
    vArguments = SimpleNamespace(
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
        sources=None,
    )

    rConfig = build_job_config(vArguments)

    assert rConfig.france_travail.enabled is False
    assert rConfig.greenhouse.enabled is False
    assert rConfig.lever.enabled is False
