"""Complétion des offres avant enregistrement, commune aux recherches et aux ajouts"""

import html

from job.benefits import add_benefits
from job.contract import add_contract
from job.enrichment import enrich_offers
from job.fingerprint import borrow_missing_companies, build_fingerprint
from job.location import add_location
from job.salary import add_net_salary, assume_euro_in_france
from utils.logger import get_logger

logger = get_logger(__name__)

# Colonnes affichées telles quelles, que certaines sources envoient encodées
ENCODED_COLUMNS = ("title", "company")


def decode_text(pValue):
    """Décode les entités HTML (&amp;, &eacute;) d'un texte ; le reste est inchangé."""

    rValue = html.unescape(pValue) if isinstance(pValue, str) else pValue

    return rValue


def decode_entities(pItems):
    """Décode les entités HTML du titre et de l'entreprise, envoyées par certaines sources."""

    rItems = pItems.assign(
        **{
            vColumn: pItems[vColumn].map(decode_text)
            for vColumn in ENCODED_COLUMNS
            if vColumn in pItems
        }
    )

    return rItems


def complete_offers(pItems, pNetRatio, pTaxRate, pRates=None):
    """Enrichit les offres et calcule empreinte, lieu, net, avantages et contrat.

    pRates convertit en euros les salaires dans une autre devise (job.exchange_rates).

    Retourne les offres complétées et le nombre d'offres écartées par source.
    """

    # Avant le calcul du net : un salaire trouvé dans la description est converti.
    vItems, vRejectedCount = enrich_offers(decode_entities(pItems))

    # L'empreinte rapproche les annonces d'une même offre publiées sur plusieurs
    # sources ; elles restent toutes enregistrées.
    # Une annonce sans entreprise reprend celle de sa jumelle d'une autre source :
    # leurs empreintes deviennent identiques.
    vOffers = vItems.to_dict("records")
    vBorrowed = borrow_missing_companies(vOffers)

    if vBorrowed:
        logger.info("Entreprise reprise d'une annonce jumelle : %s offre(s)", vBorrowed)
        vItems = vItems.assign(company=[vOffer.get("company") for vOffer in vOffers])

    vItems["fingerprint"] = [build_fingerprint(vOffer) for vOffer in vOffers]

    # Le pays est connu avant la règle des euros : « Lille » seul suffit alors.
    vItems = add_location(vItems)
    vItems = assume_euro_in_france(vItems)
    vItems = add_net_salary(
        vItems, pNetRatio=pNetRatio, pTaxRate=pTaxRate, pRates=pRates
    )
    vItems = add_benefits(vItems)
    vItems = add_contract(vItems)

    rResult = (vItems, vRejectedCount)

    return rResult
