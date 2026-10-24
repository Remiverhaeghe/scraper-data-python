"""Déclaration de la source Workday"""

from job.company_pages import PLATFORMS, load_company_list
from job.sources.config import SourceDefinition, scrape_each
from job.sources.workday.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les paramètres : sites suivis et critères."""

    rParameters = {
        "companies": load_company_list("workday"),
        "keyword": pJobConfig.keyword,
        "location": pJobConfig.location,
    }

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres de chaque site carrière suivi."""

    rDataFrame = scrape_each(
        pParameters["companies"],
        lambda pSite, pMaxItems: scrape_jobs(
            pSite,
            pParameters["keyword"],
            pParameters["location"],
            pMaxItems,
            pKnown=(pJobConfig.known_descriptions or {}).get("workday"),
        ),
        pJobConfig.max_items,
        "Workday",
    )

    return rDataFrame


# Grands groupes dont le site carrière est sur Workday : Paramètres, .env ou
# liste par défaut (job/company_pages.py)
SOURCE = SourceDefinition(
    name="workday",
    label="Workday",
    load_parameters=load_parameters,
    scrape=scrape,
    settings=(PLATFORMS["workday"][1],),
    category="company",
    companies="workday",
)
