"""
Point d'entrée de l'application.
"""

from scraper.http_client import fetch_page


def main():
    """Lance l'application."""

    url = "https://example.com"

    html = fetch_page(url)

    print(f"Page récupérée : {len(html)} caractères")


if __name__ == "__main__":
    main()