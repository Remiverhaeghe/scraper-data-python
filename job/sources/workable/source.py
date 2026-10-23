"""Déclaration de la source Workable"""

from job.sources.boards import define_board_source
from job.sources.workable.client import get_account
from job.sources.workable.parser import parse_account

# Entreprises suivies : Paramètres, .env ou liste par défaut (job/company_pages.py)
SOURCE = define_board_source(
    "workable",
    "Workable",
    lambda pAccount: parse_account(get_account(pAccount), pAccount),
)
