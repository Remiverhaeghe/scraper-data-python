"""Configuration spécifique au scraping des offres d'emploi"""

from dataclasses import dataclass, field

from config import NET_SALARY_RATIO
from job.sources.config import SourceConfig
from scraper.config import ScrapingConfig


@dataclass
class JobScrapingConfig(ScrapingConfig):
    """Configuration spécifique au scraping des offres d'emploi."""

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

    # Configuration de chaque source, indexée par son nom dans le registre
    sources: dict[str, SourceConfig] = field(default_factory=dict)

    # Calcul du salaire net : part du brut conservée et impôt facultatif, en %
    net_salary_ratio: float = NET_SALARY_RATIO
    income_tax_rate: float | None = None

    def validate(self) -> None:
        """Vérifie que la configuration complète est cohérente."""

        # Validation des paramètres communs
        super().validate()

        # Validation des sources
        for vSourceConfig in self.sources.values():
            vSourceConfig.validate()
