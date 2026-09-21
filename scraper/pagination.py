# ============================================================================
# Gestion commune de la pagination des scrapers
# ============================================================================


from scraper.collection import has_reached_limit


def scrape_paginated(
    pUrl,
    pConfig,
    pFetchPage,
    pParseHtml,
    pExtractItems,
    pExtractNextUrl
):
    """
    Parcourt plusieurs pages et récupère les éléments présents sur chaque page.

    :param pUrl: URL de départ.
    :param pConfig: Configuration commune du scraping.
    :param pFetchPage: Fonction permettant de récupérer une page.
    :param pParseHtml: Fonction permettant de parser le HTML.
    :param pExtractItems: Fonction permettant d'extraire les éléments.
    :param pExtractNextUrl: Fonction permettant de récupérer l'URL suivante.
    :return: Liste des éléments récupérés.
    """

    vItems = []
    vCurrentUrl = pUrl
    vPageCount = 0

    while vCurrentUrl:
        # Vérification du nombre maximum de pages
        if (
            pConfig.max_pages is not None
            and vPageCount >= pConfig.max_pages
        ):
            break

        # Vérification du nombre maximum d'éléments
        if has_reached_limit(
            vItems,
            pConfig.max_items
        ):
            break

        vPageCount += 1

        vHtml = pFetchPage(
            vCurrentUrl,
            pConfig
        )

        vSoup = pParseHtml(
            vHtml
        )

        vItems.extend(
            pExtractItems(
                vSoup,
                vCurrentUrl
            )
        )

        # Limitation du nombre maximum d'éléments
        if has_reached_limit(
            vItems,
            pConfig.max_items
        ):
            vItems = vItems[
                :pConfig.max_items
            ]
            break

        vCurrentUrl = pExtractNextUrl(
            vSoup,
            vCurrentUrl
        )

    rItems = vItems

    return rItems