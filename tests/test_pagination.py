# ============================================================================
# Tests de la pagination commune des scrapers
# ============================================================================


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
        "page1": ["A", "B"],
        "page2": ["C", "D"]
    }

    class Config:
        max_pages = None
        max_items = None

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

    assert rResult.items == [
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
        "page1": ["A", "B"],
        "page2": ["C", "D"]
    }

    class Config:
        max_pages = 1
        max_items = None

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

    assert rResult.items == [
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
        "page1": [
            "A",
            "B",
            "C",
            "D"
        ]
    }

    class Config:
        max_pages = None
        max_items = 3

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

    assert rResult.items == [
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

    def fetch_page(pUrl, pConfig):
        raise ValueError(
            "Erreur de récupération de la page."
        )

    def parse_html(pHtml):
        return pHtml

    def extract_items(pSoup, pCurrentUrl):
        return []

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

    assert rResult.items == []
    assert rResult.page_count == 1
    assert rResult.duration_seconds >= 0
    assert rResult.started_at is not None
    assert rResult.status == "error"
    assert rResult.error_message == (
        "Erreur de récupération de la page."
    )