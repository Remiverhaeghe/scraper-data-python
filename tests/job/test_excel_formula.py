"""Tests du moteur de formules Excel : lecture, recopie, calculs et formats"""

import pytest

from job.excel_formula import FormulaError, Sheet, parse_formula, shift_formula
from job.excel_values import format_value

ROWS = [
    ["Pièce", "Stock", "Prix", "Date"],
    ["Roulement", 12, 8.4, "2026-01-31"],
    ["Courroie", 3, 14.9, "2024-02-29"],
    ["Filtre", None, 22.5, "2026-06-30"],
]


def compute(pFormula):
    """Calcule une formule en F1 de la feuille d'essai, au format standard."""

    rText = format_value(Sheet(ROWS, {"F1": pFormula}).value(1, 6))

    return rText


@pytest.mark.parametrize(
    "pFormula, pExpected",
    [
        ("=-2^2", "4"),
        ("=1+2*3", "7"),
        ("=0,1+0,2=0,3", "VRAI"),
        ("=1/3", "0,3333333333"),
        ('="Stock : "&B2', "Stock : 12"),
        ("=SOMME(B2:B4)", "15"),
        ("=MOYENNE(B2:B4)", "7,5"),
        ("=B4*2", "0"),
        ('=SI(B3<5;"Commander";"OK")', "Commander"),
        ('=NB.SI(B2:B4;">=3")', "2"),
        ('=SOMME.SI(A2:A4;"C*";C2:C4)', "14,9"),
        ('=RECHERCHEV("filtre";A2:C4;3;FAUX)', "22,5"),
        ('=RECHERCHEV("Joint";A2:C4;3;FAUX)', "#N/A"),
        ('=SIERREUR(RECHERCHEV("Joint";A2:C4;3;FAUX);"absent")', "absent"),
        ('=INDEX(B2:C4;EQUIV("Courroie";A2:A4;0);2)', "14,9"),
        ("=ARRONDI(2,675;2)", "2,68"),
        ("=ARRONDI(-2,5;0)", "-3"),
        ("=1/0", "#DIV/0!"),
        ('=DATEDIF(D3;D4;"y")', "2"),
        ('=TEXTE(D2;"jjjj jj mmmm aaaa")', "samedi 31 janvier 2026"),
        ("=MOIS.DECALER(D2;1)-DATE(2026;2;28)", "0"),
        ("=NB.JOURS.OUVRES(D2;D4)", "107"),
        ("=AUJOURDHUI()=D4", "VRAI"),
    ],
)
def test_formulas_compute_like_excel(pFormula, pExpected):
    """Vérifie la priorité des opérateurs, les fonctions et les erreurs d'Excel."""

    assert compute(pFormula) == pExpected


@pytest.mark.parametrize(
    "pFormula, pMessage",
    [
        ("B2*2", "commence par le signe ="),
        ("=SOMME(B2,B3)", "point-virgule"),
        ("=SUM(B2:B4)", "elle s'écrit SOMME"),
        ("=Commander", "entre guillemets"),
        ("=SI(B2)", "SI attend de 2 à 3 arguments"),
        ("=(1+2", "parenthèse fermante"),
        ('="abc', "guillemet"),
        ("=" + "(" * 31 + "1" + ")" * 31, "trop imbriquée"),
    ],
)
def test_unreadable_formulas_are_explained(pFormula, pMessage):
    """Vérifie que chaque formule illisible a un message qui dit quoi corriger."""

    with pytest.raises(FormulaError, match=pMessage):
        parse_formula(pFormula)


def test_fill_keeps_absolute_references():
    """Vérifie la recopie : relatives décalées, $ figées, #REF! hors de la feuille."""

    assert shift_formula("=$A2*B$1+SOMME(B:C)", 2, 1) == "=$A4*C$1+SOMME(C:D)"
    assert shift_formula('="B2"&A1', -1, 0) == '="B2"&#REF!'


def test_formats_and_circular_reference():
    """Vérifie les formats euro, pourcentage et date, et une formule qui se cite."""

    vSheet = Sheet(ROWS, {"F1": "=F1+1"})

    assert format_value(1234.5, "euro") == "1234,50 €"
    assert format_value(0.21944, "percent") == "21,94 %"
    assert format_value(46053.0, "date") == "31/01/2026"
    assert format_value(1e-5) == "1E-05"
    assert format_value(vSheet.value(1, 6)) == "#REF!"
    assert vSheet.circular
