"""Tests du repérage des offres à double profil, maintenance et informatique"""

import pytest

from job.hybrid import (
    DEFAULT_HEADLINE,
    build_hybrid_advice,
    describe_offer_hybrid,
    detect_hybrid,
    is_profile_hybrid,
)
from job.preparation import prepare_application

HYBRID_PROFILE = {
    "name": "Camille",
    "headline": "",
    "skills": ["GMAO", "Python", "SQL"],
    "experiences": [
        {"title": "Technicien de maintenance", "skills": ["GMAO"], "achievement": ""},
        {"title": "Développeur Python", "skills": ["Python"], "achievement": ""},
    ],
    "cv_variants": [],
}


@pytest.mark.parametrize(
    ("pText", "pFirst"),
    [
        ("Technicien informatique industrielle H/F", "Informatique industrielle"),
        ("Automaticien, supervision WinCC et TIA Portal", "Supervision"),
        ("Déploiement de la solution MES sur nos lignes", "MES"),
        ("Référent GMAO : paramétrage de la GMAO et des plans", "Administration GMAO"),
        (
            "Maintenance industrielle de la ligne, scripts Python et base de données",
            "Maintenance",
        ),
    ],
)
def test_hybrid_offers_are_found(pText, pFirst):
    """Vérifie les termes ponts et la combinaison industrie plus informatique."""

    assert detect_hybrid(pText)[0] == pFirst


@pytest.mark.parametrize(
    "pText",
    [
        "Technicien de maintenance, saisie dans la GMAO, maîtrise de l'outil informatique",
        "Je veux automate workflows with Python and SQL APIs",
        "Venez rejoindre mes collègues : MES missions changent chaque semaine",
        "Chef de chantier, MES et réception des installations",
        "Développeur Python et SQL pour une plateforme web",
    ],
)
def test_ordinary_offers_are_not_hybrid(pText):
    """Vérifie les faux amis : GMAO saisie, « automate » anglais, MES de mise en service."""

    assert detect_hybrid(pText) == ()


def test_profile_and_advice_put_the_double_background_forward():
    """Vérifie le profil reconnu, l'accroche de CV, le pitch et la lettre enrichis."""

    vOffer = {
        "title": "Technicien MES",
        "company": "Acme",
        "description": "Déploiement de la solution MES et de la supervision SCADA.",
    }

    assert is_profile_hybrid(HYBRID_PROFILE)
    assert not is_profile_hybrid({**HYBRID_PROFILE, "skills": [], "experiences": []})

    vAdvice = build_hybrid_advice(HYBRID_PROFILE, vOffer)

    assert vAdvice["terms"][:2] == ["Supervision", "MES"]
    assert vAdvice["headline"] == "Technicien de maintenance et développeur Python"
    assert build_hybrid_advice(HYBRID_PROFILE, {"title": "Comptable"}) is None
    assert describe_offer_hybrid(vOffer).endswith("Supervision, MES")

    vPreparation = prepare_application(HYBRID_PROFILE, vOffer)

    assert (
        "réunit la maintenance industrielle"
        in vPreparation["interview"]["pitch"]["short"]
    )
    assert "réunit la maintenance industrielle" in vPreparation["letter"]


def test_profile_without_both_worlds_gets_an_advice_only():
    """Vérifie le conseil sans phrase de pitch quand le profil n'a qu'un monde."""

    vProfile = {
        **HYBRID_PROFILE,
        "skills": ["GMAO"],
        "experiences": [HYBRID_PROFILE["experiences"][0]],
    }
    vAdvice = build_hybrid_advice(vProfile, {"title": "Ingénieur SCADA"})

    assert not vAdvice["profile_fits"] and vAdvice["pitch"] == ""
    assert "chacun des deux domaines" in vAdvice["advice"]
    assert (
        build_hybrid_advice(
            {**HYBRID_PROFILE, "experiences": []}, {"title": "Ingénieur SCADA"}
        )["headline"]
        == DEFAULT_HEADLINE
    )
