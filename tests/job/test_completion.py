"""Tests de la complétion commune des offres"""

import pandas as pd

from job.completion import decode_entities


def test_titles_and_companies_are_decoded():
    """Vérifie le décodage des entités HTML, valeurs absentes comprises."""

    vItems = decode_entities(
        pd.DataFrame(
            [
                {"title": "Développeur Full Stack &amp; IA", "company": "R&amp;D"},
                {"title": "Ing&eacute;nieur", "company": None},
            ]
        )
    )

    assert vItems["title"].tolist() == ["Développeur Full Stack & IA", "Ingénieur"]
    assert vItems["company"][0] == "R&D"
    assert pd.isna(vItems["company"][1])
