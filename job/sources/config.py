"""Configuration commune des sources d'emploi"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    """Configuration générique d'une source d'emploi."""

    # Indique si la source doit être utilisée
    enabled: bool = False

    # Capacités proposées par la source
    api_available: bool = False
    html_available: bool = False

    # Mode sélectionné pour la récupération
    mode: str | None = None

    # Paramètres spécifiques à la source
    parameters: dict = field(default_factory=dict)

    def validate(self) -> None:
        """Vérifie que la configuration de la source est cohérente."""

        if not self.enabled:
            if self.mode is not None:
                raise ValueError("Une source désactivée ne peut pas avoir de mode.")

            return

        if not self.api_available and not self.html_available:
            raise ValueError("Une source active doit proposer au moins un mode.")

        if self.mode not in ("api", "html"):
            raise ValueError("Le mode doit être 'api' ou 'html'.")

        if self.mode == "api" and not self.api_available:
            raise ValueError("Le mode API n'est pas disponible pour cette source.")

        if self.mode == "html" and not self.html_available:
            raise ValueError("Le mode HTML n'est pas disponible pour cette source.")


@dataclass(frozen=True)
class SourceDefinition:
    """Description d'une source d'emploi utilisable par l'application."""

    # Identifiant utilisé dans la configuration et la CLI
    name: str

    # Libellé affiché à l'utilisateur
    label: str

    # Charge les paramètres de la source à partir des critères de recherche
    load_parameters: Callable

    # Récupère les offres à partir des paramètres chargés et des critères
    scrape: Callable

    # Une source indisponible reste affichée mais ne peut pas être sélectionnée
    available: bool = True

    # Variables d'environnement indispensables, comme les clés d'API
    settings: tuple[str, ...] = ()

    def get_missing_settings(self):
        """Retourne les variables d'environnement requises non renseignées."""

        rMissing = [vName for vName in self.settings if not os.getenv(vName)]

        return rMissing

    def get_unavailability_reason(self):
        """Retourne pourquoi la source ne peut pas être utilisée, ou None."""

        rReason = None

        if not self.available:
            rReason = "indisponible"

        elif self.get_missing_settings():
            rReason = "non configurée"

        return rReason
