# ============================================================================
# Fonctions communes de gestion des collections
# ============================================================================


import pandas as pd


def has_reached_limit(pItems, pMaxItems):
    """
    Vérifie si le nombre d'éléments maximum est atteint.
    """

    rReached = (
        pMaxItems is not None
        and len(pItems) >= pMaxItems
    )

    return rReached


def deduplicate_items(pItems, pKeyFunction):
    """
    Supprime les doublons d'une collection Python.
    """

    vSeenKeys = set()
    vUniqueItems = []

    for vItem in pItems:
        vKey = pKeyFunction(vItem)

        if vKey not in vSeenKeys:
            vSeenKeys.add(vKey)
            vUniqueItems.append(vItem)

    rItems = vUniqueItems

    return rItems


def deduplicate_dataframe(pDataFrame, pKeyColumn):
    """
    Supprime les doublons d'un DataFrame à partir d'une colonne.
    """

    vDataFrame = pDataFrame.drop_duplicates(
        subset=[pKeyColumn],
        keep="first"
    )

    rDataFrame = vDataFrame.reset_index(
        drop=True
    )

    return rDataFrame