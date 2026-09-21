# ============================================================================
# Fonctions communes de gestion des collections
# ============================================================================


def has_reached_limit(pItems, pMaxItems):
    """
    Vérifie si le nombre maximum d'éléments est atteint.

    :param pItems: Collection d'éléments.
    :param pMaxItems: Nombre maximum d'éléments autorisés.
    :return: True si la limite est atteinte, sinon False.
    """

    rReached = (
        pMaxItems is not None
        and len(pItems) >= pMaxItems
    )

    return rReached


def deduplicate_items(pItems, pKeyFunction):
    """
    Supprime les doublons d'une collection en conservant
    la première occurrence de chaque élément.

    :param pItems: Collection d'éléments.
    :param pKeyFunction: Fonction permettant d'obtenir la clé unique.
    :return: Collection sans doublon.
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