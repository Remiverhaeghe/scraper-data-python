"""
Point d'entrée de l'application.
"""

from scraper.parser import extract_job, parse_html


def main():
    """Lance l'application."""

    html = """
    <html>
        <body>
            <h1>Développeur Python</h1>
            <div class="company">OpenAI</div>
            <div class="location">Paris</div>
            <div class="contract">CDI</div>
            <div class="date">31/08/2026</div>
            <a href="https://example.com/job">Voir l'offre</a>
        </body>
    </html>
    """

    soup = parse_html(html)
    job = extract_job(soup)

    print(job)


if __name__ == "__main__":
    main()