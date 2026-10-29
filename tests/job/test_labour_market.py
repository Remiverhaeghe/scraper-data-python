"""Tests des métiers qui recrutent, d'après l'enquête BMO de France Travail"""

import io

import openpyxl
import pytest

import job.labour_market as labour_market
from job.labour_market import (
    build_offers_link,
    build_outlook,
    count_matching_words,
    describe_outlook_row,
    list_summary_years,
    read_count,
    refresh_labour_market,
    summarize_bmo,
)
from job.profile import EMPTY_PROFILE

HEADER = (
    "annee",
    "Code métier BMO",
    "Nom métier BMO",
    "Famille_met",
    "Lbl_fam_met",
    "REG",
    "NOM_REG",
    "Dept",
    "NomDept",
    "BE26",
    "NOMBE26",
    "met",
    "xmet",
    "smet",
)


def build_workbook(pRows):
    """Retourne un tableur BMO minimal : une ligne par (code, métier, dép., projets)."""

    vBook = openpyxl.Workbook()
    vBook.active.title = "Description_des_variables"
    vSheet = vBook.create_sheet("BMO_open_data")
    vSheet.append(HEADER)

    for vCode, vLabel, vDepartment, vCounts in pRows:
        vSheet.append(
            (
                2026,
                vCode,
                vLabel,
                "Z",
                "Famille",
                "32",
                "Hauts-de-France",
                vDepartment,
                f"Dép. {vDepartment}",
                1,
                "Bassin",
                *vCounts,
            )
        )

    vBuffer = io.BytesIO()
    vBook.save(vBuffer)

    rContent = vBuffer.getvalue()

    return rContent


@pytest.fixture(name="bmo_directory")
def fixture_bmo_directory(tmp_path, monkeypatch):
    """Range les résumés de l'enquête dans un dossier propre au test."""

    monkeypatch.setattr(labour_market, "BMO_DIRECTORY", tmp_path / "bmo")

    return tmp_path / "bmo"


def test_counts_hide_masked_values():
    """Vérifie qu'une valeur masquée ou absente compte pour zéro."""

    assert [read_count(vValue) for vValue in ("12", 7, "*", None, "3.0")] == [
        12,
        7,
        0,
        0,
        3,
    ]


def test_survey_is_summarized_by_job_and_department():
    """Vérifie le cumul par métier, en France et par département."""

    vSummary = summarize_bmo(
        build_workbook(
            [
                ("J1X80", "Développeurs informatiques", "59", ("100", "60", "0")),
                ("J1X80", "Développeurs informatiques", "62", ("50", "*", "5")),
            ]
        ),
        2026,
    )

    assert vSummary["jobs"]["J1X80"]["france"] == [150, 60, 5]
    assert vSummary["jobs"]["J1X80"]["departments"]["62"] == [50, 0, 5]
    assert vSummary["departments"] == {"59": "Dép. 59", "62": "Dép. 62"}


def test_outlook_compares_two_years_and_finds_my_jobs(bmo_directory, monkeypatch):
    """Vérifie les listes : vos métiers, en hausse, difficiles et les plus demandés."""

    monkeypatch.setattr(labour_market, "MIN_FRANCE_PROJECTS", 100)
    vFiles = {
        2025: build_workbook(
            [
                (
                    "J1X80",
                    "Ingénieurs du développement informatique",
                    "59",
                    ("200", "40", "0"),
                ),
                ("S1X20", "Serveurs de cafés restaurants", "59", ("900", "300", "800")),
            ]
        ),
        2026: build_workbook(
            [
                (
                    "J1X80",
                    "Ingénieurs du développement informatique",
                    "59",
                    ("300", "180", "0"),
                ),
                ("S1X20", "Serveurs de cafés restaurants", "59", ("800", "200", "700")),
            ]
        ),
    }
    monkeypatch.setattr(
        labour_market, "list_bmo_files", lambda: {2026: "a", 2025: "b", 2024: "c"}
    )
    monkeypatch.setattr(
        labour_market,
        "request_bytes",
        lambda pMethod, pUrl, **pOptions: vFiles[{"a": 2026, "b": 2025}[pUrl]],
    )

    assert build_outlook(EMPTY_PROFILE) is None
    assert refresh_labour_market() == [2026, 2025]
    assert list_summary_years() == [2026, 2025]

    vOutlook = build_outlook({**EMPTY_PROFILE, "headline": "Développeur Python"})

    assert vOutlook["scope"] == "France"
    assert [vRow["label"] for vRow in vOutlook["mine"]] == [
        "Ingénieurs du développement informatique"
    ]
    assert vOutlook["rising"][0]["change"] == 50
    assert vOutlook["difficult"][0]["difficult_share"] == 60
    assert vOutlook["top"][0]["label"] == "Serveurs de cafés restaurants"
    assert build_outlook(EMPTY_PROFILE, "59")["scope"] == "Dép. 59"


def test_profile_words_match_by_their_root():
    """Vérifie le rapprochement par racine : « développeur » et « développement »."""

    assert (
        count_matching_words(
            "Ingénieurs du développement informatique", {"developpeur"}
        )
        == 1
    )
    assert count_matching_words("Serveurs de cafés", {"developpeur"}) == 0


def test_row_is_described_with_its_trend():
    """Vérifie la ligne d'un métier : projets, difficulté, saisonnalité, évolution."""

    vRow = {
        "projects": 12345,
        "difficult_share": 60,
        "seasonal_share": 80,
        "change": -12,
    }

    assert describe_outlook_row(vRow) == (
        "12 345 projets · 60 % difficiles · 80 % saisonniers · -12 % sur un an"
    )
    assert describe_outlook_row({**vRow, "seasonal_share": 10, "change": None}) == (
        "12 345 projets · 60 % difficiles"
    )


def test_offers_link_searches_the_first_words_in_singular():
    """Vérifie que le lien cherche deux mots au singulier, dans le département."""

    assert build_offers_link(
        "Ouvriers du conditionnement, du tri et de l'emballage", "59"
    ) == (
        "https://candidat.francetravail.fr/offres/recherche"
        "?motsCles=ouvrier+conditionnement&offresPartenaires=true&lieux=59D"
    )
    assert "motsCles=technicien+industrie&offresPartenaires=true" in (
        build_offers_link("Techniciens (industrie) des industries de process")
    )
    assert "lieux" not in build_offers_link("Techniciens de process")
