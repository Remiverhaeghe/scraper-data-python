"""Tests du repérage des annonces douteuses"""

import pytest

from job.suspicious_offers import find_suspicious_signs


@pytest.mark.parametrize(
    ("pDescription", "pExpected"),
    [
        ("Des frais de dossier de 50 € sont demandés.", ["frais demandés au candidat"]),
        ("Contactez-nous sur WhatsApp au 06…", ["contact par messagerie"]),
        (
            "Merci d'envoyer votre RIB avec le CV.",
            ["documents sensibles demandés d'emblée"],
        ),
        # Faux positifs évités : produit cité, vocabulaire technique, mot isolé
        ("Intégration de l'API WhatsApp Business.", []),
        ("Traitement du signal et chaînes RF.", []),
        ("Poste en CDI, télétravail partiel.", []),
    ],
)
def test_suspicious_signs_are_found_without_false_alarms(pDescription, pExpected):
    """Vérifie les signes repérés, et les tournures courantes laissées de côté."""

    assert find_suspicious_signs({"title": "Poste", "description": pDescription}) == (
        pExpected
    )


def test_salary_far_above_the_market_is_suspicious_in_france_only():
    """Vérifie le salaire trop beau, en France seulement."""

    vOffer = {"salary_net_monthly_min": 9000, "country": "France"}

    assert find_suspicious_signs(vOffer, 3000) == ["salaire très au-dessus du marché"]
    assert find_suspicious_signs({**vOffer, "country": "États-Unis"}, 3000) == []
    assert find_suspicious_signs({**vOffer, "salary_net_monthly_min": 4000}, 3000) == []
