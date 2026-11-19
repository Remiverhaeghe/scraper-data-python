"""Tests du bilan mensuel de la recherche"""

from datetime import date, datetime

import pandas as pd
import pytest

from job.monthly_review import (
    build_monthly_review,
    build_review_email,
    compute_average_delay,
    describe_change,
    get_due_month,
    get_previous_month,
    send_monthly_review_if_due,
)
from storage.database import initialize_database
from storage.job_applications import save_application
from storage.job_offers import save_offers


@pytest.fixture
def database_file(tmp_path):
    """Retourne une base avec trois candidatures fictives d'octobre."""

    rDatabaseFile = tmp_path / "scraper.db"
    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {"source": "lever", "source_id": vId, "title": "Dev", "company": vId}
                for vId in ("a", "b", "c")
            ]
        ),
        datetime(2026, 9, 1),
    )
    save_application(rDatabaseFile, "lever", "a", "APPLIED", pNow=datetime(2026, 9, 28))
    save_application(rDatabaseFile, "lever", "b", "APPLIED", pNow=datetime(2026, 10, 2))
    save_application(rDatabaseFile, "lever", "c", "APPLIED", pNow=datetime(2026, 10, 5))
    # Réponses en octobre : 10 jours puis 5 jours après l'envoi
    save_application(
        rDatabaseFile, "lever", "a", "REJECTED", pNow=datetime(2026, 10, 8)
    )
    save_application(
        rDatabaseFile, "lever", "b", "INTERVIEW", pNow=datetime(2026, 10, 7)
    )

    return rDatabaseFile


def test_previous_month_and_change():
    """Vérifie le mois précédent, janvier compris, et l'écart décrit."""

    assert get_previous_month(date(2026, 11, 1)) == date(2026, 10, 1)
    assert get_previous_month(date(2026, 1, 1)) == date(2025, 12, 1)
    assert describe_change(3, 1) == "+2"
    assert describe_change(1, 3) == "−2"
    assert describe_change(2, 2) == "="


def test_review_counts_and_average_delay(database_file):
    """Vérifie le bilan d'octobre : nombres, comparaison et délai moyen."""

    vReview = build_monthly_review(database_file, date(2026, 10, 1))
    vLines = {vLine["label"]: vLine for vLine in vReview["lines"]}

    assert vReview["title"] == "Bilan d'octobre 2026"
    assert vLines["Candidatures"] == {
        "label": "Candidatures",
        "count": 2,
        "previous": 1,
    }
    assert vLines["Réponses reçues"]["count"] == 2
    assert vReview["average_delay"] == 8
    assert compute_average_delay(database_file, date(2026, 9, 1)) is None


def test_review_email(database_file):
    """Vérifie le sujet, le texte et le HTML échappé de l'e-mail."""

    vSubject, vText, vHtml = build_review_email(
        build_monthly_review(database_file, date(2026, 10, 1))
    )

    assert vSubject.endswith(": bilan d'octobre 2026")
    assert "Candidatures : 2 (+1 sur le mois précédent)" in vText
    assert "Délai moyen de réponse : 8 j." in vText
    assert "<li>Candidatures : 2 (+1 sur le mois précédent)</li>" in vHtml

    vEmpty = build_review_email(build_monthly_review(database_file, date(2026, 5, 1)))

    assert vEmpty[0].endswith(": bilan de mai 2026")
    assert "aucune réponse reçue ce mois-ci" in vEmpty[1]


def test_review_is_sent_once_per_month(database_file):
    """Vérifie l'envoi au début du mois suivant, une seule fois, et sans adresse."""

    vSent = []
    vNow = datetime(2026, 11, 2, 8, 0)

    def send(*pArgs):
        vSent.append(pArgs)

    assert send_monthly_review_if_due(database_file, vNow, "", send) is False
    assert get_due_month(database_file, vNow) == date(2026, 10, 1)
    assert send_monthly_review_if_due(database_file, vNow, "moi@example.org", send)
    assert vSent[0][0] == "moi@example.org"
    assert "octobre 2026" in vSent[0][1]
    assert get_due_month(database_file, vNow) is None
    assert not send_monthly_review_if_due(database_file, vNow, "moi@example.org", send)
    assert len(vSent) == 1
