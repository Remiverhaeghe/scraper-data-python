"""Tests du profil du candidat et de la préparation des candidatures"""

import pytest

from job.preparation import (
    match_offer,
    score_offers,
    describe_score,
    describe_missing,
    classify_requirements,
    filter_by_match,
    build_questions,
    get_offer_skills,
    match_profile,
    prepare_application,
    recommend_cv,
)
from job.profile import (
    MAX_TEXT_LENGTH,
    add_profile_skill,
    build_profile,
    is_profile_empty,
    load_profile,
    profile_to_texts,
    save_profile,
    suggest_keywords,
)
from storage.database import initialize_database

EXPERIENCES = (
    "Développeur backend | Java, Spring, SQL | Réduit de 40 % le temps de réponse\n"
    "\n"
    "Tech lead | Docker, Java | Mis en place l'intégration continue"
)


@pytest.fixture
def profile():
    """Construit un profil complet à partir des textes saisis."""

    rProfile = build_profile(
        "Rémi V.",
        "Développeur Java depuis 5 ans.",
        "Java, Spring, SQL, Docker, java",
        EXPERIENCES,
        "CV Java backend | Java, Spring, SQL\nCV Data | Python, SQL",
    )

    return rProfile


def test_build_profile_parses_lines(profile):
    """Vérifie le découpage des listes et des lignes, doublons et lignes vides exclus."""

    assert profile["skills"] == ["Java", "Spring", "SQL", "Docker"]
    assert profile["experiences"][1] == {
        "title": "Tech lead",
        "skills": ["Docker", "Java"],
        "achievement": "Mis en place l'intégration continue",
    }
    assert len(profile["experiences"]) == 2
    assert profile["cv_variants"][1]["skills"] == ["Python", "SQL"]


def test_profile_round_trip(tmp_path, profile):
    """Vérifie l'enregistrement puis la relecture du profil et de ses textes."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    assert is_profile_empty(load_profile(vDatabaseFile))

    save_profile(vDatabaseFile, profile)
    vTexts = profile_to_texts(load_profile(vDatabaseFile))

    assert vTexts["experiences"].splitlines()[0] == (
        "Développeur backend | Java, Spring, SQL | Réduit de 40 % le temps de réponse"
    )
    # Le formulaire ne porte pas l'auto-évaluation, gardée à part.
    assert {
        **build_profile(
            vTexts["name"],
            vTexts["headline"],
            vTexts["skills"],
            vTexts["experiences"],
            vTexts["cv_variants"],
        ),
        "skill_levels": {},
    } == load_profile(vDatabaseFile)


def test_build_profile_rejects_huge_text():
    """Vérifie le refus d'un champ démesuré."""

    with pytest.raises(ValueError):
        build_profile("", "", "x" * (MAX_TEXT_LENGTH + 1), "", "")


def test_match_and_recommendation(profile):
    """Vérifie les compétences couvertes, manquantes, le score et le CV conseillé."""

    vOfferSkills = get_offer_skills(
        {"skills": '["Kafka"]', "description": "Java, Spring Boot et Docker"}
    )

    vMatch = match_profile(profile, vOfferSkills)

    assert vOfferSkills == ["Kafka", "Java", "Spring", "Docker"]
    assert {vKey: vValue for vKey, vValue in vMatch.items() if vKey != "details"} == {
        "covered": ["Java", "Spring", "Docker"],
        "missing": ["Kafka"],
        "required": [],
        "score": 75,
    }
    assert vMatch["details"][0] == {"skill": "Kafka", "weight": 1.0, "coverage": 0.0}
    assert recommend_cv(profile, vOfferSkills) == {
        "name": "CV Java backend",
        "matching": 2,
    }
    assert match_profile(profile, [])["score"] is None


@pytest.mark.parametrize(
    "pOffer, pExpected",
    [
        ({}, ["rémunération", "télétravail", "type de contrat"]),
        ({"contract": "CDD", "remote": True, "salary_label": "45k"}, ["CDI"]),
        ({"contract": "CDI", "remote": False, "salary_net_monthly_min": 3000}, []),
    ],
)
def test_build_questions(pOffer, pExpected):
    """Vérifie les questions ajoutées selon ce que l'offre ne précise pas."""

    vSpecific = build_questions(pOffer)[: len(pExpected)]

    assert all(vWord in vQuestion for vWord, vQuestion in zip(pExpected, vSpecific))
    assert len(build_questions(pOffer)) == len(pExpected) + 3


def test_prepare_application(profile):
    """Vérifie l'entretien et la lettre préparés pour une offre."""

    vPreparation = prepare_application(
        profile,
        {
            "title": "Développeur Java H/F",
            "company": "Acme",
            "contract": "CDI",
            "description": "Java, Kafka",
        },
    )
    vLetter = vPreparation["letter"]

    assert vPreparation["interview"]["strengths"][0] == {
        "skill": "Java",
        "examples": [
            "Développeur backend : Réduit de 40 % le temps de réponse",
            "Tech lead : Mis en place l'intégration continue",
        ],
    }
    assert vPreparation["interview"]["gaps"][0].startswith("Kafka :")
    assert "« Développeur Java » chez Acme" in vLetter
    assert "En tant que développeur backend, j'ai par exemple réduit" in vLetter
    assert vLetter.endswith("Rémi V.")


def test_prepare_application_answers_recruiter_questions(profile):
    """Vérifie les pistes de réponse tirées du profil et de l'offre."""

    vAnswers = {
        vAnswer["question"]: vAnswer["hint"]
        for vAnswer in prepare_application(
            profile,
            {
                "title": "Développeur Java",
                "company": "Acme",
                "description": "Java, Kafka",
                "salary_label": "45 000 € par an",
            },
        )["interview"]["answers"]
    }

    assert vAnswers["Présentez-vous."].startswith("Développeur Java depuis 5 ans.")
    assert "Développeur backend, Tech lead" in vAnswers["Présentez-vous."]
    assert "Acme" in vAnswers["Pourquoi Acme ?"]
    assert "réduit de 40 %" in vAnswers["Parlez-moi d'une réussite."]
    assert vAnswers["Quel est votre point faible ?"].startswith("Kafka :")
    assert "45 000 € par an" in vAnswers["Quelles sont vos prétentions salariales ?"]


def test_recruiter_answers_without_profile_details():
    """Vérifie les pistes génériques quand le profil et l'offre sont peu remplis."""

    vProfile = build_profile("", "", "Java", "", "")

    vAnswers = [
        vAnswer["hint"]
        for vAnswer in prepare_application(vProfile, {"description": "Java"})[
            "interview"
        ]["answers"]
    ]

    assert vAnswers[0].startswith("Votre métier et votre niveau en une phrase")
    assert "ajoutez une réalisation" in vAnswers[2]
    assert vAnswers[3].startswith("Un vrai point d'amélioration")
    assert "ne donne pas de salaire" in vAnswers[4]


def test_filter_by_match_keeps_close_offers():
    """Vérifie le filtre de correspondance, ignoré sans score calculé."""

    vOffers = [
        {"title": "A", "match_score": 80},
        {"title": "B", "match_score": 40},
        {"title": "C", "match_score": None},
    ]

    assert [vOffer["title"] for vOffer in filter_by_match(vOffers, 50)] == ["A"]
    assert filter_by_match(vOffers, 0) == vOffers
    assert filter_by_match([{"match_score": None}], 70) == [{"match_score": None}]


def test_add_profile_skill(tmp_path):
    """Vérifie l'ajout d'une compétence, sans doublon de casse ni valeur vide."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)

    assert add_profile_skill(vDatabaseFile, " Python ")
    assert not add_profile_skill(vDatabaseFile, "python")
    assert not add_profile_skill(vDatabaseFile, "  ")
    assert add_profile_skill(vDatabaseFile, "Docker")
    assert load_profile(vDatabaseFile)["skills"] == ["Python", "Docker"]


def test_suggest_keywords(profile):
    """Vérifie l'ordre des suggestions, sans doublon ni intitulé trop long."""

    profile["experiences"].append({"title": "Responsable " + "x" * 40})

    assert suggest_keywords(profile) == [
        "Développeur backend",
        "Tech lead",
        "Java",
        "Spring",
        "SQL",
        "Docker",
    ]
    assert suggest_keywords(profile, 2) == ["Développeur backend", "Tech lead"]


def test_match_profile_recognizes_free_skill_wording():
    """Vérifie qu'une compétence saisie librement couvre son libellé reconnu."""

    vMatch = match_profile(
        {"skills": ["TIA Portal", "habilitation B2V"]},
        ["Siemens TIA Portal", "Habilitation électrique", "GMAO"],
    )

    assert vMatch["covered"] == ["Siemens TIA Portal", "Habilitation électrique"]
    assert vMatch["score"] == 67


def test_requirements_weigh_required_and_preferred_skills():
    """Vérifie le poids d'une compétence selon la phrase qui la cite."""

    vText = (
        "Maîtrise de Java exigée. Spring est un plus ; Docker idéalement. "
        "Vous utiliserez SQL au quotidien."
    )

    assert classify_requirements(vText, ["Java", "Spring", "Docker", "SQL"]) == {
        "Java": 2.0,
        "Spring": 0.5,
        "Docker": 0.5,
        "SQL": 1.0,
    }


def test_score_weighs_requirements_levels_and_a_minimum_of_skills():
    """Vérifie le score : compétence exigée manquante, niveau noté et plancher."""

    vText = "Java exigé. SQL. Docker est un plus."
    vSkills = ["Java", "SQL", "Docker"]
    vProfile = {"skills": ["SQL", "Docker"], "skill_levels": {}}

    # Java exigé manque : (1 + 0,5) / 3,5
    vMatch = match_profile(vProfile, vSkills, vText)

    assert vMatch["score"] == 43
    assert vMatch["required"] == ["Java"]
    assert vMatch["missing"] == ["Java"]

    # Java noté 6 : trois quarts de son poids, affiché comme couvert
    vMatch = match_profile({**vProfile, "skill_levels": {"Java": 6}}, vSkills, vText)

    assert vMatch["score"] == 86
    assert vMatch["covered"] == vSkills

    # Noté 4, sous le seuil de 5 : à renforcer, il ne compte pas
    vWeak = {**vProfile, "skills": vSkills, "skill_levels": {"Java": 4}}

    assert match_profile(vWeak, vSkills, vText)["missing"] == ["Java"]

    # Une seule compétence, couverte : rapportée au plancher de trois
    assert match_profile({"skills": ["Java"]}, ["Java"])["score"] == 33


def test_describe_missing_flags_required_skills():
    """Vérifie que les compétences exigées manquantes sont signalées."""

    assert describe_missing({"missing": ["Java", "Git"], "required": ["Java"]}) == (
        "Java (exigée), Git"
    )
    assert describe_missing({"missing": [], "required": []}) == "aucune"


def test_describe_score_explains_weights_and_mastery():
    """Vérifie l'explication : exigées d'abord, maîtrise, plancher signalé."""

    vMatch = match_profile(
        {"skills": ["SQL"], "skill_levels": {"Java": 6}},
        ["Java", "SQL", "Docker"],
        "Java exigé. SQL. Docker est un plus.",
    )

    assert describe_score(vMatch) == [
        "Java · exigée · partielle (75 %)",
        "SQL · demandée · maîtrisée",
        "Docker · appréciée · manquante",
    ]
    assert describe_score(match_profile({"skills": ["Go"]}, ["Go"]))[-1].startswith(
        "Peu de compétences citées"
    )
    assert describe_score({"missing": []}) == []


def test_offer_is_scored_on_the_best_target_profile():
    """Vérifie le double profil : chaque offre notée sur le CV qui lui correspond."""

    vProfile = {
        **build_profile("", "", "", "", ""),
        "cv_variants": [
            {"name": "Développement", "skills": ["Java", "SQL"]},
            {"name": "Maintenance", "skills": ["GMAO", "Électrotechnique"]},
        ],
    }
    vOffers = [
        {"title": "Développeur", "skills": '["Java", "SQL"]'},
        {"title": "Technicien", "skills": '["GMAO", "Électrotechnique"]'},
    ]

    score_offers(vOffers, vProfile)

    assert [(vOffer["match_score"], vOffer["match_target"]) for vOffer in vOffers] == [
        # Deux compétences seulement : rapportées au plancher de trois
        (67, "Développement"),
        (67, "Maintenance"),
    ]
    assert (
        match_offer(build_profile("", "", "Java", "", ""), vOffers[0])["target"] is None
    )


def test_match_is_kept_until_the_profile_changes():
    """Vérifie la comparaison gardée, refaite quand le profil change."""

    vOffer = {"title": "Dev", "skills": ["Java", "SQL"], "detected_skills": "[]"}
    vFirst = match_offer({"skills": ["Java"]}, vOffer)

    assert match_offer({"skills": ["Java"]}, vOffer) == vFirst
    assert match_offer({"skills": ["Java", "SQL"]}, vOffer)["score"] > vFirst["score"]
