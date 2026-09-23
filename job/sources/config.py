# ============================================================================
# Configuration commune des sources d'emploi
# ============================================================================

from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    """
    Configuration générique d'une source d'emploi.
    """

    # Indique si la source doit être utilisée
    enabled: bool = False

    # Capacités proposées par la source
    api_available: bool = False
    html_available: bool = False

    # Mode sélectionné pour la récupération
    mode: str | None = None

    # Paramètres spécifiques à la source
    parameters: dict = field(
        default_factory=dict
    )

    def validate(self):
        """
        Vérifie que la configuration de la source est cohérente.
        """

        if not self.enabled:
            if self.mode is not None:
                raise ValueError(
                    "Une source désactivée ne peut pas avoir de mode."
                )

            return

        if not self.api_available and not self.html_available:
            raise ValueError(
                "Une source active doit proposer au moins un mode."
            )

        if self.mode not in ("api", "html"):
            raise ValueError(
                "Le mode doit être 'api' ou 'html'."
            )

        if self.mode == "api" and not self.api_available:
            raise ValueError(
                "Le mode API n'est pas disponible pour cette source."
            )

        if self.mode == "html" and not self.html_available:
            raise ValueError(
                "Le mode HTML n'est pas disponible pour cette source."
            )