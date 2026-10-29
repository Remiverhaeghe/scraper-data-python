"""Configuration commune des sources d'emploi"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd
import requests

from job.csv_schema import JOB_COLUMNS
from utils.logger import get_logger

logger = get_logger(__name__)

# Catégories des sources, dans l'ordre d'affichage : le lieu des offres qu'elles
# publient, ou les pages carrière d'entreprises choisies.
SOURCE_CATEGORIES = {
    "france": "France",
    "company": "Pages carrière",
    "international": "International",
    "remote": "Télétravail",
}


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


# Une page carrière sans entreprise suivie n'est pas mal configurée : elle attend
# simplement qu'on lui en ajoute une.
NO_COMPANY_REASON = "aucune entreprise suivie"


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

    # Catégorie affichée et filtrable, parmi SOURCE_CATEGORIES
    category: str = "international"

    # Plateforme de pages carrière (job/company_pages.py) : la source est
    # configurée dès qu'elle suit des entreprises, réglées dans Paramètres ou .env.
    companies: str | None = None

    def get_missing_settings(self):
        """Retourne les variables d'environnement requises non renseignées."""

        if self.companies:
            # pylint: disable=import-outside-toplevel
            from job.company_pages import load_company_list

            return [] if load_company_list(self.companies) else list(self.settings)

        rMissing = [vName for vName in self.settings if not os.getenv(vName)]

        return rMissing

    def get_unavailability_reason(self):
        """Retourne pourquoi la source ne peut pas être utilisée, ou None."""

        rReason = None

        if not self.available:
            rReason = "indisponible"

        elif self.get_missing_settings():
            rReason = NO_COMPANY_REASON if self.companies else "non configurée"

        return rReason

    def describe_missing(self):
        """Retourne ce qu'il reste à faire pour utiliser la source, ou None.

        Seuls les noms des variables sont donnés, jamais leurs valeurs.
        """

        vMissing = self.get_missing_settings()

        if not vMissing:
            rText = None
        elif self.companies:
            rText = "Aucune entreprise suivie : à ajouter dans Paramètres, Pages carrière suivies"
        else:
            rText = "À renseigner dans .env : " + ", ".join(vMissing)

        return rText


def scrape_each(pNames, pScrape, pMaxItems, pLabel):
    """Récupère les offres de plusieurs sites d'une source, séparés par des virgules.

    Un site en erreur, mal orthographié par exemple, n'empêche pas les autres ;
    l'erreur remonte seulement si aucun site n'a répondu.
    """

    vFrames = []
    vError = None

    vNames = [vName.strip() for vName in pNames.split(",") if vName.strip()]

    for vIndex, vName in enumerate(vNames, start=1):
        vRemaining = None if pMaxItems is None else pMaxItems - sum(map(len, vFrames))

        if vRemaining is not None and vRemaining <= 0:
            logger.info(
                "%s : limite d'offres atteinte, %s site(s) non lu(s)",
                pLabel,
                len(vNames) - vIndex + 1,
            )
            break

        # Une source peut lire plusieurs minutes par grand site : le rang montre
        # dans le journal que la recherche avance.
        logger.info("%s : site %s (%s/%s)", pLabel, vName, vIndex, len(vNames))

        try:
            vFrames.append(pScrape(vName, vRemaining))

        except (requests.RequestException, ValueError) as vException:
            logger.error("%s : site %s ignoré : %s", pLabel, vName, vException)
            vError = vException

    if not vFrames and vError is not None:
        raise vError

    rDataFrame = (
        pd.concat(vFrames, ignore_index=True)
        if vFrames
        else pd.DataFrame(columns=JOB_COLUMNS)
    )

    return rDataFrame
