"""Tests des mots de l'annonce à reprendre dans le CV"""

from job.cv_keywords import build_keyword_advice, clean_title

PROFILE = {
    "headline": "Technicien de maintenance industrielle",
    "skills": ["TIA Portal", "GMAO"],
    "experiences": [
        {
            "title": "Technicien de maintenance",
            "skills": "Siemens TIA Portal",
            "achievement": "Travail rigoureux et autonome sur ligne de production",
        }
    ],
}
OFFER_TEXT = (
    "Technicien de maintenance H/F. Vous maîtrisez Siemens TIA Portal et la GMAO. "
    "Autonomie, rigueur et esprit d'équipe. Travail en 3x8, astreintes, permis B. "
    "Habilitation électrique exigée."
)
MATCH = {
    "covered": ["GMAO", "Siemens TIA Portal", "Électrotechnique"],
    "missing": ["Habilitation électrique", "Anglais"],
    "required": ["Siemens TIA Portal", "Habilitation électrique"],
}


def test_title_is_cleaned_of_gender_contract_and_place():
    """Vérifie l'intitulé débarrassé du genre, du contrat et du lieu."""

    assert clean_title("Technicien de maintenance (H/F)- CDI - Secteur Blangy") == (
        "Technicien de maintenance"
    )
    assert clean_title("Technicien chauffage F/H/N") == "Technicien chauffage"
    assert clean_title("Automaticien (CDI)") == "Automaticien"
    assert clean_title("Électricien / automaticien") == "Électricien / automaticien"
    assert clean_title(None) == ""


def test_keywords_are_marked_present_or_to_write():
    """Vérifie l'intitulé, les compétences exigées en tête, qualités et conditions."""

    vAdvice = build_keyword_advice(
        PROFILE, {"title": "Technicien de maintenance H/F"}, MATCH, OFFER_TEXT
    )

    assert vAdvice["title"] == "Technicien de maintenance"
    assert vAdvice["title_in_cv"]
    assert vAdvice["skills"] == [
        {"term": "Siemens TIA Portal", "required": True, "in_cv": True},
        {"term": "GMAO", "required": False, "in_cv": True},
        {"term": "Électrotechnique", "required": False, "in_cv": False},
    ]
    assert vAdvice["qualities"] == [
        {"term": "Autonomie", "in_cv": True},
        {"term": "Rigueur", "in_cv": True},
        {"term": "Esprit d'équipe", "in_cv": False},
    ]
    assert vAdvice["conditions"] == ["Astreintes", "Travail posté", "Permis B"]
    assert vAdvice["missing_required"] == ["Habilitation électrique"]


def test_generic_wording_does_not_trigger_rules():
    """Vérifie qu'un poste « au sein d'une équipe » ou « notre organisation » ne compte pas."""

    vAdvice = build_keyword_advice(
        {},
        {"title": ""},
        {},
        "Le poste au sein d'une équipe de nuitée ; notre organisation grandit.",
    )

    assert vAdvice == {
        "title": "",
        "title_in_cv": False,
        "skills": [],
        "qualities": [],
        "conditions": [],
        "missing_required": [],
    }
