"""Annonces douteuses : signes fréquents des fausses offres, repérés par règles

Une annonce signalée n'est pas forcément fausse : c'est une invitation à
vérifier l'entreprise avant de répondre ou d'envoyer des documents.
"""

import re
from statistics import median

from job.fingerprint import normalize
from job.location import FRANCE
from job.salary_market import get_net_salary, load_salaried_offers

# Signe : expressions cherchées dans le texte normalisé (minuscules, sans accents)
SUSPICIOUS_PATTERNS = {
    "frais demandés au candidat": re.compile(
        r"frais (d inscription|de dossier|de formation|d adhesion)"
        r"|formation (payante|a vos frais)|achat (du|de votre) materiel|caution de"
    ),
    # Une demande de contact par messagerie, pas un produit cité dans l'annonce
    "contact par messagerie": re.compile(
        r"\b(contact\w*|ecri\w*|envoy\w*|joindre|repond\w*|postul\w*)\b"
        r"[^.]{0,40}\b(whatsapp|telegram)\b"
    ),
    "documents sensibles demandés d'emblée": re.compile(
        r"\b(envoy\w*|fourni\w*|transmet\w*|communiqu\w*)\b[^.]{0,40}"
        r"\b(rib|carte bancaire|numero de securite sociale|carte d identite)\b"
    ),
}

# Salaire au-delà de ce multiple de la médiane du marché : trop beau pour être vrai
SALARY_RATIO = 2.5


def find_suspicious_signs(pOffer, pMarketMedian=None):
    """Retourne les signes d'annonce douteuse repérés, vide s'il n'y en a pas."""

    vText = normalize(
        " ".join(
            str(pOffer.get(vField) or "")
            for vField in ("title", "description", "requirements", "missions")
        )
    )

    rSigns = [
        vLabel
        for vLabel, vPattern in SUSPICIOUS_PATTERNS.items()
        if vPattern.search(vText)
    ]

    vSalary = get_net_salary(pOffer)

    # Médiane française : un poste à l'étranger mieux payé n'est pas suspect.
    if (
        pMarketMedian
        and pOffer.get("country") == FRANCE
        and vSalary is not None
        and vSalary > SALARY_RATIO * pMarketMedian
    ):
        rSigns.append("salaire très au-dessus du marché")

    return rSigns


def load_market_median(pDatabaseFile):
    """Retourne le net mensuel médian des offres en France qui l'annoncent, ou None."""

    vSalaries = [vSalary for _, _, vSalary in load_salaried_offers(pDatabaseFile)]

    rMedian = median(vSalaries) if vSalaries else None

    return rMedian


def mark_suspicious_offers(pDatabaseFile, pOffers):
    """Ajoute à chaque offre ses signes d'annonce douteuse (suspicious_signs)."""

    vMedian = load_market_median(pDatabaseFile)

    for vOffer in pOffers:
        vOffer["suspicious_signs"] = find_suspicious_signs(vOffer, vMedian)
