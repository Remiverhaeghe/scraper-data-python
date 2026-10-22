"""Déclaration de la source SmartRecruiters"""

from job.sources.config import SourceDefinition, scrape_each
from job.sources.smartrecruiters.config import load_config
from job.sources.smartrecruiters.service import scrape_jobs


def load_parameters(pJobConfig):
    """Construit les paramètres : entreprises suivies, pays et critères."""

    vConfig = load_config()

    rParameters = {
        "companies": vConfig.companies,
        "country": vConfig.country,
        "keyword": pJobConfig.keyword,
        "location": pJobConfig.location,
    }

    return rParameters


def scrape(pParameters, pJobConfig):
    """Récupère les offres de chaque entreprise suivie."""

    rDataFrame = scrape_each(
        pParameters["companies"],
        lambda pCompany, pMaxItems: scrape_jobs(
            pCompany,
            pParameters["country"],
            pParameters["keyword"],
            pParameters["location"],
            pMaxItems,
        ),
        pJobConfig.max_items,
        "SmartRecruiters",
    )

    return rDataFrame


SOURCE = SourceDefinition(
    name="smartrecruiters",
    label="SmartRecruiters",
    load_parameters=load_parameters,
    scrape=scrape,
    category="company",
)
