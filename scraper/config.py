# ============================================================================
# Configuration commune aux différents scrapers
# ============================================================================


from dataclasses import dataclass

from config import MAX_RESPONSE_SIZE_MB


@dataclass
class ScrapingConfig:
    """
    Configuration commune aux différents scrapers.
    """

    # Nombre maximum d'éléments à récupérer
    max_items: int | None = None

    # Nombre maximum de pages à parcourir
    max_pages: int | None = None

    # Évite de récupérer plusieurs fois le même élément
    avoid_duplicates: bool = True

    # Délai entre deux requêtes HTTP
    delay: float = 0.0

    # Délai d'attente d'une requête HTTP
    timeout: int = 10

    # Taille maximale d'une réponse HTTP en Mo
    max_response_size_mb: float = MAX_RESPONSE_SIZE_MB

    # Nombre de nouvelles tentatives après une erreur HTTP
    retry_count: int = 0

    # Délai entre deux tentatives
    retry_delay: float = 1.0

    @property
    def max_response_size(self) -> int:
        """
        Retourne la taille maximale d'une réponse HTTP en octets.
        """

        rSize = int(
            self.max_response_size_mb * 1024 * 1024
        )

        return rSize

    def validate(self) -> None:
        """
        Vérifie que la configuration est cohérente.
        """

        if (
            self.max_items is not None
            and self.max_items <= 0
        ):
            raise ValueError(
                "max_items doit être supérieur à 0"
            )

        if (
            self.max_pages is not None
            and self.max_pages <= 0
        ):
            raise ValueError(
                "max_pages doit être supérieur à 0"
            )

        if self.delay < 0:
            raise ValueError(
                "delay ne peut pas être négatif"
            )

        if self.timeout <= 0:
            raise ValueError(
                "timeout doit être supérieur à 0"
            )

        if self.max_response_size_mb <= 0:
            raise ValueError(
                "max_response_size_mb doit être supérieur à 0"
            )

        if self.retry_count < 0:
            raise ValueError(
                "retry_count ne peut pas être négatif"
            )

        if self.retry_delay < 0:
            raise ValueError(
                "retry_delay ne peut pas être négatif"
            )