"""Tests du pitch de présentation"""

from job.pitch import build_pitch, describe_of, describe_target, end_sentence
from job.profile import EMPTY_PROFILE

PROFILE = {
    **EMPTY_PROFILE,
    "headline": "Développeur Python backend",
    "experiences": [
        {
            "title": "Développeur",
            "skills": ["Python"],
            "achievement": "Livré une API de paiement",
        },
        {"title": "Stagiaire data", "skills": ["SQL"], "achievement": ""},
    ],
}

MATCH = {"covered": ["Python", "SQL"], "missing": ["Docker"]}


def test_short_pitch_presents_profile_and_offer():
    """Vérifie le pitch court : accroche, parcours, compétences, poste visé."""

    rPitch = build_pitch(PROFILE, MATCH, {"title": "Dev Python", "company": "Acme"})

    assert rPitch["short"] == (
        "Développeur Python backend. J'ai notamment été développeur puis stagiaire "
        "data. Je pratique Python, SQL, des compétences demandées ici. Je souhaite "
        "aujourd'hui mettre mon expérience au service d'Acme sur le poste de "
        "Dev Python."
    )


def test_long_pitch_adds_example_gap_and_question():
    """Vérifie le pitch long : réalisation, compétence en cours, question finale."""

    rPitch = build_pitch(PROFILE, MATCH, {"title": "Dev Python", "company": "Globex"})

    assert "Comme développeur, j'ai par exemple livré une API de paiement." in (
        rPitch["long"]
    )
    assert "Je progresse aussi sur Docker" in rPitch["long"]
    assert "au service de Globex" in rPitch["long"]
    assert rPitch["long"].endswith("rejoindra l'équipe ?")


def test_pitch_with_empty_profile_keeps_the_offer():
    """Vérifie qu'un profil vide donne au moins la phrase sur le poste."""

    rPitch = build_pitch(EMPTY_PROFILE, {"covered": [], "missing": []}, {})

    assert rPitch["short"] == (
        "Je souhaite aujourd'hui mettre mon expérience au service de ce poste."
    )


def test_end_sentence_and_describe_of():
    """Vérifie la ponctuation finale et l'élision devant une voyelle."""

    assert end_sentence("Bonjour ") == "Bonjour."
    assert end_sentence("Prêt ?") == "Prêt ?"
    assert describe_of("Hermès") == "d'Hermès"
    assert describe_of("Thales") == "de Thales"
    assert describe_target("Acme", None) == "d'Acme"
    assert describe_target(None, "Dev") == "du poste de Dev"
