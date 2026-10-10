"""Tests de la transformation des offres Adzuna"""

from job.csv_schema import JOB_COLUMNS
from job.sources.adzuna.parser import parse_job, parse_jobs


def build_job(**pValues):
    """Construit une offre Adzuna proche d'une réponse réelle."""

    rJob = {
        "id": "5920450613",
        "title": "Développeur Python / Django",
        "company": {"display_name": "Entreprise A"},
        "location": {
            "display_name": "Lille, Nord",
            "area": ["France", "Hauts-De-France", "Nord", "Lille"],
        },
        "redirect_url": "https://www.adzuna.fr/details/5920450613",
        "contract_type": "permanent",
        "contract_time": "full_time",
        "created": "2026-10-09T13:03:34Z",
        "category": {"label": "Emplois Informatique", "tag": "it-jobs"},
        "description": "Développement back-end...",
        "salary_min": 40000,
        "salary_max": 45000,
        "salary_is_predicted": "0",
    }

    rJob.update(pValues)

    return rJob


def test_parse_job():
    """Vérifie la transformation d'une offre Adzuna."""

    rJob = parse_job(build_job())

    assert rJob["source"] == "adzuna"
    assert rJob["source_id"] == "5920450613"
    assert rJob["company"] == "Entreprise A"
    assert rJob["url"] == "https://www.adzuna.fr/details/5920450613"
    assert rJob["city"] == "Lille"
    assert rJob["country"] == "France"
    assert rJob["contract"] == "CDI"
    assert rJob["employment_type"] == "full_time"
    assert rJob["salary_min"] == 40000
    assert rJob["salary_currency"] == "EUR"
    assert rJob["salary_period"] == "year"
    assert rJob["published_at"] == "2026-10-09T13:03:34Z"
    assert rJob["job_type"] == "Emplois Informatique"


def test_parse_job_ignores_predicted_salary():
    """Vérifie qu'un salaire estimé par Adzuna n'est pas conservé."""

    rJob = parse_job(build_job(salary_is_predicted="1"))

    assert rJob["salary_min"] is None
    assert rJob["salary_max"] is None
    assert rJob["salary_currency"] is None
    assert rJob["salary_period"] is None


def test_parse_job_without_city():
    """Vérifie qu'une localisation au niveau du département n'a pas de ville."""

    rJob = parse_job(
        build_job(location={"area": ["France", "Hauts-De-France", "Nord"]})
    )

    assert rJob["city"] is None
    assert rJob["country"] == "France"


def test_parse_jobs():
    """Vérifie la création d'un DataFrame au format commun."""

    rJobs = parse_jobs([build_job(), build_job(id="2")])

    assert list(rJobs.columns) == JOB_COLUMNS
    assert rJobs["source_id"].tolist() == ["5920450613", "2"]


def test_parse_job_leaves_ambiguous_contract_to_detection():
    """Vérifie qu'un contrat « contract », CDD ou freelance, n'est pas qualifié."""

    rJob = parse_job(build_job(contract_type="contract"))

    assert rJob["contract"] is None
    assert rJob["contract_type"] == "contract"


def test_parse_job_decodes_unicode_escapes():
    """Vérifie que les accents échappés par Adzuna sont restitués."""

    vJob = parse_job(
        {
            "title": "D\\u00e9veloppeur",
            "description": "Syst\\u00e8mes d\\u2019Information",
        }
    )

    assert vJob["title"] == "Développeur"
    assert vJob["description"] == "Systèmes d’Information"
