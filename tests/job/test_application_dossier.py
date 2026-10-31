"""Tests du dossier de candidature en PDF"""

import io
from datetime import date

from pypdf import PdfReader

import job.application_dossier as dossier
from job.application_dossier import (
    build_dossier_blocks,
    describe_company_lines,
    write_dossier_pdf,
)
from job.pdf_document import PAGE_BREAK, write_pdf

PROFILE = {
    "name": "Camille Martin",
    "headline": "Technicienne de maintenance",
    "skills": ["GMAO", "Électrotechnique"],
    "experiences": [
        {"title": "Technicienne chez Acme", "skills": "GMAO", "achievement": ""}
    ],
    "cv_variants": [],
    "skill_levels": {},
    "diplomas": [],
    "education_level": None,
}
OFFER = {
    "source": "adzuna",
    "source_id": "1",
    "title": "Technicien de maintenance H/F",
    "company": "Roquette",
    "location": "Lestrem",
    "url": "https://www.adzuna.fr/details/1",
    "description": "Maintenance préventive et curative. GMAO exigée.",
    "salary_net_monthly_min": float("nan"),
}
COMPANY = {
    "name": "ROQUETTE FRERES",
    "activity": "Industrie manufacturière",
    "category": "Grande entreprise",
    "employees": "5 000 à 9 999 salariés",
    "created": "1933",
    "city": "LESTREM",
    "revenue": None,
    "sites": 12,
    "active": True,
    "nearest": {"city": "Lestrem", "distance_km": 28},
    "url": "https://annuaire-entreprises.data.gouv.fr/entreprise/1",
}


def read_pages(pContent):
    """Retourne le texte de chaque page d'un PDF."""

    rPages = [vPage.extract_text() for vPage in PdfReader(io.BytesIO(pContent)).pages]

    return rPages


def test_dossier_has_one_part_per_page(monkeypatch):
    """Vérifie les quatre pages : offre, CV, lettre modifiée, entreprise et questions."""

    monkeypatch.setattr(dossier, "lookup_company", lambda *pArgs: [COMPANY])

    vPages = read_pages(
        write_dossier_pdf(PROFILE, OFFER, "Madame,\nMa lettre", None, date(2026, 11, 2))
    )

    assert len(vPages) == 4
    assert vPages[0].startswith("Dossier de candidature")
    assert "Préparé le 02/11/2026 pour Camille Martin" in vPages[0]
    assert "4. Questions à poser" in vPages[0]
    assert vPages[1].startswith("Camille Martin")
    assert vPages[2] == "Lettre de motivation\nMadame,\nMa lettre"
    assert "Effectif : 5 000 à 9 999 salariés" in vPages[3]
    assert "Le plus proche : Lestrem, 28 km de chez vous" in vPages[3]
    assert "Questions à poser\n•" in vPages[3]


def test_company_sheet_explains_its_absence():
    """Vérifie la fiche absente : service muet, aucun résultat, entreprise étrangère."""

    def failing(*_pArgs):
        raise ValueError("Le service public ne répond pas.")

    def texts(pOffer, pLookup):
        return [
            vBlock[0]
            for vBlock in build_dossier_blocks(PROFILE, pOffer, pLookup=pLookup)
        ]

    assert "Fiche indisponible : Le service public ne répond pas." in texts(
        OFFER, failing
    )
    assert "Aucune entreprise trouvée sous ce nom dans l'annuaire." in texts(
        OFFER, lambda *pArgs: []
    )
    assert any(
        "entreprises françaises" in vText
        for vText in texts({**OFFER, "country": "Belgique"}, failing)
    )
    assert any(
        vText.startswith("Madame, Monsieur,")
        for vText in texts(OFFER, lambda *pArgs: [])
    )


def test_company_lines_skip_missing_facts_and_flag_closure():
    """Vérifie les lignes de la fiche sans les valeurs absentes, et la fermeture."""

    vLines = describe_company_lines({**COMPANY, "nearest": None, "active": False})

    assert vLines[0] == "Activité : Industrie manufacturière"
    assert "Siège : Lestrem" in vLines
    assert not any(vLine.startswith(("Chiffre", "Le plus proche")) for vLine in vLines)
    assert vLines[-1] == "Entreprise fermée d'après l'annuaire."


def test_page_break_is_ignored_at_the_top_of_a_page():
    """Vérifie qu'un saut de page en tête ne crée pas de page vide."""

    vBreak = (PAGE_BREAK, 10, False, 0)
    vPages = read_pages(
        write_pdf(
            [vBreak, ("Un", 10, False, 0), vBreak, vBreak, ("Deux", 10, False, 0)]
        )
    )

    assert vPages == ["Un", "Deux"]
