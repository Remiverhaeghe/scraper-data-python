"""Déclaration de la source Ashby"""

from job.sources.ashby.client import get_jobs
from job.sources.ashby.parser import parse_jobs
from job.sources.boards import define_board_source

# Entreprises suivies : Paramètres, .env ou liste par défaut (job/company_pages.py)
SOURCE = define_board_source(
    "ashby", "Ashby", lambda pCompany: parse_jobs(get_jobs(pCompany), pCompany)
)
