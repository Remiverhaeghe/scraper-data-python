"""Déclaration de la source Lever"""

from job.sources.boards import define_board_source
from job.sources.lever.client import get_postings
from job.sources.lever.parser import parse_postings

# Entreprises suivies : Paramètres, .env ou liste par défaut (job/company_pages.py)
SOURCE = define_board_source(
    "lever", "Lever", lambda pCompany: parse_postings(get_postings(pCompany), pCompany)
)
