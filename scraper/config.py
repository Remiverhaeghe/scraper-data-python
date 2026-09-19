# ============================================================================
# Configuration commune aux différents scrapers
# ============================================================================


from dataclasses import dataclass


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