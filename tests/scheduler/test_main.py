"""Tests du point d'entrée du planificateur"""

import signal

import pytest

import scheduler.__main__ as entry


@pytest.fixture
def calls(monkeypatch):
    """Remplace la base, les signaux et l'exécution par des enregistrements."""

    rCalls = []

    monkeypatch.setattr(entry, "initialize_database", lambda pFile: None)
    monkeypatch.setattr(
        signal, "signal", lambda pSignal, pHandler: rCalls.append(pSignal)
    )
    monkeypatch.setattr(entry, "run_due_search", lambda *pArgs: rCalls.append("once"))
    monkeypatch.setattr(entry, "run_forever", lambda *pArgs: rCalls.append("loop"))

    return rCalls


@pytest.mark.parametrize("pArguments, pMode", [(["--once"], "once"), ([], "loop")])
def test_main(calls, pArguments, pMode):
    """Vérifie l'arrêt propre sur signal et le choix du mode d'exécution."""

    entry.main(pArguments)

    assert calls == [signal.SIGINT, signal.SIGTERM, pMode]
