"""Déclaration de la source Lever"""

from job.sources.boards import define_board_source
from job.sources.lever.client import get_postings
from job.sources.lever.parser import parse_postings

# Entreprises suivies par défaut, vérifiées sur l'API, avec des offres en France
DEFAULT_COMPANIES = "qonto,aircall,swile,agicap,malt"

SOURCE = define_board_source(
    "lever",
    "Lever",
    "LEVER_COMPANIES",
    DEFAULT_COMPANIES,
    lambda pCompany: parse_postings(get_postings(pCompany), pCompany),
)
