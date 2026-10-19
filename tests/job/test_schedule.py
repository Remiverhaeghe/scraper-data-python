"""Tests des réglages de la recherche planifiée"""

from datetime import datetime

import pytest

from job.schedule import (
    DEFAULT_INTERVAL_HOURS,
    describe_extra_searches,
    describe_schedule_runs,
    describe_scheduled_search,
    format_interval,
    format_min_score,
    get_next_run,
    get_scheduled_searches,
    is_schedule_due,
    load_schedule,
    mark_schedule_run,
    request_immediate_run,
    save_extra_searches,
    save_min_score,
    save_notification_email,
    save_schedule_options,
    save_scheduled_search,
)
from storage.database import initialize_database
from storage.saved_searches import save_search
from storage.settings_repository import save_setting_values

NOW = datetime(2026, 10, 10, 12, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base vide."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)

    return rDatabaseFile


def build_schedule(**pValues):
    """Construit un état de planification active, modifiable par paramètre."""

    rSchedule = {
        "enabled": True,
        "interval_hours": 6,
        "search": {"sources": ["adzuna"], "criteria": {}},
        "last_run": None,
        "email": None,
    }

    rSchedule.update(pValues)

    return rSchedule


def test_load_schedule_returns_defaults(database_file):
    """Vérifie l'état d'une base où rien n'est planifié."""

    assert load_schedule(database_file) == {
        "enabled": False,
        "interval_hours": DEFAULT_INTERVAL_HOURS,
        "search": None,
        "extra_searches": [],
        "last_run": None,
        "email": None,
        "min_score": 0,
        "run_requested": None,
    }


def test_load_schedule_ignores_invalid_values(database_file):
    """Vérifie qu'une valeur illisible retombe sur son défaut."""

    save_setting_values(
        database_file,
        {
            "schedule_interval_hours": "2",
            "schedule_search": "{non json",
            "schedule_last_run": "hier",
        },
    )

    rSchedule = load_schedule(database_file)

    assert rSchedule["interval_hours"] == DEFAULT_INTERVAL_HOURS
    assert rSchedule["search"] is None
    assert rSchedule["last_run"] is None


def test_save_scheduled_search_keeps_filled_criteria(database_file):
    """Vérifie que seuls les critères renseignés sont enregistrés."""

    save_scheduled_search(
        database_file,
        ["adzuna", "remotive"],
        {"keyword": "Java", "location": None, "remote": True},
    )

    rSchedule = load_schedule(database_file)

    assert rSchedule["search"] == {
        "sources": ["adzuna", "remotive"],
        "criteria": {"keyword": "Java", "remote": True},
    }
    assert describe_scheduled_search(rSchedule) == (
        "Java · télétravail",
        "Adzuna, Remotive",
    )


def test_describe_scheduled_search_without_search():
    """Vérifie le résumé lorsqu'aucune recherche n'est enregistrée."""

    assert describe_scheduled_search(build_schedule(search=None)) == (
        "Aucune recherche enregistrée",
        "",
    )


@pytest.mark.parametrize(
    "pEnabled, pInterval, pWithSearch, pErrors",
    [
        (True, 2, True, ["Fréquence non proposée."]),
        (
            True,
            6,
            False,
            ["Enregistrez d'abord une recherche depuis la page Recherche."],
        ),
        (False, 12, False, []),
        (True, 24, True, []),
    ],
)
def test_save_schedule_options(
    database_file, pEnabled, pInterval, pWithSearch, pErrors
):
    """Vérifie la validation et l'enregistrement de l'activation et de la fréquence."""

    if pWithSearch:
        save_scheduled_search(database_file, ["adzuna"], {})

    assert save_schedule_options(database_file, pEnabled, pInterval) == pErrors

    rSchedule = load_schedule(database_file)

    if not pErrors:
        assert rSchedule["enabled"] is pEnabled
        assert rSchedule["interval_hours"] == pInterval
    else:
        assert rSchedule["enabled"] is False


@pytest.mark.parametrize(
    "pEmail, pErrors, pSaved",
    [
        (" moi@example.com ", [], "moi@example.com"),
        ("", [], None),
        ("pas-une-adresse", ["Adresse e-mail invalide."], None),
        ("moi@example.com\nBcc: x@y.z", ["Adresse e-mail invalide."], None),
    ],
)
def test_save_notification_email(database_file, pEmail, pErrors, pSaved):
    """Vérifie la validation de l'adresse, qui refuse aussi les sauts de ligne."""

    assert save_notification_email(database_file, pEmail) == pErrors
    assert load_schedule(database_file)["email"] == pSaved


def test_mark_schedule_run(database_file):
    """Vérifie l'enregistrement de l'heure de la dernière exécution."""

    mark_schedule_run(database_file, NOW)

    assert load_schedule(database_file)["last_run"] == NOW


@pytest.mark.parametrize(
    "pSchedule, pNextRun, pDue",
    [
        (build_schedule(enabled=False), None, False),
        (build_schedule(search=None), None, False),
        (build_schedule(), NOW, True),
        (
            build_schedule(last_run=datetime(2026, 10, 10, 8, 0)),
            datetime(2026, 10, 10, 14, 0),
            False,
        ),
        (build_schedule(last_run=datetime(2026, 10, 10, 6, 0)), NOW, True),
    ],
)
def test_next_run_and_due(pSchedule, pNextRun, pDue):
    """Vérifie l'échéance selon l'activation, la recherche et la dernière exécution."""

    assert get_next_run(pSchedule, NOW) == pNextRun
    assert is_schedule_due(pSchedule, NOW) is pDue


@pytest.mark.parametrize(
    "pHours, pLabel", [(1, "Toutes les heures"), (6, "Toutes les 6 heures")]
)
def test_format_interval(pHours, pLabel):
    """Vérifie le libellé des fréquences."""

    assert format_interval(pHours) == pLabel


@pytest.mark.parametrize(
    "pSchedule, pExpected",
    [
        (
            build_schedule(enabled=False),
            "Planification désactivée. Dernière exécution : jamais.",
        ),
        (
            build_schedule(),
            "Prochaine : dès la prochaine vérification du planificateur.",
        ),
        (
            build_schedule(last_run=datetime(2026, 10, 10, 8, 0)),
            "Dernière exécution : 10/10/2026 à 08:00. Prochaine : 10/10/2026 à 14:00.",
        ),
    ],
)
def test_describe_schedule_runs(pSchedule, pExpected):
    """Vérifie le résumé des exécutions passées et à venir."""

    assert pExpected in describe_schedule_runs(pSchedule, NOW)


def test_immediate_run_request(database_file):
    """Vérifie la demande immédiate : refusée sans recherche, puis traitée et effacée."""

    assert request_immediate_run(database_file, NOW) == [
        "Enregistrez d'abord une recherche depuis la page Recherche."
    ]

    save_scheduled_search(database_file, ["adzuna"], {})

    assert request_immediate_run(database_file, NOW) == []

    vSchedule = load_schedule(database_file)

    # La planification régulière est désactivée : seule la demande la déclenche.
    assert is_schedule_due(vSchedule, NOW)
    assert "Recherche demandée le 10/10/2026" in describe_schedule_runs(vSchedule, NOW)

    mark_schedule_run(database_file, NOW)

    assert load_schedule(database_file)["run_requested"] is None


def test_save_min_score(database_file):
    """Vérifie l'enregistrement du score minimal et le refus d'un score non proposé."""

    assert save_min_score(database_file, 70) == []
    assert load_schedule(database_file)["min_score"] == 70
    assert save_min_score(database_file, 42) == ["Score minimal non proposé."]
    assert load_schedule(database_file)["min_score"] == 70

    save_setting_values(database_file, {"notification_min_score": "abc"})

    assert load_schedule(database_file)["min_score"] == 0
    assert format_min_score(0) == "Toutes les nouvelles offres"
    assert format_min_score(70) == "Offres à 70 % de correspondance ou plus"


def test_extra_searches_follow_the_scheduled_one(database_file, caplog):
    """Vérifie l'ordre des recherches lancées et l'oubli d'un nom supprimé."""

    save_scheduled_search(database_file, ["remotive"], {"keyword": "Java"})
    save_search(database_file, "Python", ["jooble"], {"keyword": "Python"}, NOW)
    save_extra_searches(database_file, ["Python", "Supprimée", "Python"])

    vSchedule = load_schedule(database_file)
    vSearches = get_scheduled_searches(database_file, vSchedule)

    assert vSchedule["extra_searches"] == ["Python", "Supprimée"]
    assert [vSearch["name"] for vSearch in vSearches] == [
        "Recherche planifiée",
        "Python",
    ]
    assert vSearches[1]["criteria"] == {"keyword": "Python"}
    assert "introuvable, ignorée : Supprimée" in caplog.text
    assert describe_extra_searches(vSchedule) == (
        "Avec 2 recherche(s) enregistrée(s) : Python, Supprimée"
    )


@pytest.mark.parametrize("pValue", ["pas du json", '{"nom": "Python"}'])
def test_unreadable_extra_searches_are_ignored(database_file, pValue):
    """Vérifie qu'une liste illisible ne bloque pas la planification."""

    save_setting_values(database_file, {"schedule_extra_searches": pValue})

    assert load_schedule(database_file)["extra_searches"] == []
