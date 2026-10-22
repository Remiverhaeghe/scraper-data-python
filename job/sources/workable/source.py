"""Déclaration de la source Workable"""

from job.sources.boards import define_board_source
from job.sources.workable.client import get_account
from job.sources.workable.parser import parse_account

# Aucune entreprise par défaut : la liste publique est vide pour beaucoup de
# comptes. La source s'active avec WORKABLE_ACCOUNTS dans .env.
SOURCE = define_board_source(
    "workable",
    "Workable",
    "WORKABLE_ACCOUNTS",
    "",
    lambda pAccount: parse_account(get_account(pAccount), pAccount),
)
