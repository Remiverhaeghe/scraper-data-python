"""Tests des informations sur l'entreprise et des demandes préparées pour ChatGPT"""

import pytest
import requests

import job.company_info as company_info
from job.assistant import PROMPT_KINDS, build_prompts, describe_offer
from job.company_info import lookup_company, summarize_company
from job.profile import build_profile

API_RESULT = {
    "nom_complet": "DECATHLON FRANCE",
    "siren": "500569405",
    "section_activite_principale": "G",
    "activite_principale": "47.64Z",
    "tranche_effectif_salarie": "53",
    "categorie_entreprise": "GE",
    "date_creation": "2008-01-15",
    "siege": {"libelle_commune": "VILLENEUVE-D'ASCQ"},
    "finances": {"2024": {"ca": 3500000000}, "2025": {"ca": 3944371232}},
    "etat_administratif": "A",
}


def test_lookup_company_describes_results(monkeypatch):
    """Vérifie la traduction des codes INSEE et le lien vers la fiche officielle."""

    vCalls = []

    def fake_request(pMethod, pUrl, pParams=None):
        """Renvoie un résultat type de l'API publique."""
        vCalls.append(pParams)

        return {"results": [API_RESULT, {"siren": None}]}

    monkeypatch.setattr(company_info, "request_json", fake_request)

    vCompanies = lookup_company("  Decathlon   France ")

    assert vCalls == [{"q": "Decathlon France", "per_page": 3, "page": 1}]
    assert vCompanies[0]["url"].endswith("/entreprise/500569405")
    assert vCompanies[1]["url"] is None
    assert summarize_company(vCompanies[0]) == (
        "DECATHLON FRANCE : Commerce, réparation automobile, Grande entreprise, "
        "10 000 salariés et plus, créée en 2008, siège à Villeneuve-D'Ascq, "
        "chiffre d'affaires 3,9 Md€ en 2025"
    )


def test_lookup_company_errors(monkeypatch):
    """Vérifie les messages pour un nom trop court ou un service indisponible."""

    with pytest.raises(ValueError, match="trop court"):
        lookup_company("ab")

    def fail(*pArgs, **pKwargs):
        """Simule un service public injoignable."""
        raise requests.ConnectionError("injoignable")

    monkeypatch.setattr(company_info, "request_json", fail)

    with pytest.raises(ValueError, match="ne répond pas"):
        lookup_company("Acme")


def test_build_prompts_uses_offer_profile_and_company():
    """Vérifie le contenu des trois demandes préparées."""

    vProfile = build_profile(
        "Rémi",
        "Développeur Java",
        "Java, Spring",
        "Développeur | Java | Migration réussie",
        "CV Java | Java, Spring",
    )
    vOffer = {
        "title": "Développeur Java H/F",
        "company": "Acme",
        "description": "Java, Kafka. " + "x" * 5000,
        "url": "https://acme.example",
    }

    vPrompts = build_prompts(vProfile, vOffer, "ACME : Grande entreprise")

    assert set(vPrompts) == set(PROMPT_KINDS)
    assert "Poste : Développeur Java\nEntreprise : Acme" in vPrompts["interview"]
    assert "CV conseillé pour cette offre : CV Java" in vPrompts["cv"]
    assert "que je n'ai pas indiquées : Kafka" in vPrompts["cv"]
    assert "Informations publiques déjà trouvées : ACME" in vPrompts["company"]
    assert describe_offer(vOffer).endswith("x […]")
