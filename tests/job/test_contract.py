"""Tests de la normalisation du type de contrat"""

import pandas as pd
import pytest

from job.contract import add_contract, detect_contract


@pytest.mark.parametrize(
    "pText, pExpected",
    [
        ("Développeur Python H/F (CDI)", "CDI"),
        ("Contrat à durée déterminée de 6 mois", "CDD"),
        ("Mission freelance, TJM selon profil", "FREELANCE"),
        ("Free-lance Python", "FREELANCE"),
        ("Portage salarial possible", "FREELANCE"),
        ("Full-time permanent, Mid-senior", "CDI"),
        ("Unbefristeter Arbeitsvertrag", "CDI"),
        ("parttime fixed term", "CDD"),
        ("Temporary employment", "CDD"),
        ("Befristeter Vertrag", "CDD"),
        ("Full-time contract", None),
        ("Développeur Python", None),
    ],
)
def test_detect_contract(pText, pExpected):
    """Vérifie la détection du contrat dans un texte."""

    assert detect_contract([pText]) == pExpected


def test_detect_contract_skips_ambiguous_text():
    """Vérifie qu'un texte citant plusieurs contrats laisse décider le suivant."""

    assert detect_contract(["Poste en CDI ou freelance", "Contrat : CDD"]) == "CDD"


def test_detect_contract_prefers_first_text():
    """Vérifie que le titre prime sur la description."""

    assert detect_contract(["Développeur (CDI)", "Ancien freelance bienvenu"]) == "CDI"


def test_add_contract_keeps_source_contract():
    """Vérifie que le contrat fourni par la source n'est pas remplacé."""

    vItems = pd.DataFrame(
        [
            {"title": "Mission freelance", "contract": "CDI"},
            {"title": "Mission freelance", "contract": None},
            {"title": "Développeur", "contract": None},
        ]
    )

    rItems = add_contract(vItems)

    assert rItems["contract"].tolist()[:2] == ["CDI", "FREELANCE"]
    assert pd.isna(rItems.loc[2, "contract"])


def test_add_contract_with_empty_items():
    """Vérifie le traitement d'un résultat sans offre."""

    rItems = add_contract(pd.DataFrame(columns=["title", "contract"]))

    assert rItems.empty
