"""Exécution d'une recherche d'offres hors du thread de l'interface"""

import threading

from PySide6.QtCore import QObject, Signal, Slot

from gui.job_controller import JobController
from job.sources.aggregator import ScrapingCancelled
from utils.logger import get_logger

logger = get_logger(__name__)


class SearchWorker(QObject):
    """Lance la recherche et rend compte de son avancement par des signaux.

    Le worker est déplacé dans un QThread : ses signaux sont alors transmis
    au thread de l'interface, seul autorisé à modifier les widgets.
    """

    progress = Signal(int, int, str)
    succeeded = Signal(object)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, pSources, pCriteria, pController=None):
        """Prépare la recherche sans la lancer."""
        super().__init__()

        self.sources = pSources
        self.criteria = pCriteria
        self.controller = pController if pController is not None else JobController()
        self.cancel_event = threading.Event()

    @Slot()
    def run(self):
        """Exécute la recherche puis émet le signal correspondant à son issue."""
        try:
            vResult = self.controller.search_jobs(
                self.sources,
                self.criteria,
                pOnProgress=self.progress.emit,
                pCancelEvent=self.cancel_event,
            )

        except ScrapingCancelled:
            self.cancelled.emit()

        except Exception as vException:
            logger.exception("Échec de la recherche Jobs lancée depuis la GUI")

            self.failed.emit(str(vException))

        else:
            self.succeeded.emit(vResult)

    def stop(self):
        """Demande l'arrêt avant la source suivante."""
        self.cancel_event.set()
