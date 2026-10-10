"""Tests du contrôleur Jobs"""

import threading
from types import SimpleNamespace

import pytest

from gui.job_controller import JobController


def test_build_arguments():
    """Vérifie que les critères complètent les valeurs par défaut."""

    vController = JobController()

    vArguments = vController.build_arguments(
        ["adzuna"], {"keyword": "Java", "contract": "CDI", "min_salary": 2500}
    )

    assert vArguments.sources == ["adzuna"]
    assert vArguments.keyword == "Java"
    assert vArguments.contract == "CDI"
    assert vArguments.min_salary == 2500
    assert vArguments.location is None
    assert vArguments.delay == 0.0
    assert vArguments.timeout == 30


def test_build_arguments_rejects_unknown_criteria():
    """Vérifie qu'une faute de frappe dans un critère est signalée."""

    with pytest.raises(ValueError, match="keywords"):
        JobController().build_arguments(["adzuna"], {"keywords": "Java"})


def test_search_jobs(monkeypatch):
    """Vérifie que le contrôleur lance le traitement Jobs."""

    vCalls = []

    vResult = SimpleNamespace(items=[{"title": "Développeur Java"}])

    vOnProgress = object()

    vCancelEvent = threading.Event()

    def mock_build_job_config(pArguments):
        """Simule la création de la configuration."""

        vCalls.append("build_config")

        assert pArguments.keyword == "Java"
        assert pArguments.sources == ["adzuna"]

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

    rResult = JobController().search_jobs(
        ["adzuna"],
        {"keyword": "Java"},
        pOnProgress=vOnProgress,
        pCancelEvent=vCancelEvent,
    )

    assert rResult is vResult

    assert vCalls == ["build_config", "process_jobs"]
