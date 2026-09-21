# ============================================================================
# Configuration spécifique au scraping des livres
# ============================================================================


from dataclasses import dataclass

from scraper.config import ScrapingConfig


@dataclass
class BookScrapingConfig(ScrapingConfig):
    """
    Configuration spécifique au scraping des livres.
    """

    # Première page à scraper
    start_page: int = 1

    # Filtre sur le titre
    title: str | None = None

    # Prix maximum d'un livre
    max_price: float | None = None

    # Note minimale d'un livre
    min_rating: int | None = None

    # Type du livre
    book_type: str | None = None

    # Langue du livre
    language: str | None = None

    # Disponibilité du livre
    availability: str | None = None

    def validate(self) -> None:
        """
        Vérifie que la configuration Books est cohérente.
        """

        # Vérification de la configuration commune
        super().validate()

        # Vérification de la première page
        if self.start_page <= 0:
            raise ValueError(
                "start_page doit être supérieur à 0"
            )

        # Vérification du prix maximum
        if self.max_price is not None and self.max_price < 0:
            raise ValueError(
                "max_price ne peut pas être négatif"
            )

        # Vérification de la note minimale
        if self.min_rating is not None and not 1 <= self.min_rating <= 5:
            raise ValueError(
                "min_rating doit être compris entre 1 et 5"
            )


@dataclass
class BookExportConfig:
    """
    Configuration de l'export des livres.
    """

    # Format d'export
    format: str = "csv"

    # Encodage du fichier
    encoding: str = "utf-8"