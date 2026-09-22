# ============================================================================
# Tests de la pagination commune des scrapers
# ============================================================================


import pandas as pd

from scraper.pagination import scrape_paginated


def test_scrape_paginated_scrapes_multiple_pages():
    """
    Vérifie que plusieurs pages sont parcourues correctement.
    """

    vPages = {
        "https://example.com/page1": "page1",
        "https://example.com/page2": "page2"
    }

    vNextUrls = {
        "https://example.com/page1": "https://example.com/page2",
        "https://example.com/page2": ""
    }

    vItems = {
        "page1": pd.DataFrame([
            {"url": "A"},
            {"url": "B"}
        ]),
        "page2": pd.DataFrame([
            {"url": "C"},
            {"url": "D"}
        ])
    }

    class Config:
        max_pages = None
        max_items = None
        avoid_duplicates = True

    def fetch_page(pUrl, pConfig):
        return vPages[pUrl]

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return vItems[pSoup]

    def extract_next_url(pSoup, pCurrentUrl):
        return vNextUrls[pCurrentUrl]

    rResult = scrape_paginated(
        "https://example.com/page1",
        Config(),
        fetch_page,
        parse_html,
        extract_items,
        extract_next_url
    )

    assert rResult.items["url"].tolist() == [
        "A",
        "B",
        "C",
        "D"
    ]

    assert rResult.page_count == 2
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_paginated_respects_max_pages():
    """
    Vérifie que le nombre maximum de pages est respecté.
    """

    vPages = {
        "https://example.com/page1": "page1",
        "https://example.com/page2": "page2"
    }

    vItems = {
        "page1": pd.DataFrame([
            {"url": "A"},
            {"url": "B"}
        ]),
        "page2": pd.DataFrame([
            {"url": "C"},
            {"url": "D"}
        ])
    }

    class Config:
        max_pages = 1
        max_items = None
        avoid_duplicates = True

    def fetch_page(pUrl, pConfig):
        return vPages[pUrl]

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return vItems[pSoup]

    def extract_next_url(pSoup, pCurrentUrl):
        return "https://example.com/page2"

    rResult = scrape_paginated(
        "https://example.com/page1",
        Config(),
        fetch_page,
        parse_html,
        extract_items,
        extract_next_url
    )

    assert rResult.items["url"].tolist() == [
        "A",
        "B"
    ]

    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_paginated_respects_max_items():
    """
    Vérifie que le nombre maximum d'éléments est respecté.
    """

    vPages = {
        "https://example.com/page1": "page1"
    }

    vItems = {
        "page1": pd.DataFrame([
            {"url": "A"},
            {"url": "B"},
            {"url": "C"},
            {"url": "D"}
        ])
    }

    class Config:
        max_pages = None
        max_items = 3
        avoid_duplicates = True

    def fetch_page(pUrl, pConfig):
        return vPages[pUrl]

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return vItems[pSoup]

    def extract_next_url(pSoup, pCurrentUrl):
        return ""

    rResult = scrape_paginated(
        "https://example.com/page1",
        Config(),
        fetch_page,
        parse_html,
        extract_items,
        extract_next_url
    )

    assert rResult.items["url"].tolist() == [
        "A",
        "B",
        "C"
    ]

    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "success"
    assert rResult.error_message is None


def test_scrape_paginated_returns_error_result_when_scraping_fails():
    """
    Vérifie qu'une erreur pendant le scraping produit un résultat ERROR.
    """

    class Config:
        max_pages = None
        max_items = None
        avoid_duplicates = True

    def fetch_page(pUrl, pConfig):
        raise ValueError(
            "Erreur de récupération de la page."
        )

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return pd.DataFrame()

    def extract_next_url(pSoup, pCurrentUrl):
        return ""

    rResult = scrape_paginated(
        "https://example.com/page1",
        Config(),
        fetch_page,
        parse_html,
        extract_items,
        extract_next_url
    )

    assert rResult.items.empty
    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "error"
    assert rResult.error_message == (
        "Erreur de récupération de la page."
    )


def test_scrape_paginated_removes_duplicates():
    """
    Vérifie que les doublons présents sur plusieurs pages
    sont supprimés.
    """

    vPages = {
        "https://example.com/page1": "page1",
        "https://example.com/page2": "page2"
    }

    vNextUrls = {
        "https://example.com/page1": "https://example.com/page2",
        "https://example.com/page2": ""
    }

    vItems = {
        "page1": pd.DataFrame([
            {
                "url": "https://example.com/1",
                "title": "Premier"
            },
            {
                "url": "https://example.com/2",
                "title": "Deuxième"
            }
        ]),
        "page2": pd.DataFrame([
            {
                "url": "https://example.com/2",
                "title": "Deuxième doublon"
            },
            {
                "url": "https://example.com/3",
                "title": "Troisième"
            }
        ])
    }

    class Config:
        max_pages = None
        max_items = None
        avoid_duplicates = True

    def fetch_page(pUrl, pConfig):
        return vPages[pUrl]

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return vItems[pSoup]

    def extract_next_url(pSoup, pCurrentUrl):
        return vNextUrls[pCurrentUrl]

    rResult = scrape_paginated(
        "https://example.com/page1",
        Config(),
        fetch_page,
        parse_html,
        extract_items,
        extract_next_url,
        "url"
    )

    assert rResult.items["url"].tolist() == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3"
    ]

    assert rResult.items["title"].tolist() == [
        "Premier",
        "Deuxième",
        "Troisième"
    ]

    assert len(rResult.items) == 3
    assert rResult.page_count == 2
    assert rResult.status == "success"
    assert rResult.error_message is None