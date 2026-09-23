# ============================================================================
# Mécanique commune de scraping d'un élément
# ============================================================================

from utils.logger import get_logger

logger = get_logger(__name__)


def scrape_item(
    pUrl,
    pConfig,
    pFetchPage,
    pParseHtml,
    pExtractItem
):
    """
    Récupère et extrait un élément depuis une URL.

    :param pUrl: URL de l'élément.
    :param pConfig: Configuration du scraping.
    :param pFetchPage: Fonction de récupération HTTP.
    :param pParseHtml: Fonction de parsing.
    :param pExtractItem: Fonction d'extraction.
    :return: Élément extrait.
    """
    logger.info(
        "Début du scraping : %s",
        pUrl
    )

    vHtml = pFetchPage(
        pUrl,
        pConfig
    )

    vSoup = pParseHtml(
        vHtml
    )

    vItem = pExtractItem(
        vSoup
    )

    logger.info(
        "Scraping terminé : %s",
        pUrl
    )

    rItem = vItem
    return rItem