# ============================================================================
# Configuration spécifique au scraping des offres d'emploi
# ============================================================================

from dataclasses import dataclass, field

from job.sources.config import SourceConfig
from scraper.config import ScrapingConfig


@dataclass
class JobScrapingConfig(ScrapingConfig):
    """
    Configuration spécifique au scraping des offres d'emploi.
    """

    # Recherche textuelle
    keyword: str | None = None

    # Localisation
    location: str | None = None
    max_distance_km: float | None = None

    # Type de contrat
    contract: str | None = None

    # Salaire
    min_salary: float | None = None
    max_salary: float | None = None

    # Télétravail
    remote: bool | None = None
    min_remote_days: int | None = None

    # Accessibilité en métro
    metro_required: bool | None = None
    max_metro_distance_km: float | None = None

    # Formation
    education: str | None = None

    # Compétences recherchées
    skills: list[str] | None = None

    # Missions recherchées
    missions: list[str] | None = None

    # Sources
    france_travail: SourceConfig = field(
        default_factory=SourceConfig
    )

    greenhouse: SourceConfig = field(
        default_factory=SourceConfig
    )

    lever: SourceConfig = field(
        default_factory=SourceConfig
    )

    def validate(self):
        """
        Vérifie que la configuration complète est cohérente.
        """

        # Validation des paramètres communs
        super().validate()

        # Validation des sources
        self.france_travail.validate()
        self.greenhouse.validate()
        self.lever.validate()