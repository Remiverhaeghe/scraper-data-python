"""Tests du résumé d'une annonce"""

from job.offer_summary import build_offer_summary


def test_sections_are_found_on_lines_or_inline():
    """Vérifie les parties repérées, intertitres en ligne ou suivis de deux-points."""

    vOnLines = {
        "description": "Acme recrute.\nVos missions\nDévelopper l'API.\nVotre profil\n"
        "Trois ans de Java.\nAvantages\nTickets restaurant.",
        "contract": "CDI",
        "experience_level": "Not Applicable",
    }
    vInline = {
        "description": "Description: Acme recrute. Missions : Maintenir les lignes. "
        "Profil: Électrotechnicien confirmé."
    }

    assert build_offer_summary(vOnLines)[:3] == [
        ("Missions", "Développer l'API."),
        ("Profil recherché", "Trois ans de Java."),
        ("Avantages", "Tickets restaurant."),
    ]
    assert build_offer_summary(vOnLines)[-1] == ("En pratique", "CDI")
    assert build_offer_summary(vInline)[:2] == [
        ("Missions", "Maintenir les lignes."),
        ("Profil recherché", "Électrotechnicien confirmé."),
    ]


def test_first_sentences_are_used_without_headings():
    """Vérifie le résumé de secours : les deux premières phrases, coupées si besoin."""

    vSummary = build_offer_summary(
        {"description": "Première phrase. Deuxième phrase. Troisième phrase."}
    )

    assert vSummary == [("En bref", "Première phrase. Deuxième phrase.")]
    assert build_offer_summary({}) == []
