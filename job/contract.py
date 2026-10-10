"""Normalisation du type de contrat des offres"""

import re

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

CONTRACT_TYPES = ("CDI", "CDD", "FREELANCE")

CONTRACT_PATTERNS = {
    # Formulations françaises, anglaises et allemandes (Arbeitnow, Greenhouse)
    "CDI": re.compile(
        r"\bCDI\b|contrat\s+à\s+durée\s+indéterminée|\bpermanent\b|\bunbefristet",
        re.IGNORECASE,
    ),
    "CDD": re.compile(
        r"\bCDD\b|contrat\s+à\s+durée\s+déterminée|\bfixed[\s-]term\b"
        r"|\btemporary\b|\bbefristet",
        re.IGNORECASE,
    ),
    "FREELANCE": re.compile(
        r"\bfree-?lances?\b|\bindépendants?\b|\bportage\s+salarial\b|\bTJM\b",
        re.IGNORECASE,
    ),
}

# Du plus fiable au moins fiable : le titre annonce souvent le contrat,
# la description peut citer plusieurs contrats sans rapport avec l'offre.
TEXT_COLUMNS = ["title", "contract_type", "description"]


def detect_contract(pTexts):
    """Retourne le contrat détecté dans le premier texte sans ambiguïté."""

    rContract = None

    for vText in pTexts:
        vMatches = [
            vContract
            for vContract, vPattern in CONTRACT_PATTERNS.items()
            if vPattern.search(vText)
        ]

        if len(vMatches) == 1:
            rContract = vMatches[0]
            break

    return rContract


def add_contract(pItems):
    """Complète le contrat des offres que leur source n'a pas pu qualifier."""

    vItems = pItems.copy()

    vTexts = vItems.reindex(columns=TEXT_COLUMNS).fillna("").astype(str)

    vContracts = [
        vContract if not pd.isna(vContract) else detect_contract(vTextRow)
        for vContract, vTextRow in zip(
            vItems.reindex(columns=["contract"])["contract"],
            vTexts.itertuples(index=False),
        )
    ]

    vItems["contract"] = vContracts

    logger.info(
        "Contrats identifiés : %s",
        {vType: vContracts.count(vType) for vType in CONTRACT_TYPES},
    )

    rItems = vItems

    return rItems
