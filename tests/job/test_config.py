# ============================================================================
# Tests de la configuration du scraping des offres d'emploi
# ============================================================================

import pytest

from job.config import JobScrapingConfig


def test_job_scraping_config():
    """
    Vérifie la création d'une configuration Jobs.
    """

    vConfig = JobScrapingConfig(
        max_items=50,
        delay=1.0,
        timeout=30,
        keyword="Python",
        location="Lille",
        contract="CDI",
        remote=True
    )

    assert vConfig.max_items == 50
    assert vConfig.delay == 1.0
    assert vConfig.timeout == 30
    assert vConfig.keyword == "Python"
    assert vConfig.location == "Lille"
    assert vConfig.contract == "CDI"
    assert vConfig.remote is True


def test_job_scraping_config_with_default_values():
    """
    Vérifie les valeurs par défaut de la configuration Jobs.
    """

    vConfig = JobScrapingConfig()

    assert vConfig.max_items is None
    assert vConfig.delay == 0.0
    assert vConfig.timeout == 10
    assert vConfig.keyword is None
    assert vConfig.location is None
    assert vConfig.contract is None
    assert vConfig.remote is None

def test_job_scraping_config_validates_common_values():
    """
    Vérifie que la configuration Jobs utilise les validations communes.
    """

    vConfig = JobScrapingConfig(
        max_items=0
    )

    with pytest.raises(
        ValueError,
        match="max_items"
    ):
        vConfig.validate()