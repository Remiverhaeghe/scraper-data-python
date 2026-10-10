"""Contrôleur graphique du traitement des offres d'emploi"""

from job.application import process_jobs
from job.sources.configuration import build_job_config, build_search_arguments
from utils.logger import get_logger

logger = get_logger(__name__)


class JobController:
    """Fait le lien entre la GUI Jobs et le traitement métier."""

    def search_jobs(self, pSources, pCriteria, pOnProgress=None, pCancelEvent=None):
        """Lance une recherche d'offres avec les paramètres de la GUI."""

        vArguments = self.build_arguments(pSources, pCriteria)

        logger.info(
            "Lancement d'une recherche Jobs depuis la GUI sur %s source(s)",
            len(pSources),
        )

        vConfig = build_job_config(vArguments)

        rResult = process_jobs(
            vConfig, pOnProgress=pOnProgress, pCancelEvent=pCancelEvent
        )

        logger.info("Recherche Jobs terminée : %s offre(s)", len(rResult.items))

        return rResult

    def build_arguments(self, pSources, pCriteria):
        """Construit les arguments attendus par la configuration Jobs."""

        rArguments = build_search_arguments(pSources, pCriteria)

        return rArguments
