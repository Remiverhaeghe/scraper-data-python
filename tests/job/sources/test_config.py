# ============================================================================
# Tests de la configuration commune des sources
# ============================================================================

import pytest

from job.sources.config import SourceConfig
from job.config import JobScrapingConfig
from job.sources.config import SourceConfig


def test_source_disabled():
    """
    Vérifie qu'une source désactivée est valide.
    """

    vConfig = SourceConfig()

    vConfig.validate()


def test_source_api_only():
    """
    Vérifie qu'une source API uniquement est valide.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=True,
        html_available=False,
        mode="api"
    )

    vConfig.validate()


def test_source_html_only():
    """
    Vérifie qu'une source HTML uniquement est valide.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=False,
        html_available=True,
        mode="html"
    )

    vConfig.validate()


def test_source_api_and_html():
    """
    Vérifie qu'une source proposant les deux modes est valide.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=True,
        html_available=True,
        mode="api"
    )

    vConfig.validate()


def test_enabled_source_without_mode():
    """
    Vérifie qu'une source active doit avoir un mode.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=True,
        html_available=True
    )

    with pytest.raises(
        ValueError,
        match="Le mode doit être"
    ):
        vConfig.validate()


def test_enabled_source_without_available_mode():
    """
    Vérifie qu'une source active doit proposer au moins
    un mode de récupération.
    """

    vConfig = SourceConfig(
        enabled=True
    )

    with pytest.raises(
        ValueError,
        match="au moins un mode"
    ):
        vConfig.validate()


def test_api_mode_not_available():
    """
    Vérifie qu'une source ne peut pas utiliser une API
    qui n'est pas disponible.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=False,
        html_available=True,
        mode="api"
    )

    with pytest.raises(
        ValueError,
        match="mode API n'est pas disponible"
    ):
        vConfig.validate()


def test_html_mode_not_available():
    """
    Vérifie qu'une source ne peut pas utiliser HTML
    si HTML n'est pas disponible.
    """

    vConfig = SourceConfig(
        enabled=True,
        api_available=True,
        html_available=False,
        mode="html"
    )

    with pytest.raises(
        ValueError,
        match="mode HTML n'est pas disponible"
    ):
        vConfig.validate()


def test_disabled_source_with_mode():
    """
    Vérifie qu'une source désactivée ne peut pas avoir
    de mode sélectionné.
    """

    vConfig = SourceConfig(
        enabled=False,
        api_available=True,
        html_available=True,
        mode="api"
    )

    with pytest.raises(
        ValueError,
        match="source désactivée"
    ):
        vConfig.validate()

def test_job_config_has_sources():
    """
    Vérifie que les sources sont disponibles dans la configuration.
    """

    vConfig = JobScrapingConfig()

    assert isinstance(
        vConfig.france_travail,
        SourceConfig
    )

    assert isinstance(
        vConfig.greenhouse,
        SourceConfig
    )

    assert isinstance(
        vConfig.lever,
        SourceConfig
    )


def test_job_config_sources_are_independent():
    """
    Vérifie que chaque source possède sa propre configuration.
    """

    vConfig = JobScrapingConfig()

    vConfig.france_travail.enabled = True
    vConfig.france_travail.api_available = True
    vConfig.france_travail.mode = "api"

    assert vConfig.france_travail.enabled is True
    assert vConfig.greenhouse.enabled is False
    assert vConfig.lever.enabled is False


def test_job_config_sources_validation():
    """
    Vérifie que la validation des sources est appelée.
    """

    vConfig = JobScrapingConfig(
        france_travail=SourceConfig(
            enabled=True,
            api_available=True,
            mode="api"
        )
    )

    vConfig.validate()