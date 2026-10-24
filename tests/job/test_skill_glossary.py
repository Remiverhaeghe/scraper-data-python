"""Tests du glossaire des compétences"""

from job.skill_glossary import build_glossary, describe_skill, list_undefined_skills


def test_every_detected_skill_has_a_definition():
    """Vérifie qu'aucune compétence repérée dans les offres n'est sans définition."""

    assert not list_undefined_skills()


def test_definitions_are_found_without_case():
    """Vérifie la recherche sans casse, et None pour une compétence inconnue."""

    assert describe_skill(" python ").startswith("Langage polyvalent")
    assert describe_skill("Cobol") is None
    assert describe_skill(None) is None


def test_glossary_is_sorted_and_limited_to_known_skills():
    """Vérifie l'ordre alphabétique et l'écart des compétences inconnues."""

    assert [vSkill for vSkill, _ in build_glossary(["sql", "Cobol", "Docker"])] == [
        "Docker",
        "SQL",
    ]
    assert len(build_glossary()) >= 87
