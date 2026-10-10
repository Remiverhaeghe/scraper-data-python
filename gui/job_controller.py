"""Contrôleur graphique du traitement des offres d'emploi"""

from types import SimpleNamespace

from job.application import process_jobs
from job.sources.configuration import build_job_config
from utils.logger import get_logger

logger = get_logger(__name__)


class JobController:
    """Fait le lien entre la GUI Jobs et le traitement métier."""

    def search_jobs(self, pMaxItems, pKeyword, pLocation, pSources):
        """Lance une recherche d'offres avec les paramètres de la GUI."""

        vArguments = self.build_arguments(pMaxItems, pKeyword, pLocation, pSources)

        logger.info("Lancement d'une recherche Jobs depuis la GUI")

        logger.info("Construction de la configuration Jobs")

        vConfig = build_job_config(vArguments)

        logger.info("Configuration Jobs construite avec succès")

        logger.info("Lancement du traitement Jobs")

        rResult = process_jobs(vConfig)

        logger.info("Recherche Jobs terminée : %s offre(s)", len(rResult.items))

        return rResult

    def build_arguments(self, pMaxItems, pKeyword, pLocation, pSources):
        """Construit les arguments attendus par la configuration Jobs."""

        vArguments = SimpleNamespace(
            max_items=pMaxItems,
            delay=0.0,
            timeout=30,
            max_pages=None,
            keyword=pKeyword,
            location=pLocation,
            max_distance_km=None,
            contract=None,
            min_salary=None,
            max_salary=None,
            remote=None,
            min_remote_days=None,
            metro_required=None,
            max_metro_distance_km=None,
            education=None,
            skills=None,
            missions=None,
            sources=pSources,
        )

        return vArguments
