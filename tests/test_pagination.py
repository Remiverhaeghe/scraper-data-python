# ============================================================================
# Tests de la gestion commune de la pagination
# ============================================================================


from scraper.config import ScrapingConfig
from scraper.pagination import scrape_paginated


def test_scrape_paginated_scrapes_multiple_pages():
    """
    Vérifie que plusieurs pages sont parcourues.
    """

    vConfig = ScrapingConfig(
        max_pages=3
    )

    vPages = {
        "https://example.com/page-1": ["A", "B"],
        "https://example.com/page-2": ["C", "D"]
    }

    def vFetchPage(pUrl, pConfig):
        rHtml = pUrl
        return rHtml

    def vParseHtml(pHtml):
        rSoup = pHtml
        return rSoup

    def vExtractItems(pSoup, pUrl):
        rItems = vPages[pUrl]
        return rItems

    def vExtractNextUrl(pSoup, pCurrentUrl):
        if pCurrentUrl == "https://example.com/page-1":
            rNextUrl = "https://example.com/page-2"
        else:
            rNextUrl = ""

        return rNextUrl

    rItems = scrape_paginated(
        "https://example.com/page-1",
        vConfig,
        vFetchPage,
        vParseHtml,
        vExtractItems,
        vExtractNextUrl
    )

    assert rItems == [
        "A",
        "B",
        "C",
        "D"
    ]


def test_scrape_paginated_respects_max_pages():
    """
    Vérifie que le nombre maximum de pages est respecté.
    """

    vConfig = ScrapingConfig(
        max_pages=1
    )

    vPages = {
        "https://example.com/page-1": ["A", "B"],
        "https://example.com/page-2": ["C", "D"]
    }

    def vFetchPage(pUrl, pConfig):
        rHtml = pUrl
        return rHtml

    def vParseHtml(pHtml):
        rSoup = pHtml
        return rSoup

    def vExtractItems(pSoup, pUrl):
        rItems = vPages[pUrl]
        return rItems

    def vExtractNextUrl(pSoup, pCurrentUrl):
        rNextUrl = "https://example.com/page-2"
        return rNextUrl

    rItems = scrape_paginated(
        "https://example.com/page-1",
        vConfig,
        vFetchPage,
        vParseHtml,
        vExtractItems,
        vExtractNextUrl
    )

    assert rItems == [
        "A",
        "B"
    ]


def test_scrape_paginated_respects_max_items():
    """
    Vérifie que le nombre maximum d'éléments est respecté.
    """

    vConfig = ScrapingConfig(
        max_items=3
    )

    vPages = {
        "https://example.com/page-1": ["A", "B", "C"],
        "https://example.com/page-2": ["D", "E"]
    }

    def vFetchPage(pUrl, pConfig):
        rHtml = pUrl
        return rHtml

    def vParseHtml(pHtml):
        rSoup = pHtml
        return rSoup

    def vExtractItems(pSoup, pUrl):
        rItems = vPages[pUrl]
        return rItems

    def vExtractNextUrl(pSoup, pCurrentUrl):
        rNextUrl = "https://example.com/page-2"
        return rNextUrl

    rItems = scrape_paginated(
        "https://example.com/page-1",
        vConfig,
        vFetchPage,
        vParseHtml,
        vExtractItems,
        vExtractNextUrl
    )

    assert rItems == [
        "A",
        "B",
        "C"
    ]