"""Déclaration de la source Recruitee"""

from job.sources.boards import define_board_source
from job.sources.recruitee.client import get_offers
from job.sources.recruitee.parser import parse_offers

# Aucune entreprise par défaut : l'API publique ne répond que pour peu de pages
# carrière. La source s'active avec RECRUITEE_COMPANIES dans .env.
SOURCE = define_board_source(
    "recruitee",
    "Recruitee",
    "RECRUITEE_COMPANIES",
    "",
    lambda pCompany: parse_offers(get_offers(pCompany), pCompany),
)
