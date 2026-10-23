"""Tests de l'authentification du tableau de bord"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD
from web.app import app, get_database_file
from web.auth import (
    SESSION_COOKIE,
    SESSION_DURATION,
    LoginRateLimiter,
    create_session_token,
    get_missing_auth_settings,
    hash_password,
    is_safe_redirect,
    read_session_token,
    second_factor,
    verify_password,
)
from utils.totp import compute_code, generate_secret
from web import totp

NOW = datetime(2026, 10, 10, 12, 0)


@pytest.fixture
def anonymous_client(tmp_path, web_login):
    """Fournit un client non connecté, avec un compte configuré."""

    app.dependency_overrides[get_database_file] = lambda: tmp_path / "scraper.db"

    with TestClient(app) as rClient:
        yield rClient

    app.dependency_overrides.clear()


def log_in(pClient, pPassword=TEST_PASSWORD, pNext="/"):
    """Envoie le formulaire de connexion sans suivre la redirection."""

    rResponse = pClient.post(
        "/login",
        data={"username": "admin", "password": pPassword, "next": pNext},
        follow_redirects=False,
    )

    return rResponse


def test_password_hash_is_salted_and_verified():
    """Vérifie l'empreinte salée et sa vérification."""

    vHash = hash_password("correct horse", 1000)

    assert vHash.startswith("pbkdf2_sha256:1000:")
    assert vHash != hash_password("correct horse", 1000)
    assert verify_password("correct horse", vHash)
    assert not verify_password("mauvais", vHash)


@pytest.mark.parametrize("pStoredHash", ["", "md5:1:aa:bb", "pbkdf2_sha256:x:zz:yy"])
def test_unreadable_hash_never_matches(pStoredHash):
    """Vérifie qu'une empreinte illisible refuse toute connexion."""

    assert not verify_password("", pStoredHash)


def test_session_token_rejects_tampering_and_expiry():
    """Vérifie la signature et l'expiration du jeton de session."""

    vToken = create_session_token("secret", "admin", NOW)
    vPayload, vSignature = vToken.split(".")

    assert read_session_token("secret", vToken, NOW)["user"] == "admin"
    assert read_session_token("autre-secret", vToken, NOW) is None
    assert read_session_token("secret", f"{vPayload}x.{vSignature}", NOW) is None
    assert read_session_token("secret", "illisible", NOW) is None
    assert read_session_token("secret", vToken, NOW + SESSION_DURATION) is None


@pytest.mark.parametrize(
    "pTarget, pSafe",
    [
        ("/offers?new=1", True),
        ("", False),
        ("https://exemple.com", False),
        ("//exemple.com", False),
        ("/\\exemple.com", False),
    ],
)
def test_is_safe_redirect(pTarget, pSafe):
    """Vérifie que seules les adresses internes servent de retour après connexion."""

    assert is_safe_redirect(pTarget) is pSafe


def test_rate_limiter_blocks_then_forgets():
    """Vérifie le blocage après trop d'échecs, puis l'oubli après la fenêtre."""

    vLimiter = LoginRateLimiter(pMaxFailures=2, pWindow=timedelta(minutes=15))

    vLimiter.record_failure("1.2.3.4", NOW)
    assert not vLimiter.is_blocked("1.2.3.4", NOW)

    vLimiter.record_failure("1.2.3.4", NOW)
    assert vLimiter.is_blocked("1.2.3.4", NOW)
    assert not vLimiter.is_blocked("5.6.7.8", NOW)
    assert not vLimiter.is_blocked("1.2.3.4", NOW + timedelta(minutes=16))

    vLimiter.record_failure("1.2.3.4", NOW)
    vLimiter.reset("1.2.3.4")
    assert not vLimiter.is_blocked("1.2.3.4", NOW)


def test_pages_require_login(anonymous_client):
    """Vérifie la redirection vers la connexion, en gardant la page demandée."""

    vResponse = anonymous_client.get("/offers?new=1", follow_redirects=False)

    assert vResponse.status_code == 303
    assert vResponse.headers["location"] == "/login?next=/offers%3Fnew%3D1"


def test_htmx_requests_reload_the_login_page(anonymous_client):
    """Vérifie qu'une requête HTMX sans session recharge la page de connexion."""

    vResponse = anonymous_client.get("/offers", headers={"HX-Request": "true"})

    assert vResponse.status_code == 401
    assert vResponse.headers["HX-Redirect"].startswith("/login")


@pytest.mark.parametrize("pPath", ["/login", "/legal", "/license", "/static/style.css"])
def test_public_pages_stay_open(anonymous_client, pPath):
    """Vérifie l'accès sans session à la connexion, aux mentions et aux ressources."""

    assert anonymous_client.get(pPath).status_code == 200


def test_login_page_explains_missing_configuration(anonymous_client, monkeypatch):
    """Vérifie qu'un tableau de bord non configuré reste fermé et l'explique."""

    monkeypatch.delenv("WEB_PASSWORD_HASH")

    assert get_missing_auth_settings() == ["WEB_PASSWORD_HASH"]
    assert "python -m web.password" in anonymous_client.get("/login").text
    assert log_in(anonymous_client).status_code == 503


def test_login_opens_a_protected_session(anonymous_client):
    """Vérifie la connexion, le retour à la page demandée et les options du cookie."""

    vResponse = log_in(anonymous_client, pNext="/history")

    vCookie = vResponse.headers["set-cookie"]

    assert vResponse.status_code == 303
    assert vResponse.headers["location"] == "/history"
    assert "HttpOnly" in vCookie
    assert "SameSite=lax" in vCookie
    assert "Secure" not in vCookie
    assert anonymous_client.get("/", follow_redirects=False).status_code == 200
    assert anonymous_client.get("/login", follow_redirects=False).status_code == 303


def test_secure_cookie_can_be_required(anonymous_client, monkeypatch):
    """Vérifie l'option Secure du cookie, pour un tableau de bord servi en HTTPS."""

    monkeypatch.setenv("WEB_SECURE_COOKIE", "1")

    assert "Secure" in log_in(anonymous_client).headers["set-cookie"]


def test_login_ignores_external_redirects(anonymous_client):
    """Vérifie qu'une adresse de retour externe est remplacée par l'accueil."""

    vResponse = log_in(anonymous_client, pNext="//exemple.com")

    assert vResponse.headers["location"] == "/"


def test_failed_logins_are_limited(anonymous_client):
    """Vérifie le message générique, puis le blocage après cinq échecs."""

    vResponses = [log_in(anonymous_client, "mauvais") for _ in range(6)]

    assert [vResponse.status_code for vResponse in vResponses] == [401] * 5 + [429]
    assert "Identifiant ou mot de passe incorrect." in vResponses[0].text
    assert log_in(anonymous_client).status_code == 429


def test_writes_require_the_csrf_token(anonymous_client):
    """Vérifie le refus d'un formulaire envoyé sans le jeton de la session."""

    log_in(anonymous_client)

    vWithout = anonymous_client.post("/settings", data={"follow_up_days": "9"})
    vWrong = anonymous_client.post(
        "/settings", data={"follow_up_days": "9", "csrf_token": "faux"}
    )

    assert vWithout.status_code == 403
    assert vWrong.status_code == 403


def test_logout_closes_the_session(anonymous_client):
    """Vérifie que la déconnexion supprime la session."""

    log_in(anonymous_client)

    vToken = read_session_token(
        "secret-de-test", anonymous_client.cookies[SESSION_COOKIE], datetime.now()
    )
    vResponse = anonymous_client.post(
        "/logout", data={"csrf_token": vToken["csrf"]}, follow_redirects=False
    )

    assert vResponse.status_code == 303
    assert anonymous_client.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("pPath", ["/legal", "/license"])
def test_public_pages_hide_the_application(anonymous_client, monkeypatch, pPath):
    """Vérifie qu'une page publique n'affiche ni menu ni action sans session."""

    monkeypatch.delenv("WEB_PASSWORD_HASH")

    vText = anonymous_client.get(pPath).text

    assert 'class="sidebar"' not in vText
    assert "Se connecter" in vText
    assert "/offers" not in vText


def test_second_factor_is_required_when_configured(anonymous_client, monkeypatch):
    """Vérifie le code demandé, refusé s'il est faux ou déjà utilisé."""

    vSecret = generate_secret()
    monkeypatch.setenv("WEB_TOTP_SECRET", vSecret)
    monkeypatch.setattr(second_factor, "last_step", None)
    vCode = compute_code(vSecret, int(datetime.now().timestamp() // 30))

    def log_in_with(pCode):
        rResponse = anonymous_client.post(
            "/login",
            data={"username": "admin", "password": TEST_PASSWORD, "code": pCode},
            follow_redirects=False,
        )

        return rResponse

    assert "Code de l'application" in anonymous_client.get("/login").text
    assert log_in_with("000000").status_code == 401
    assert log_in_with(vCode).status_code == 303

    anonymous_client.cookies.clear()

    assert log_in_with(vCode).status_code == 401


def test_totp_setup_writes_the_qr_code(tmp_path, monkeypatch, capsys):
    """Vérifie l'outil d'installation : QR code écrit, ligne du .env affichée."""

    monkeypatch.setattr("sys.argv", ["web.totp", str(tmp_path)])

    totp.main()

    assert (
        (tmp_path / totp.QR_FILE_NAME).read_text(encoding="utf-8").startswith("<?xml")
    )
    assert "WEB_TOTP_SECRET=" in capsys.readouterr().out
