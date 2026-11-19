"""Tests de la relecture des lettres de candidature"""

import pytest

from job.application_review import (
    MAX_WORDS,
    MIN_WORDS,
    count_words,
    describe_length,
    find_keywords,
    find_mistakes,
    review_letter,
)

OFFER = {
    "title": "Technicien de maintenance H/F - CDI",
    "company": "Usine Fictive",
    "description": "Vous êtes rigoureux et autonome. Maîtrise de Python et SQL.",
    "skills": '["Python", "SQL"]',
}


def test_count_words_keeps_elisions_and_hyphens():
    """Vérifie le décompte : « l'entreprise » et « peut-être » comptent pour un mot."""

    assert count_words("Je rejoins l'entreprise, peut-être demain.") == 5
    assert count_words("") == 0


@pytest.mark.parametrize(
    ("pWords", "pTone"),
    [
        (0, "danger"),
        (MIN_WORDS - 1, "warning"),
        (250, "success"),
        (MAX_WORDS + 1, "warning"),
    ],
)
def test_describe_length(pWords, pTone):
    """Vérifie l'avis sur la longueur selon le nombre de mots."""

    assert describe_length(pWords)[1] == pTone


@pytest.mark.parametrize(
    ("pText", "pAdvice"),
    [
        ("Je me permet de vous écrire.", "Je me permets"),
        ("Quelque soit le poste.", "Quel que soit"),
        ("En temps que technicien.", "En tant que"),
        ("Pour pallier à ce manque.", "sans « à »"),
        ("Un parcours professionel.", "deux n"),
        ("Le dévelopement web.", "un l, deux p"),
        ("Une connection stable.", "connexion"),
        ("Je parle anglais courament.", "deux m"),
        ("Je suis le le candidat.", "Mot répété"),
        ("Chez [Entreprise], je…", "Reste du modèle"),
        ("Bonjour Madame XXXX,", "Reste du modèle"),
        ("Pourquoi moi? Parce que.", "Une espace avant"),
        ("Mes atouts: rigueur.", "Une espace avant"),
        ("Deux  espaces.", "Double espace"),
        ("Vous trouverez ci-joint mon CV.", "Le CV est joint"),
    ],
)
def test_common_mistakes_are_found(pText, pAdvice):
    """Vérifie le repérage de chaque faute courante."""

    assert any(pAdvice in vItem["advice"] for vItem in find_mistakes(pText))


def test_correct_text_has_no_mistake():
    """Vérifie qu'un texte correct, avec adresse web et heure, n'est pas signalé."""

    vText = (
        "Je me permets de vous écrire : mon projet est sur https://exemple.fr ; "
        "nous nous verrons à 9:30 ? En tant que technicien, je développe et le "
        "développement me plaît !"
    )

    assert find_mistakes(vText) == []


def test_keywords_are_marked_found_or_missing():
    """Vérifie les mots-clés : intitulé, entreprise, compétences et qualités."""

    vKeywords = {
        vItem["term"]: vItem
        for vItem in find_keywords(
            "Technicien de maintenance rigoureux, je connais Python.", OFFER
        )
    }

    assert vKeywords["Technicien de maintenance"]["found"] is True
    assert vKeywords["Usine Fictive"] == {
        "term": "Usine Fictive",
        "kind": "Entreprise",
        "found": False,
    }
    assert vKeywords["Python"]["found"] is True
    assert vKeywords["SQL"]["found"] is False
    assert vKeywords["Rigueur"]["found"] is True
    assert vKeywords["Autonomie"]["found"] is False


def test_review_letter_summarizes_everything():
    """Vérifie la relecture complète, et celle d'une lettre vide."""

    vLetter = " ".join(
        ["Technicien autonome chez Usine Fictive, je code en Python."] * 30
    )
    vReview = review_letter(vLetter, OFFER)

    assert vReview["words"] == 270
    assert vReview["length"][1] == "success"
    assert vReview["found_share"] == 50
    assert vReview["long_sentences"] == 0

    vEmpty = review_letter("", OFFER)

    assert vEmpty["keywords"] == []
    assert vEmpty["found_share"] == 0
    assert vEmpty["length"] == ("Lettre vide.", "danger")
    assert review_letter(" ".join(["mot"] * 45) + ".", {})["long_sentences"] == 1


def test_keywords_ignore_case_duplicates():
    """Vérifie qu'une compétence écrite deux fois avec une casse différente compte une fois."""

    vKeywords = find_keywords("", {"skills": '["python"]', "title": "Dev Python"})

    assert [vItem["term"].lower() for vItem in vKeywords].count("python") == 1
