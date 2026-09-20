# ============================================================================
# Tests de sécurité des URLs
# ============================================================================


import pytest

from utils.security import validate_url

from unittest.mock import patch


def test_validate_public_http_url():
    """
    Vérifie qu'une URL HTTP publique est autorisée.
    """

    vUrl = "http://example.com"
    assert validate_url(vUrl) is True


def test_validate_public_https_url():
    """
    Vérifie qu'une URL HTTPS publique est autorisée.
    """

    vUrl = "https://example.com"
    assert validate_url(vUrl) is True


@pytest.mark.parametrize(
    "pUrl",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "sftp://example.com/file",
        "javascript:alert(1)",
        "data:text/html,test"
    ]
)
def test_validate_rejects_unsupported_scheme(pUrl):
    """
    Vérifie que les schémas non autorisés sont refusés.
    """

    with pytest.raises(ValueError):
        validate_url(pUrl)


@pytest.mark.parametrize(
    "pUrl",
    [
        "http://localhost",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:8080",
        "http://[::1]",
    ]
)
def test_validate_rejects_localhost(pUrl):
    """
    Vérifie que les destinations locales sont refusées.
    """

    with pytest.raises(ValueError):
        validate_url(pUrl)


@pytest.mark.parametrize(
    "pUrl",
    [
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://172.31.255.254",
        "http://192.168.1.1",
        "http://169.254.1.1",
    ]
)
def test_validate_rejects_private_network(pUrl):
    """
    Vérifie que les adresses réseau privées ou locales sont refusées.
    """

    with pytest.raises(ValueError):
        validate_url(pUrl)


@pytest.mark.parametrize(
    "pUrl",
    [
        "",
        "example.com",
        "http://",
        "https://",
        "not-a-url",
    ]
)
def test_validate_rejects_invalid_url(pUrl):
    """
    Vérifie que les URLs invalides sont refusées.
    """

    with pytest.raises(ValueError):
        validate_url(pUrl)

def test_validate_url_rejects_domain_resolving_to_private_ip():
    """
    Vérifie qu'un domaine qui résout vers une IP privée est refusé.
    """

    vUrl = "https://example.com"

    with patch(
        "utils.security.socket.getaddrinfo",
        return_value=[
            (
                2,
                1,
                6,
                "",
                ("192.168.1.10", 0)
            )
        ]
    ):
        with pytest.raises(ValueError):
            validate_url(vUrl)

def test_validate_url_allows_domain_resolving_to_public_ip():
    """
    Vérifie qu'un domaine qui résout vers une IP publique est autorisé.
    """

    vUrl = "https://example.com"

    with patch(
        "utils.security.socket.getaddrinfo",
        return_value=[
            (
                2,
                1,
                6,
                "",
                ("93.184.216.34", 0)
            )
        ]
    ):
        assert validate_url(vUrl) is True