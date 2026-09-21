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