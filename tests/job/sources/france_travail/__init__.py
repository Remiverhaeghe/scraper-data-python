# ============================================================================
# Configuration de la source France Travail
# ============================================================================

from dataclasses import dataclass


@dataclass
class FranceTravailConfig:
    """
    Configuration de l'accès à l'API France Travail.
    """

    client_id: str
    client_secret: str

    token_url: str = (
        "https://entreprise.francetravail.fr/"
        "connexion/oauth2/access_token?realm=/partenaire"
    )

    api_base_url: str = (
        "https://api.francetravail.io/"
    )

    scope: str = (
        "api_offresdemploiv2 o2dsoffre"
    )