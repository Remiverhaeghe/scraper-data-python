# ============================================================================
# Tests du client HTTP de l'API publique Lever
# ============================================================================

from unittest.mock import Mock

import pytest
import requests

from job.sources.lever.client import get_jobs


def test_get_jobs(monkeypatch):
    """
    Vérifie la récupération des offres Lever.
    """

    vResponse = Mock()
    vResponse.json.return_value = [
        {
            "id": "job-1",
            "text": "Python Developer"
        }
    ]

    def mock_get(
        pUrl,
        params,
        headers,
        timeout
    ):
        assert (
            pUrl
            == "https://api.lever.co/v0/postings/example-company"
        )

        assert params["mode"] == "json"
        assert params["limit"] == 50
        assert params["skip"] == 100

        assert headers["Accept"] == "application/json"
        assert timeout == 10

        return vResponse

    monkeypatch.setattr(
        "job.sources.lever.client.requests.get",
        mock_get
    )

    rData = get_jobs(
        "example-company",
        pLimit=50,
        pSkip=100
    )

    assert len(rData) == 1
    assert rData[0]["id"] == "job-1"


def test_get_jobs_without_offset(monkeypatch):
    """
    Vérifie que le scraping commence à l'offset zéro.
    """

    vResponse = Mock()
    vResponse.json.return_value = [
        {
            "id": "job-1"
        }
    ]

    def mock_get(
        pUrl,
        params,
        headers,
        timeout
    ):
        assert params["limit"] == 100
        assert params["skip"] == 0

        return vResponse

    monkeypatch.setattr(
        "job.sources.lever.client.requests.get",
        mock_get
    )

    rData = get_jobs(
        "example-company"
    )

    assert len(rData) == 1


def test_get_jobs_http_error(monkeypatch):
    """
    Vérifie qu'une erreur HTTP est propagée.
    """

    vResponse = Mock()

    vResponse.raise_for_status.side_effect = (
        requests.RequestException("Erreur HTTP")
    )

    def mock_get(
        pUrl,
        params,
        headers,
        timeout
    ):
        return vResponse

    monkeypatch.setattr(
        "job.sources.lever.client.requests.get",
        mock_get
    )

    with pytest.raises(
        requests.RequestException
    ):
        get_jobs(
            "example-company"
        )


def test_get_jobs_invalid_json(monkeypatch):
    """
    Vérifie qu'un JSON invalide provoque une erreur explicite.
    """

    vResponse = Mock()

    vResponse.raise_for_status.return_value = None
    vResponse.json.side_effect = ValueError(
        "JSON invalide"
    )

    def mock_get(
        pUrl,
        params,
        headers,
        timeout
    ):
        return vResponse

    monkeypatch.setattr(
        "job.sources.lever.client.requests.get",
        mock_get
    )

    with pytest.raises(
        ValueError,
        match="La réponse Lever n'est pas un JSON valide"
    ):
        get_jobs(
            "example-company"
        )