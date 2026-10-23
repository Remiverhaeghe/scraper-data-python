"""Recherches prêtes à l'emploi, enregistrées d'un clic"""

from job.sources.configuration import DEFAULT_CRITERIA
from job.sources.registry import SOURCES
from storage.saved_searches import save_search

# Métiers industriels cherchés, un par recherche : les sources qui cherchent
# côté serveur n'acceptent qu'un mot-clé à la fois.
INDUSTRY_KEYWORDS = ("Maintenance", "Automatisme", "Électrotechnique")

# Sources cochées : offres en France et pages carrière des entreprises suivies
INDUSTRY_CATEGORIES = ("france", "company")

INDUSTRY_MAX_ITEMS = 100


def create_industry_searches(pDatabaseFile, pNow):
    """Enregistre une recherche par métier industriel ; retourne leurs noms.

    Une recherche du même nom, déjà enregistrée, est remplacée.
    """

    vSources = [
        vName
        for vName, vDefinition in SOURCES.items()
        if vDefinition.category in INDUSTRY_CATEGORIES
    ]

    rNames = [
        save_search(
            pDatabaseFile,
            f"Industrie · {vKeyword}",
            vSources,
            {
                **DEFAULT_CRITERIA,
                "keyword": vKeyword.lower(),
                "max_items": INDUSTRY_MAX_ITEMS,
            },
            pNow,
        )
        for vKeyword in INDUSTRY_KEYWORDS
    ]

    return rNames
