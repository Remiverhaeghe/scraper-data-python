"""Détection des avantages salariaux mentionnés dans les offres"""

import re

from utils.logger import get_logger

logger = get_logger(__name__)

# Formulations volontairement strictes pour limiter les faux positifs :
# « participation » ou « variable » seuls sont trop fréquents dans les offres.
BENEFIT_PATTERNS = {
    "has_13th_month": re.compile(
        r"\b13\s*(?:e|è|ème|eme|ième|ieme)\s+mois\b|\bsur\s+13(?:[.,]0)?\s+mois\b",
        re.IGNORECASE,
    ),
    "has_bonus": re.compile(
        r"\bprimes?\b|\bbonus\b|\b(?:part|rémunération)\s+variable\b",
        re.IGNORECASE,
    ),
    "has_profit_sharing": re.compile(
        r"\bintéressement\b|\bparticipation\s+aux\s+(?:résultats|bénéfices)\b",
        re.IGNORECASE,
    ),
    "has_savings_plan": re.compile(
        r"\b(?:PEE|PEI|PERCOL?|PERECO|PER\s+collectif)\b|\bépargne\s+salariale\b",
        re.IGNORECASE,
    ),
}

TEXT_COLUMNS = ["title", "salary_label", "description", "missions", "requirements"]


def detect_benefits(pText):
    """Retourne les avantages détectés dans un texte.

    Une absence de mention ne prouve pas l'absence de l'avantage :
    la valeur est alors laissée vide plutôt qu'à False.
    """

    rBenefits = {
        vColumn: True if vPattern.search(pText) else None
        for vColumn, vPattern in BENEFIT_PATTERNS.items()
    }

    return rBenefits


def add_benefits(pItems):
    """Ajoute aux offres les avantages détectés dans leurs textes."""

    vItems = pItems.copy()

    vTexts = vItems.reindex(columns=TEXT_COLUMNS).fillna("").astype(str)

    vBenefits = [
        detect_benefits(" ".join(vRow)) for vRow in vTexts.itertuples(index=False)
    ]

    for vColumn in BENEFIT_PATTERNS:
        vItems[vColumn] = [vBenefit[vColumn] for vBenefit in vBenefits]

    logger.info(
        "Avantages détectés : %s",
        {vColumn: int(vItems[vColumn].notna().sum()) for vColumn in BENEFIT_PATTERNS},
    )

    rItems = vItems

    return rItems
