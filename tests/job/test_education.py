"""Tests du diplôme demandé par les offres"""

import json

import pandas as pd
import pytest

from job.education import (
    NO_LEVEL,
    compare_education,
    describe_education,
    detect_education_level,
    refresh_education_levels,
)
from storage.database import connect_database, initialize_database
from storage.job_offers import save_offers

NOW = pd.Timestamp("2026-10-29 10:00").to_pydatetime()


@pytest.mark.parametrize(
    ("pText", "pLevel"),
    [
        ("Titulaire d'un BTS Maintenance des systèmes", 5),
        ("Formation Bac+2 à Bac+5 en électrotechnique", 5),
        ("Diplôme d'ingénieur ou Master 2 en mécanique", 7),
        ("Licence professionnelle ou BUT GEII", 6),
        ("Bachelor's degree in Computer Science", 6),
        ("CAP ou BEP électrotechnique, permis B", 3),
        ("Niveau bac, première expérience appréciée", 4),
        ("Garder le cap, le but est de livrer vite", NO_LEVEL),
        ("Scrum Master, merge sur la branche master", NO_LEVEL),
        ("", NO_LEVEL),
    ],
)
def test_level_is_read_in_the_text(pText, pLevel):
    """Vérifie les niveaux repérés, le plus bas accepté, et les faux amis écartés."""

    assert detect_education_level(None, pText) == pLevel


def test_structured_field_comes_first():
    """Vérifie que le champ formation de la source prime sur le texte."""

    vAlternance = json.dumps({"european": "5", "label": "BTS, DEUST (Bac+2)"})
    vFranceTravail = json.dumps(
        [{"niveauLibelle": "Bac ou équivalent", "exigence": "S"}]
    )

    assert detect_education_level(vAlternance, "Master 2 exigé") == 5
    assert detect_education_level(vFranceTravail, "Bac+5") == 4
    assert detect_education_level("illisible {", "BTS") == 5


@pytest.mark.parametrize(
    ("pRequired", "pMine", "pStatus"),
    [
        (5, 5, "ok"),
        (4, 5, "ok"),
        (6, 5, "close"),
        (7, 5, "blocked"),
        (NO_LEVEL, 5, None),
        (7, None, None),
        (float("nan"), 5, None),
    ],
)
def test_education_gap(pRequired, pMine, pStatus):
    """Vérifie l'écart : accessible, un niveau au-dessus, bloquant ou inconnu."""

    assert compare_education(pRequired, pMine) == pStatus


def test_description_gives_label_and_tone():
    """Vérifie le libellé et la couleur affichés sur une offre."""

    assert (
        describe_education({"education_level": 7, "education_status": "blocked"})[
            "tone"
        ]
        == "danger"
    )
    assert describe_education({"education_level": NO_LEVEL}) is None


def test_levels_are_saved_once_then_recomputed_with_new_rules(tmp_path, monkeypatch):
    """Vérifie le repérage enregistré, puis repris quand les règles changent."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": "1", "title": "Technicien BTS"},
                {"source": "lever", "source_id": "2", "title": "Développeur"},
            ]
        ),
        NOW,
    )

    assert refresh_education_levels(vDatabaseFile) == 2
    assert refresh_education_levels(vDatabaseFile) == 0

    vConnection = connect_database(vDatabaseFile)

    try:
        vLevels = vConnection.execute(
            "SELECT source_id, education_level FROM job_offer ORDER BY source_id"
        ).fetchall()

    finally:
        vConnection.close()

    assert vLevels == [("1", 5), ("2", NO_LEVEL)]

    monkeypatch.setattr("job.education.EDUCATION_VERSION", "autres-regles")

    assert refresh_education_levels(vDatabaseFile) == 2
