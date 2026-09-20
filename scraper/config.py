# ============================================================================
# Configuration commune aux différents scrapers
# ============================================================================


from dataclasses import dataclass

from config import MAX_RESPONSE_SIZE_MB


@dataclass
class ScrapingConfig:
    """
    Configuration commune à tous les scrapers.
    """

    # Nombre maximum d'éléments à récupérer
    max_items: int | None = None

    # Délai entre deux requêtes HTTP
    delay: float = 0.0

    # Temps maximum d'attente d'une requête HTTP
    timeout: int = 10

    # Taille maximale d'une réponse HTTP en Mo
    max_response_size_mb: float = MAX_RESPONSE_SIZE_MB

    @property
    def max_response_size(self) -> int:
        """
        Retourne la taille maximale d'une réponse HTTP en octets.
        """

        rSize = int(self.max_response_size_mb * 1024 * 1024)
        return rSize

    def validate(self) -> None:
        """
        Vérifie que la configuration est cohérente.
        """

        # Vérification du nombre maximum d'éléments
        if self.max_items is not None and self.max_items <= 0:
            raise ValueError("max_items doit être supérieur à 0")

        # Vérification du délai entre les requêtes
        if self.delay < 0:
            raise ValueError("delay ne peut pas être négatif")

        # Vérification du délai d'attente HTTP
        if self.timeout <= 0:
            raise ValueError("timeout doit être supérieur à 0")

        # Vérification de la taille maximale des réponses HTTP
        if self.max_response_size_mb <= 0:
            raise ValueError(
                "max_response_size_mb doit être supérieur à 0"
            )