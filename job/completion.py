"""Complétion des offres avant enregistrement, commune aux recherches et aux ajouts"""

from job.benefits import add_benefits
from job.contract import add_contract
from job.enrichment import enrich_offers
from job.fingerprint import build_fingerprint
from job.salary import add_net_salary, assume_euro_in_france


def complete_offers(pItems, pNetRatio, pTaxRate):
    """Enrichit les offres et calcule empreinte, net, avantages et contrat.

    Retourne les offres complétées et le nombre d'offres inexploitables écartées.
    """

    # Avant le calcul du net : un salaire trouvé dans la description est converti.
    vItems, vRejectedCount = enrich_offers(pItems)

    # L'empreinte rapproche les annonces d'une même offre publiées sur plusieurs
    # sources ; elles restent toutes enregistrées.
    vItems["fingerprint"] = [
        build_fingerprint(vOffer) for vOffer in vItems.to_dict("records")
    ]

    vItems = assume_euro_in_france(vItems)
    vItems = add_net_salary(vItems, pNetRatio=pNetRatio, pTaxRate=pTaxRate)
    vItems = add_benefits(vItems)
    vItems = add_contract(vItems)

    rResult = (vItems, vRejectedCount)

    return rResult
