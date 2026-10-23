"""Déclaration de la source Recruitee"""

from job.sources.boards import define_board_source
from job.sources.recruitee.client import get_offers
from job.sources.recruitee.parser import parse_offers

# Entreprises suivies : Paramètres, .env ou liste par défaut (job/company_pages.py)
SOURCE = define_board_source(
    "recruitee",
    "Recruitee",
    lambda pCompany: parse_offers(get_offers(pCompany), pCompany),
)
