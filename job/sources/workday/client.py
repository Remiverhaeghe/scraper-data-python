"""Client HTTP des sites carrière Workday (API publique de leurs pages)

Chaque entreprise est décrite par « hôte/tenant/site », lu dans l'adresse de
son site carrière : https://valeo.wd3.myworkdayjobs.com/valeo_jobs donne
« valeo.wd3/valeo/valeo_jobs ». Un nom peut précéder : « Airbus=ag.wd3/ag/Airbus ».
"""

from dataclasses import dataclass

from utils.api_client import request_json
from utils.logger import get_logger

logger = get_logger(__name__)

# Maximum accepté par l'API pour une page
PAGE_SIZE = 20

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


@dataclass(frozen=True)
class WorkdaySite:
    """Site carrière Workday d'une entreprise."""

    name: str
    host: str
    tenant: str
    site: str

    @property
    def api_url(self):
        """Adresse de l'API du site."""
        return (
            f"https://{self.host}.myworkdayjobs.com/wday/cxs/{self.tenant}/{self.site}"
        )

    @property
    def page_url(self):
        """Adresse publique du site, base des liens vers les offres."""
        return f"https://{self.host}.myworkdayjobs.com/{self.site}"


def parse_site(pValue):
    """Lit « [Nom=]hôte/tenant/site » ; lève ValueError si le format diffère."""

    vName, _, vPath = str(pValue).strip().rpartition("=")
    vParts = vPath.strip().split("/")

    if len(vParts) != 3 or not all(vParts):
        raise ValueError(
            f"Site Workday « {pValue} » : format attendu hôte/tenant/site, "
            "par exemple valeo.wd3/valeo/valeo_jobs"
        )

    vHost, vTenant, vSite = vParts

    rSite = WorkdaySite(vName.strip() or vTenant.title(), vHost, vTenant, vSite)

    return rSite


def search_jobs(pSite, pKeyword, pOffset, pFacets=None):
    """Retourne une page de résultats : offres, total et filtres proposés."""

    rData = request_json(
        "POST",
        f"{pSite.api_url}/jobs",
        pHeaders=HEADERS,
        pJson={
            "limit": PAGE_SIZE,
            "offset": pOffset,
            "searchText": pKeyword or "",
            "appliedFacets": pFacets or {},
        },
    )

    return rData


def get_job(pSite, pExternalPath):
    """Retourne le détail d'une offre : description, lieu, contrat, entreprise."""

    rData = request_json("GET", f"{pSite.api_url}{pExternalPath}", pHeaders=HEADERS)

    return rData
