# ============================================================================
# Méthodes utilitaires pour la gestion des URLs
# ============================================================================


from urllib.parse import urljoin


def build_absolute_url(pBaseUrl, pRelativeUrl):
    """
    Construit une URL absolue à partir d'une URL de base.

    :param pBaseUrl: URL de base.
    :param pRelativeUrl: URL relative.
    :return: URL absolue ou chaîne vide.
    """

    if not pRelativeUrl:
        rUrl = ""

    else:
        rUrl = urljoin(
            pBaseUrl,
            pRelativeUrl
        )

    return rUrl