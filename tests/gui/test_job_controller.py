"""Tests du contrôleur Jobs"""

import threading
from types import SimpleNamespace

from gui.job_controller import JobController


def test_build_arguments():
    """Vérifie la construction des paramètres Jobs."""

    vController = JobController()

    vArguments = vController.build_arguments(20, "Java", "Lille", ["france-travail"])

    assert vArguments.max_items == 20
    assert vArguments.keyword == "Java"
    assert vArguments.location == "Lille"
    assert vArguments.sources == ["france-travail"]
    assert vArguments.delay == 0.0
    assert vArguments.timeout == 30


def test_search_jobs(monkeypatch):
    """Vérifie que le contrôleur lance le traitement Jobs."""

    vCalls = []

    vResult = SimpleNamespace(items=[{"title": "Développeur Java"}])

    vOnProgress = object()

    vCancelEvent = threading.Event()

    def mock_build_job_config(pArguments):
        """Simule la création de la configuration."""

        vCalls.append("build_config")

        assert pArguments.max_items == 20
        assert pArguments.keyword == "Java"
        assert pArguments.location == "Lille"
        assert pArguments.sources == ["france-travail"]

        return "config"

    def mock_process_jobs(pConfig, pOnProgress=None, pCancelEvent=None):
        """Simule le traitement Jobs."""

        vCalls.append("process_jobs")

        assert pConfig == "config"
        assert pOnProgress is vOnProgress
        assert pCancelEvent is vCancelEvent

        return vResult

    monkeypatch.setattr("gui.job_controller.build_job_config", mock_build_job_config)

    monkeypatch.setattr("gui.job_controller.process_jobs", mock_process_jobs)

    vController = JobController()

    rResult = vController.search_jobs(
        20,
        "Java",
        "Lille",
        ["france-travail"],
        pOnProgress=vOnProgress,
        pCancelEvent=vCancelEvent,
    )

    assert rResult is vResult

    assert vCalls == ["build_config", "process_jobs"]
