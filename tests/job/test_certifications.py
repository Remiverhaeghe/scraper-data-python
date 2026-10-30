"""Tests des certifications citées par les offres et suivies par le candidat"""

from datetime import date, datetime

import pytest

from job.certifications import (
    add_months,
    build_overview,
    build_plan,
    describe_offer_certifications,
    describe_validity,
    detect_certifications,
    find_renewals,
    load_details,
    load_owned,
    save_details,
    save_owned,
)
from storage.attachments import add_attachment
from storage.database import initialize_database

TODAY = date(2026, 10, 30)


@pytest.mark.parametrize(
    ("pText", "pExpected"),
    [
        ("Habilitation électrique B2V-BR souhaitée", {"habilitation-electrique"}),
        ("Titulaire du BR et du SST", {"habilitation-electrique", "sst"}),
        ("Bretagne, bras robotisé, SST en cours", {"sst"}),
        ("CACES R489 catégorie 3 exigé", {"caces-r489"}),
        ("CACES apprécié", {"caces"}),
        ("Connaissance de la norme ISO 9001 et ISO 14001", {"iso-9001", "qse"}),
        ("Programmation sous TIA Portal", {"tia-portal"}),
        ("Anglais technique lu", {"anglais"}),
        ("Fluent English required", set()),
        ("Permis B obligatoire", {"permis-b"}),
        ("Rien de particulier", set()),
    ],
)
def test_certifications_are_found_in_offers(pText, pExpected):
    """Vérifie le repérage : sigles en capitales, CACES par type, faux amis écartés."""

    assert detect_certifications(pText) == pExpected


def test_validity_and_renewal_reminder(tmp_path):
    """Vérifie la fin de validité, l'alerte avant échéance et le retrait."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_owned(vDatabaseFile, "sst", date(2024, 12, 15))
    save_owned(vDatabaseFile, "permis-b", date(2010, 5, 2))

    assert describe_validity("sst", "2024-12-15", TODAY) == (date(2026, 12, 15), "soon")
    assert describe_validity("sst", "2024-01-15", TODAY)[1] == "expired"
    assert describe_validity("permis-b", "2010-05-02", TODAY) == (None, "valid")
    assert find_renewals(vDatabaseFile, TODAY) == [
        {
            "label": "Sauveteur secouriste du travail (SST)",
            "valid_until": "2026-12-15",
            "status": "soon",
        }
    ]

    save_owned(vDatabaseFile, "sst", None)

    assert load_owned(vDatabaseFile) == {"permis-b": "2010-05-02"}
    with pytest.raises(ValueError):
        save_owned(vDatabaseFile, "inconnue", TODAY)


def test_month_addition_keeps_a_valid_day():
    """Vérifie l'ajout de mois en fin de mois."""

    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2024, 11, 30), 24) == date(2026, 11, 30)


def test_plan_picks_the_certifications_covering_most_offers():
    """Vérifie le plan : la certification la plus utile d'abord, puis la suivante."""

    vSets = [{"sst"}, {"sst", "caces"}, {"caces"}, {"atex"}, set()]
    vPlan = build_plan(vSets, {})

    assert vPlan["plan"][0] == "caces"
    assert set(vPlan["plan"]) == {"caces", "sst", "atex"}
    assert (vPlan["citing"], vPlan["covered_before"], vPlan["covered_after"]) == (
        4,
        0,
        100,
    )
    assert build_plan(vSets, {"sst": "2025-01-01"})["covered_before"] == 50


def test_overview_counts_close_offers_and_marks_owned(tmp_path):
    """Vérifie les comptes, l'offre proche du profil et la certification détenue."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_owned(vDatabaseFile, "sst", TODAY)
    vOffers = [
        {"title": "Technicien", "description": "SST et CACES", "match_score": 80},
        {"title": "Opérateur", "description": "CACES R489", "match_score": 20},
    ]

    vRows = {
        vRow["id"]: vRow
        for vRow in build_overview(vDatabaseFile, vOffers, TODAY)["rows"]
    }

    assert (vRows["caces"]["count"], vRows["caces"]["close_count"]) == (1, 1)
    assert vRows["caces-r489"]["close_count"] == 0
    assert vRows["sst"]["obtained"] == TODAY.isoformat()
    assert describe_offer_certifications(vOffers[0], {"sst": "x"}) == (
        "CACES (type non précisé par l'offre) (à passer) · "
        "Sauveteur secouriste du travail (SST) (vous l'avez)"
    )


def test_details_documents_and_printed_expiry(tmp_path):
    """Vérifie les informations saisies, l'expiration lue et les documents comptés."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_owned(vDatabaseFile, "habilitation-electrique", date(2026, 1, 10))
    save_details(
        vDatabaseFile,
        "habilitation-electrique",
        {"organism": " Apave ", "level": "B2V-BR", "expires": "2026-12-01", "x": "y"},
    )

    for vName in ("titre.pdf", "carte.jpg"):
        add_attachment(
            vDatabaseFile,
            "certification",
            "habilitation-electrique",
            vName,
            b"contenu",
            datetime(2026, 10, 30),
        )

    vRow = next(
        vRow
        for vRow in build_overview(vDatabaseFile, [], TODAY)["rows"]
        if vRow["id"] == "habilitation-electrique"
    )

    assert load_details(vDatabaseFile)["habilitation-electrique"] == {
        "organism": "Apave",
        "level": "B2V-BR",
        "expires": "2026-12-01",
    }
    assert (vRow["valid_until"], vRow["status"], vRow["documents"]) == (
        "2026-12-01",
        "soon",
        2,
    )

    with pytest.raises(ValueError):
        save_details(vDatabaseFile, "sst", {"verify_link": "file:///C:/secret"})
    with pytest.raises(ValueError):
        save_details(vDatabaseFile, "sst", {"expires": "31/12/2026"})

    save_details(vDatabaseFile, "habilitation-electrique", {"notes": "  "})

    assert not load_details(vDatabaseFile)
