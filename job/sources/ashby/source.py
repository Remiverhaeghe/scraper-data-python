"""Déclaration de la source Ashby"""

from job.sources.ashby.client import get_jobs
from job.sources.ashby.parser import parse_jobs
from job.sources.boards import define_board_source

# Entreprises suivies par défaut, vérifiées sur l'API, avec des offres en France
DEFAULT_COMPANIES = "alan,pennylane,ledger,photoroom,dust,lemlist,nabla"

SOURCE = define_board_source(
    "ashby",
    "Ashby",
    "ASHBY_COMPANIES",
    DEFAULT_COMPANIES,
    lambda pCompany: parse_jobs(get_jobs(pCompany), pCompany),
)
