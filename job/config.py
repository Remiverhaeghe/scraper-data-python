# ============================================================================
# Configuration spécifique au scraping des offres d'emploi
# ============================================================================


from dataclasses import dataclass

from scraper.config import ScrapingConfig


@dataclass
class JobScrapingConfig(ScrapingConfig):
    """
    Configuration spécifique au scraping des offres d'emploi.
    """

    # Mot-clé recherché dans les offres
    keyword: str | None = None

    # Localisation recherchée
    location: str | None = None

    # Type de contrat recherché
    contract: str | None = None

    # Télétravail recherché
    remote: bool | None = None