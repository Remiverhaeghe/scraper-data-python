# ============================================================================
# Tests du filtrage des offres d'emploi
# ============================================================================


import pandas as pd

from job.config import JobScrapingConfig
from job.filter import filter_jobs


def create_job(**pValues):
    """
    Crée une offre de test sous forme de dictionnaire.
    """

    vValues = {
        "title": "Développeur Python",
        "company": "Entreprise A",
        "location": "Lille",
        "city": "Lille",
        "postal_code": "59000",
        "distance_km": 10,
        "contract": "CDI",
        "salary_min": 40000,
        "salary_max": 50000,
        "salary_period": "year",
        "remote": True,
        "remote_days": 2,
        "remote_type": "hybrid",
        "nearest_metro": "République",
        "metro_distance_km": 0.5,
        "date": "31/08/2026",
        "url": "https://example.com/job",
        "description": "Développement d'applications",
        "missions": "Développer des applications Python",
        "requirements": "Expérience Python",
        "education": "Bac+3",
        "skills": "Python, Django, Git"
    }

    vValues.update(pValues)

    rJob = vValues

    return rJob


def create_jobs(*pJobs):
    """
    Crée un DataFrame à partir des offres de test.
    """

    rJobs = pd.DataFrame(
        list(pJobs)
    )

    return rJobs


def test_filter_jobs_without_filter():
    """
    Vérifie que toutes les offres sont conservées sans critère.
    """

    vJobs = create_jobs(
        create_job(),
        create_job(
            title="Développeur Java",
            url="https://example.com/job-2"
        )
    )

    rJobs = filter_jobs(
        vJobs,
        JobScrapingConfig()
    )

    pd.testing.assert_frame_equal(
        rJobs,
        vJobs
    )


def test_filter_jobs_by_keyword():
    """
    Vérifie le filtrage par mot-clé.
    """

    vJobs = create_jobs(
        create_job(),
        create_job(
            title="Développeur Java",
            description="Développement d'applications Java",
            missions="Développer des applications Java",
            requirements="Expérience Java",
            skills="Java, Spring",
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        keyword="python"
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["title"] == "Développeur Python"


def test_filter_jobs_by_location_and_distance():
    """
    Vérifie le filtrage par localisation et distance.
    """

    vJobs = create_jobs(
        create_job(
            distance_km=10
        ),
        create_job(
            location="Arras",
            city="Arras",
            distance_km=45,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        location="Lille",
        max_distance_km=40
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["location"] == "Lille"


def test_filter_jobs_by_contract():
    """
    Vérifie le filtrage par type de contrat.
    """

    vJobs = create_jobs(
        create_job(),
        create_job(
            contract="CDD",
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        contract="CDI"
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["contract"] == "CDI"


def test_filter_jobs_by_salary():
    """
    Vérifie le filtrage par salaire.
    """

    vJobs = create_jobs(
        create_job(
            salary_min=40000,
            salary_max=50000
        ),
        create_job(
            salary_min=30000,
            salary_max=35000,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        min_salary=40000
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["salary_min"] == 40000


def test_filter_jobs_by_remote():
    """
    Vérifie le filtrage sur le télétravail.
    """

    vJobs = create_jobs(
        create_job(
            remote=True
        ),
        create_job(
            remote=False,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        remote=True
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["remote"] == True


def test_filter_jobs_by_remote_days():
    """
    Vérifie le nombre minimum de jours de télétravail.
    """

    vJobs = create_jobs(
        create_job(
            remote_days=3
        ),
        create_job(
            remote_days=1,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        min_remote_days=2
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["remote_days"] == 3


def test_filter_jobs_by_metro():
    """
    Vérifie l'accessibilité en métro.
    """

    vJobs = create_jobs(
        create_job(
            nearest_metro="République"
        ),
        create_job(
            nearest_metro=None,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        metro_required=True
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["nearest_metro"] == "République"


def test_filter_jobs_by_metro_distance():
    """
    Vérifie la distance maximale jusqu'au métro.
    """

    vJobs = create_jobs(
        create_job(
            metro_distance_km=0.5
        ),
        create_job(
            metro_distance_km=2,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        max_metro_distance_km=1
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["metro_distance_km"] == 0.5


def test_filter_jobs_by_education():
    """
    Vérifie le filtrage par formation.
    """

    vJobs = create_jobs(
        create_job(
            education="Bac+5"
        ),
        create_job(
            education="Bac+2",
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        education="Bac+5"
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["education"] == "Bac+5"


def test_filter_jobs_by_skills():
    """
    Vérifie le filtrage par compétences.
    """

    vJobs = create_jobs(
        create_job(
            skills="Python, Django, Git"
        ),
        create_job(
            skills="Java, Spring",
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        skills=[
            "Python",
            "Git"
        ]
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["skills"] == "Python, Django, Git"


def test_filter_jobs_by_missions():
    """
    Vérifie le filtrage par missions.
    """

    vJobs = create_jobs(
        create_job(
            missions="Développer des applications Python"
        ),
        create_job(
            missions="Administrer les serveurs",
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        missions=[
            "Python"
        ]
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert "Python" in rJobs.iloc[0]["missions"]


def test_filter_jobs_with_multiple_criteria():
    """
    Vérifie que plusieurs critères sont appliqués simultanément.
    """

    vJobs = create_jobs(
        create_job(
            distance_km=20,
            salary_min=42000,
            salary_max=50000,
            remote_days=3,
            metro_distance_km=0.8
        ),
        create_job(
            distance_km=20,
            salary_min=42000,
            salary_max=50000,
            remote_days=1,
            metro_distance_km=0.8,
            url="https://example.com/job-2"
        ),
        create_job(
            distance_km=50,
            salary_min=45000,
            salary_max=55000,
            remote_days=3,
            metro_distance_km=0.5,
            url="https://example.com/job-3"
        )
    )

    vConfig = JobScrapingConfig(
        keyword="Python",
        location="Lille",
        max_distance_km=40,
        contract="CDI",
        min_salary=40000,
        min_remote_days=2,
        metro_required=True,
        max_metro_distance_km=1
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["url"] == "https://example.com/job"


def test_filter_jobs_rejects_missing_required_data():
    """
    Vérifie qu'une offre sans donnée nécessaire est rejetée
    lorsqu'un filtre correspondant est demandé.
    """

    vJobs = create_jobs(
        create_job(
            distance_km=None
        ),
        create_job(
            distance_km=20,
            url="https://example.com/job-2"
        )
    )

    vConfig = JobScrapingConfig(
        max_distance_km=40
    )

    rJobs = filter_jobs(
        vJobs,
        vConfig
    )

    assert len(rJobs) == 1
    assert rJobs.iloc[0]["url"] == "https://example.com/job-2"