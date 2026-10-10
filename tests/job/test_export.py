"""Tests de l'export des offres"""

import json

import pandas as pd
import pytest

from job.export import export_offers, protect_formula


def build_offers():
    """Construit deux offres, dont une au titre qu'un tableur prendrait pour une formule."""

    rOffers = pd.DataFrame(
        [
            {
                "title": "Développeur Java",
                "company": "Kent",
                "source": "adzuna",
                "remote": 1,
                "application_status": "APPLIED",
                "salary_net_monthly_min": 2500.0,
            },
            {
                "title": '=HYPERLINK("https://example.com")',
                "company": "Inconnue",
                "source": "lever",
                "remote": None,
                "application_status": None,
                "salary_net_monthly_min": None,
            },
        ]
    )

    return rOffers


@pytest.mark.parametrize(
    "pValue, pExpected",
    [
        ("=1+1", "'=1+1"),
        ("+33 6", "'+33 6"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("Développeur", "Développeur"),
        (2500.0, 2500.0),
    ],
)
def test_protect_formula(pValue, pExpected):
    """Vérifie que seules les valeurs pouvant devenir des formules sont préfixées."""

    assert protect_formula(pValue) == pExpected


def test_export_csv_uses_readable_labels(tmp_path):
    """Vérifie le CSV : intitulés français, libellés et formules neutralisées."""

    vPath = tmp_path / "offres.csv"

    assert export_offers(build_offers(), vPath) == 2

    vExported = pd.read_csv(vPath, sep=";", encoding="utf-8-sig")

    assert vExported.loc[0, "Titre"] == "Développeur Java"
    assert vExported.loc[0, "Source"] == "Adzuna"
    assert vExported.loc[0, "Télétravail"] == "Oui"
    assert vExported.loc[0, "Suivi"] == "Postulé"
    assert vExported.loc[1, "Titre"].startswith("'=")


def test_export_excel(tmp_path):
    """Vérifie que le fichier Excel se relit avec les mêmes intitulés."""

    vPath = tmp_path / "offres.xlsx"

    export_offers(build_offers(), vPath)

    vExported = pd.read_excel(vPath)

    assert list(vExported.columns[:3]) == ["Titre", "Entreprise", "Lieu"]
    assert vExported.loc[1, "Titre"].startswith("'=")


def test_export_json_keeps_technical_values(tmp_path):
    """Vérifie que le JSON garde les noms et codes techniques."""

    vPath = tmp_path / "offres.json"

    export_offers(build_offers(), vPath)

    vExported = json.loads(vPath.read_text(encoding="utf-8"))

    assert vExported[0]["title"] == "Développeur Java"
    assert vExported[0]["application_status"] == "APPLIED"


def test_export_rejects_unknown_format(tmp_path):
    """Vérifie qu'une extension inconnue est refusée."""

    with pytest.raises(ValueError, match=".txt"):
        export_offers(build_offers(), tmp_path / "offres.txt")
