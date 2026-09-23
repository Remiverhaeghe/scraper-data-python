# ============================================================================
# Tests de la mécanique commune de scraping
# ============================================================================

from scraper.service import scrape_item


def test_scrape_item():
    """
    Vérifie l'enchaînement récupération, parsing et extraction.
    """

    vCalls = []

    def mock_fetch_page(pUrl, pConfig):
        vCalls.append("fetch")
        return "<html>test</html>"

    def mock_parse_html(pHtml):
        vCalls.append("parse")
        return "soup"

    def mock_extract_item(pSoup):
        vCalls.append("extract")
        return {
            "title": "Test"
        }

    vResult = scrape_item(
        "https://example.com",
        None,
        mock_fetch_page,
        mock_parse_html,
        mock_extract_item
    )

    assert vCalls == [
        "fetch",
        "parse",
        "extract"
    ]

    assert vResult == {
        "title": "Test"
    }


def test_scrape_item_propagates_extraction_error():
    """
    Vérifie qu'une erreur d'extraction est propagée.
    """

    def mock_fetch_page(pUrl, pConfig):
        return "<html>test</html>"

    def mock_parse_html(pHtml):
        return "soup"

    def mock_extract_item(pSoup):
        raise ValueError("Erreur extraction")

    try:
        scrape_item(
            "https://example.com",
            None,
            mock_fetch_page,
            mock_parse_html,
            mock_extract_item
        )
        assert False
    except ValueError as vException:
        assert str(vException) == "Erreur extraction"