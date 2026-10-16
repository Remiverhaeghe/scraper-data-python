"""Tests du classement des thèmes de révision par domaine et du compte des offres"""

import json
from datetime import datetime

import pandas as pd
import pytest

import job.quiz as quiz
from job.quiz import build_quiz_overview, load_active_quiz
from job.quiz_domains import (
    OTHER_DOMAIN,
    classify_theme,
    count_categories,
    group_themes,
)
from job.quiz_import import import_questions
from storage.database import initialize_database
from storage.job_offers import save_offers

NOW = datetime(2026, 10, 12, 10, 0)


@pytest.mark.parametrize(
    "pLabel, pSkills, pExpected",
    [
        ("Python et automatisation", (), ("Informatique", "Développement")),
        ("Cybersécurité et réseau", (), ("Réseau et sécurité", "Sécurité et identité")),
        ("Réseaux et diagnostic", (), ("Réseau et sécurité", "Réseau")),
        ("Automatisme industriel et API/PLC", (), ("Industrie", "Automatisme")),
        ("Analyse mémoire", ("JVM", "GC"), ("Informatique", "Exploitation et DevOps")),
        ("Kafka", (), OTHER_DOMAIN),
    ],
)
def test_classify_theme(pLabel, pSkills, pExpected):
    """Vérifie le classement par le libellé, puis par les compétences."""

    assert classify_theme(pLabel, pSkills) == pExpected


def test_group_themes_keeps_display_order_and_filters():
    """Vérifie l'ordre des domaines et sous-domaines et le filtre par domaine."""

    vThemes = [
        {"label": "Méca", "domain": "Industrie", "subdomain": "Mécanique et fluides"},
        {"label": "SQL", "domain": "Informatique", "subdomain": "Données"},
        {"label": "Java", "domain": "Informatique", "subdomain": "Développement"},
    ]

    vGroups = group_themes(vThemes)

    assert [vDomain for vDomain, _ in vGroups] == ["Informatique", "Industrie"]
    assert [vSubdomain for vSubdomain, _ in vGroups[0][1]] == [
        "Développement",
        "Données",
    ]
    assert group_themes(vThemes, "Industrie")[0][1][0][1][0]["label"] == "Méca"


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec trois offres au texte varié."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "1",
                    "title": "Admin Tomcat",
                    "description": "Tomcat, logs applicatifs et analyse GC",
                },
                {
                    "source": "remotive",
                    "source_id": "2",
                    "title": "Support",
                    "description": "Lecture de logs uniquement",
                },
                {
                    "source": "remotive",
                    "source_id": "3",
                    "title": "Comptable",
                    "description": "Pas de gc en minuscules, tomcatisme inventé",
                },
            ]
        ),
        NOW,
    )

    return rDatabaseFile


def import_theme(pDatabaseFile, pTheme, pSkills, **pExtra):
    """Importe un thème d'une question avec ses compétences."""

    import_questions(
        pDatabaseFile,
        "",
        json.dumps(
            {
                "theme": pTheme,
                "skills": pSkills,
                **pExtra,
                "questions": [
                    {
                        "id": f"{pTheme.lower()}-001",
                        "level": "débutant",
                        "question": f"{pTheme} ?",
                        "choices": ["a", "b"],
                        "answer": 0,
                        "explanation": "x",
                    }
                ],
            }
        ),
        NOW,
    )


def test_offer_count_needs_two_skills_and_exact_acronyms(database_file):
    """Vérifie le compte par texte : deux compétences, sigles en majuscules."""

    import_theme(database_file, "Exploitation", ["Tomcat", "logs", "GC"])
    import_theme(database_file, "Tracing", ["logs"])

    vCounts = {
        vTheme["label"]: vTheme["offer_count"]
        for vTheme in build_quiz_overview(
            database_file, load_active_quiz(database_file)
        )
    }

    assert vCounts["Exploitation"] == 1
    assert vCounts["Tracing"] == 2
    assert vCounts["Python"] == 0


def test_offer_count_is_cached_until_offers_change(database_file, monkeypatch):
    """Vérifie qu'un second affichage ne relit pas les offres."""

    import_theme(database_file, "Exploitation", ["Tomcat", "logs"])
    build_quiz_overview(database_file, load_active_quiz(database_file))

    monkeypatch.setattr(quiz, "get_offer_texts", pytest.fail)

    build_quiz_overview(database_file, load_active_quiz(database_file))


def test_pack_domain_overrides_classification(database_file):
    """Vérifie le domaine indiqué par un pack, et le refus d'un domaine inconnu."""

    import_theme(
        database_file, "Kafka", ["Kafka"], domain="Informatique", subdomain="Données"
    )
    import_theme(
        database_file, "Rust", ["Rust"], domain="Cuisine", subdomain="Desserts"
    )

    vDomains = {
        vTheme["label"]: (vTheme["domain"], vTheme["subdomain"])
        for vTheme in build_quiz_overview(
            database_file, load_active_quiz(database_file)
        )
    }

    assert vDomains["Kafka"] == ("Informatique", "Données")
    assert vDomains["Rust"] == OTHER_DOMAIN


def test_count_categories_keeps_empty_rubrics():
    """Vérifie les comptes par rubrique, rubriques vides comprises, « Autres » masqué."""

    vThemes = [
        {"domain": "Informatique", "subdomain": "Données"},
        {"domain": "Informatique", "subdomain": "Données"},
        {"domain": "Industrie", "subdomain": "Automatisme"},
    ]

    vCounts = count_categories(vThemes)

    assert vCounts[(None, None)] == 3
    assert vCounts[("Informatique", None)] == 2
    assert vCounts[("Informatique", "Données")] == 2
    assert vCounts[("Réseau et sécurité", "Réseau")] == 0
    assert vCounts[("Industrie", "Maintenance")] == 0
    assert (OTHER_DOMAIN[0], None) not in vCounts
    assert list(vCounts)[1] == ("Informatique", None)

    vCounts = count_categories([{"domain": "Autres", "subdomain": "Divers"}])

    assert vCounts[OTHER_DOMAIN] == 1
