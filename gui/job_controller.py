"""Contrôleur graphique du traitement des offres d'emploi"""

from types import SimpleNamespace

from job.application import process_jobs
from job.sources.configuration import build_job_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Critères attendus par build_job_config, avec les valeurs par défaut de la GUI
DEFAULT_CRITERIA = {
    "max_items": None,
    "delay": 0.0,
    "timeout": 30,
    "max_pages": None,
    "keyword": None,
    "location": None,
    "max_distance_km": None,
    "contract": None,
    "min_salary": None,
    "max_salary": None,
    "remote": None,
    "min_remote_days": None,
    "metro_required": None,
    "max_metro_distance_km": None,
    "education": None,
    "skills": None,
    "missions": None,
    "exclude_keywords": None,
}


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

        vUnknown = sorted(set(pCriteria) - set(DEFAULT_CRITERIA))

        if vUnknown:
            raise ValueError(f"Critère(s) de recherche inconnu(s) : {vUnknown}")

        rArguments = SimpleNamespace(
            **{**DEFAULT_CRITERIA, **pCriteria}, sources=pSources
        )

        return rArguments
