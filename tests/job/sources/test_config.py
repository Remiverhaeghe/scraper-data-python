"""Tests de la configuration commune des sources"""

import pytest

from job.config import JobScrapingConfig
from job.sources.config import SourceConfig, SourceDefinition


def test_source_disabled():
    """Vérifie qu'une source désactivée est valide."""

    vConfig = SourceConfig()

    vConfig.validate()


def test_source_api_only():
    """Vérifie qu'une source API uniquement est valide."""

    vConfig = SourceConfig(
        enabled=True, api_available=True, html_available=False, mode="api"
    )

    vConfig.validate()


def test_source_html_only():
    """Vérifie qu'une source HTML uniquement est valide."""

    vConfig = SourceConfig(
        enabled=True, api_available=False, html_available=True, mode="html"
    )

    vConfig.validate()


def test_source_api_and_html():
    """Vérifie qu'une source proposant les deux modes est valide."""

    vConfig = SourceConfig(
        enabled=True, api_available=True, html_available=True, mode="api"
    )

    vConfig.validate()


def test_enabled_source_without_mode():
    """Vérifie qu'une source active doit avoir un mode."""

    vConfig = SourceConfig(enabled=True, api_available=True, html_available=True)

    with pytest.raises(ValueError, match="Le mode doit être"):
        vConfig.validate()


def test_enabled_source_without_available_mode():
    """Vérifie qu'une source active doit proposer au moins
    un mode de récupération.
    """

    vConfig = SourceConfig(enabled=True)

    with pytest.raises(ValueError, match="au moins un mode"):
        vConfig.validate()


def test_api_mode_not_available():
    """Vérifie qu'une source ne peut pas utiliser une API
    qui n'est pas disponible.
    """

    vConfig = SourceConfig(
        enabled=True, api_available=False, html_available=True, mode="api"
    )

    with pytest.raises(ValueError, match="mode API n'est pas disponible"):
        vConfig.validate()


def test_html_mode_not_available():
    """Vérifie qu'une source ne peut pas utiliser HTML
    si HTML n'est pas disponible.
    """

    vConfig = SourceConfig(
        enabled=True, api_available=True, html_available=False, mode="html"
    )

    with pytest.raises(ValueError, match="mode HTML n'est pas disponible"):
        vConfig.validate()


def test_disabled_source_with_mode():
    """Vérifie qu'une source désactivée ne peut pas avoir
    de mode sélectionné.
    """

    vConfig = SourceConfig(
        enabled=False, api_available=True, html_available=True, mode="api"
    )

    with pytest.raises(ValueError, match="source désactivée"):
        vConfig.validate()


def test_job_config_has_no_source_by_default():
    """Vérifie qu'aucune source n'est configurée par défaut."""

    vConfig = JobScrapingConfig()

    assert vConfig.sources == {}


def test_job_config_sources_are_independent():
    """Vérifie que chaque source possède sa propre configuration."""

    vConfig = JobScrapingConfig()

    vConfig.sources["france-travail"] = SourceConfig(
        enabled=True, api_available=True, mode="api"
    )
    vConfig.sources["lever"] = SourceConfig()

    assert vConfig.sources["france-travail"].enabled is True
    assert vConfig.sources["lever"].enabled is False


def test_job_config_sources_validation():
    """Vérifie que la validation des sources est appelée."""

    vConfig = JobScrapingConfig(sources={"lever": SourceConfig(enabled=True)})

    with pytest.raises(ValueError, match="au moins un mode"):
        vConfig.validate()


def test_source_definition_lists_missing_settings(monkeypatch):
    """Vérifie que seules les variables absentes ou vides sont signalées."""

    monkeypatch.setenv("TEST_SOURCE_ID", "identifiant")
    monkeypatch.setenv("TEST_SOURCE_KEY", "")
    monkeypatch.delenv("TEST_SOURCE_SITE", raising=False)

    vDefinition = SourceDefinition(
        name="test",
        label="Test",
        load_parameters=None,
        scrape=None,
        settings=("TEST_SOURCE_ID", "TEST_SOURCE_KEY", "TEST_SOURCE_SITE"),
    )

    assert vDefinition.get_missing_settings() == [
        "TEST_SOURCE_KEY",
        "TEST_SOURCE_SITE",
    ]


@pytest.mark.parametrize(
    "pAvailable, pSettings, pExpected",
    [
        (True, (), None),
        (False, (), "indisponible"),
        (True, ("TEST_MISSING_SETTING",), "non configurée"),
    ],
)
def test_get_unavailability_reason(monkeypatch, pAvailable, pSettings, pExpected):
    """Vérifie la raison affichée à côté d'une source non sélectionnable."""

    monkeypatch.delenv("TEST_MISSING_SETTING", raising=False)

    vDefinition = SourceDefinition(
        name="test",
        label="Test",
        load_parameters=None,
        scrape=None,
        available=pAvailable,
        settings=pSettings,
    )

    assert vDefinition.get_unavailability_reason() == pExpected
