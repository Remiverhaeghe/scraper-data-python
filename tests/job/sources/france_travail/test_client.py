# ============================================================================
# Tests du client France Travail
# ============================================================================

import requests

from job.sources.france_travail.client import search_jobs


class FakeConfig:
    """
    Configuration fictive utilisée par les tests.
    """

    api_base_url = "https://example.com/"


def test_search_jobs(monkeypatch):
    """
    Vérifie l'appel de recherche des offres.
    """

    vCalls = []

    def mock_get(
        pUrl,
        headers,
        params,
        timeout
    ):
        vCalls.append(
            {
                "url": pUrl,
                "headers": headers,
                "params": params,
                "timeout": timeout
            }
        )

        class FakeResponse:

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "resultats": [
                        {
                            "id": "123"
                        }
                    ]
                }

        rResponse = FakeResponse()
        return rResponse

    def mock_get_access_token(pConfig):
        return "token-test"

    monkeypatch.setattr(
        requests,
        "get",
        mock_get
    )

    monkeypatch.setattr(
        "job.sources.france_travail.client.get_access_token",
        mock_get_access_token
    )

    vParams = {
        "motsCles": "python",
        "commune": "59000"
    }

    rData = search_jobs(
        FakeConfig(),
        vParams
    )

    assert rData == {
        "resultats": [
            {
                "id": "123"
            }
        ]
    }

    assert vCalls[0]["url"] == (
        "https://example.com/"
        "offresdemploi/v2/offres/search"
    )

    assert vCalls[0]["headers"] == {
        "Authorization": "Bearer token-test",
        "Accept": "application/json"
    }

    assert vCalls[0]["params"] == vParams
    assert vCalls[0]["timeout"] == 10


def test_search_jobs_http_error(monkeypatch):
    """
    Vérifie la propagation d'une erreur HTTP.
    """

    def mock_get_access_token(pConfig):
        return "token-test"

    def mock_get(*args, **kwargs):
        raise requests.RequestException(
            "Erreur HTTP"
        )

    monkeypatch.setattr(
        "job.sources.france_travail.client.get_access_token",
        mock_get_access_token
    )

    monkeypatch.setattr(
        requests,
        "get",
        mock_get
    )

    try:
        search_jobs(
            FakeConfig(),
            {}
        )
        assert False
    except requests.RequestException:
        assert True