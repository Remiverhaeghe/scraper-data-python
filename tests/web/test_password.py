"""Tests de la génération de l'empreinte du mot de passe"""

import pytest

import web.password as password
from web.auth import hash_password, verify_password


def answer(pMonkeypatch, *pInputs):
    """Simule les saisies successives du mot de passe."""

    vInputs = iter(pInputs)

    pMonkeypatch.setattr(password.getpass, "getpass", lambda pPrompt: next(vInputs))


@pytest.mark.parametrize(
    "pInputs, pExpected",
    [
        (["court"], "trop court"),
        (["mot-de-passe-long", "different-du-premier"], "différentes"),
    ],
)
def test_main_refuses_invalid_input(monkeypatch, capsys, pInputs, pExpected):
    """Vérifie le refus d'un mot de passe court ou mal confirmé."""

    answer(monkeypatch, *pInputs)

    password.main()

    vOutput = capsys.readouterr().out

    assert pExpected in vOutput
    assert "WEB_PASSWORD_HASH" not in vOutput


def test_main_prints_hash_and_secret(monkeypatch, capsys):
    """Vérifie les lignes à copier dans .env, sans le mot de passe en clair."""

    answer(monkeypatch, "mot-de-passe-long", "mot-de-passe-long")
    monkeypatch.setattr(
        password, "hash_password", lambda pPassword: hash_password(pPassword, 1000)
    )

    password.main()

    vOutput = capsys.readouterr().out
    vValues = dict(
        vLine.split("=", 1) for vLine in vOutput.splitlines() if "=" in vLine
    )

    assert verify_password("mot-de-passe-long", vValues["WEB_PASSWORD_HASH"])
    assert len(vValues["WEB_SESSION_SECRET"]) >= 32
    assert "mot-de-passe-long" not in vOutput
