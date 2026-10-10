"""Tests du worker de recherche"""

from types import SimpleNamespace

from gui.search_worker import SearchWorker
from job.sources.aggregator import ScrapingCancelled


class FakeController:
    """Simule le contrôleur en renvoyant un résultat ou en levant une erreur."""

    def __init__(self, pOutcome):
        self.outcome = pOutcome

    def search_jobs(self, pSources, pCriteria, pOnProgress=None, pCancelEvent=None):
        pOnProgress(1, 2, "Adzuna")

        if isinstance(self.outcome, Exception):
            raise self.outcome

        return self.outcome


def run_worker(pOutcome):
    """Exécute un worker et retourne les signaux émis."""

    vEmitted = []

    vWorker = SearchWorker(["adzuna"], {}, FakeController(pOutcome))

    vWorker.progress.connect(lambda *pArgs: vEmitted.append(("progress", pArgs)))
    vWorker.succeeded.connect(lambda pResult: vEmitted.append(("succeeded", pResult)))
    vWorker.cancelled.connect(lambda: vEmitted.append(("cancelled", None)))
    vWorker.failed.connect(lambda pMessage: vEmitted.append(("failed", pMessage)))

    vWorker.run()

    return vEmitted


def test_worker_emits_progress_then_result(qt_application):
    """Vérifie la transmission de la progression puis du résultat."""

    vResult = SimpleNamespace(items=[])

    assert run_worker(vResult) == [
        ("progress", (1, 2, "Adzuna")),
        ("succeeded", vResult),
    ]


def test_worker_emits_cancelled(qt_application):
    """Vérifie qu'un arrêt est signalé comme tel et non comme une erreur."""

    assert run_worker(ScrapingCancelled())[-1] == ("cancelled", None)


def test_worker_emits_failure_message(qt_application):
    """Vérifie qu'une erreur inattendue est transmise à l'interface."""

    assert run_worker(ValueError("Source inconnue"))[-1] == (
        "failed",
        "Source inconnue",
    )


def test_worker_stop_sets_cancel_event(qt_application):
    """Vérifie que l'arrêt positionne l'événement lu par l'agrégateur."""

    vWorker = SearchWorker(["adzuna"], {}, FakeController(None))

    vWorker.stop()

    assert vWorker.cancel_event.is_set()
