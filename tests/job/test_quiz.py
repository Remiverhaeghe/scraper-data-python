"""Tests de la révision technique et du contenu des questions"""

import io
import json
import zipfile
import random
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from job.quiz import (
    answer_question,
    build_quiz_overview,
    build_quiz_statistics,
    count_streak,
    flag_question,
    load_active_quiz,
    load_quiz,
    pick_question,
)
from job.quiz_import import (
    build_generation_prompt,
    describe_quiz_import,
    import_questions,
    import_questions_file,
)
from storage.database import initialize_database
from storage.job_offers import save_offers
from storage.quiz_answers import get_last_answers
from storage.settings_repository import save_setting_values

NOW = datetime(2026, 10, 11, 10, 0)


@pytest.fixture
def database_file(tmp_path):
    """Crée une base avec deux offres citant Java."""

    rDatabaseFile = tmp_path / "scraper.db"

    initialize_database(rDatabaseFile)
    save_offers(
        rDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": vId,
                    "title": "Dev",
                    "skills": vSkills,
                }
                for vId, vSkills in (("1", ["Java", "SQL"]), ("2", ["Java"]))
            ]
        ),
        NOW,
    )

    return rDatabaseFile


def test_versioned_questions_are_valid():
    """Vérifie que chaque fichier de questions du dépôt se charge sans défaut."""

    vQuiz = load_quiz()

    assert {
        "java",
        "python",
        "sql",
        "javascript",
        "git",
        "practices",
        "docker",
        "spring",
    } <= set(vQuiz)
    assert all(len(vTheme["questions"]) >= 8 for vTheme in vQuiz.values())


def test_invalid_question_is_reported(tmp_path):
    """Vérifie le message d'une question dont la réponse n'existe pas."""

    (tmp_path / "theme.json").write_text(
        json.dumps(
            {
                "theme": "Test",
                "questions": [
                    {
                        "id": "q-1",
                        "level": "débutant",
                        "question": "?",
                        "choices": ["a", "b"],
                        "answer": 2,
                        "explanation": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="theme.json, question q-1 : réponse hors"):
        load_quiz(tmp_path)


def test_overview_suggests_themes_from_offers(database_file):
    """Vérifie l'ordre des thèmes selon les offres et le score après une réponse."""

    vQuiz = load_quiz()

    answer_question(database_file, vQuiz, "java-optional", 1, NOW)
    answer_question(database_file, vQuiz, "java-list-of", 0, NOW)

    vOverview = build_quiz_overview(database_file, vQuiz)

    assert [vTheme["label"] for vTheme in vOverview[:2]] == ["Java", "SQL"]
    assert vOverview[0]["offer_count"] == 2
    assert (vOverview[0]["answered"], vOverview[0]["to_review"]) == (2, 1)
    assert vOverview[0]["score"] == round(100 / len(vQuiz["java"]["questions"]))


def test_pick_question_modes_and_shuffle(database_file):
    """Vérifie les questions proposées selon le mode et le mélange des choix."""

    vQuiz = load_quiz()

    answer_question(database_file, vQuiz, "git-stash", 0, NOW)
    vAnswers = get_last_answers(database_file)

    vReview = pick_question(vQuiz, "git", "review", vAnswers, random.Random(1))

    assert vReview["id"] == "git-stash"
    assert sorted(vReview["shuffled"]) == list(enumerate(vReview["choices"]))

    for vSeed in range(10):
        vQuestion = pick_question(
            vQuiz, "git", "discover", vAnswers, random.Random(vSeed)
        )

        assert vQuestion["id"] != "git-stash"

    assert pick_question(vQuiz, "sql", "review", vAnswers) is None


def test_answer_question_rejects_unknown(database_file):
    """Vérifie le refus d'une question inconnue ou d'un choix hors liste."""

    vQuiz = load_quiz()

    vResult = answer_question(database_file, vQuiz, "sql-null", 1, NOW)

    assert vResult["correct"] is True
    assert vResult["answer"] == "Aucune ligne"

    for vQuestionId, vChoice in (("inconnue", 0), ("sql-null", 9)):
        with pytest.raises(ValueError):
            answer_question(database_file, vQuiz, vQuestionId, vChoice, NOW)


def test_quiz_statistics_count_answers_rate_and_streak(database_file):
    """Vérifie les chiffres globaux, la série de jours et le graphique."""

    vQuiz = load_quiz()

    answer_question(database_file, vQuiz, "java-optional", 1, NOW - timedelta(days=1))
    answer_question(database_file, vQuiz, "java-list-of", 1, NOW)
    answer_question(database_file, vQuiz, "java-list-of", 0, NOW)

    vStatistics = build_quiz_statistics(
        database_file, build_quiz_overview(database_file, vQuiz), NOW
    )

    assert vStatistics["acquired"] == 1
    assert vStatistics["to_review"] == 1
    assert vStatistics["answers"] == 3
    assert vStatistics["rate"] == 67
    assert vStatistics["streak"] == 2
    assert len(vStatistics["days"]) == 14
    assert vStatistics["days"][-1] == (NOW.date(), 2, 1)


def test_quiz_statistics_without_answers(database_file):
    """Vérifie l'état sans aucune réponse."""

    vStatistics = build_quiz_statistics(database_file, [], NOW)

    assert (vStatistics["answers"], vStatistics["rate"], vStatistics["streak"]) == (
        0,
        None,
        0,
    )


def test_count_streak_keeps_an_unfinished_day():
    """Vérifie qu'une série reste en cours tant que la journée n'est pas finie."""

    vToday = date(2026, 10, 12)
    vDays = {"2026-10-11": (1, 1), "2026-10-10": (2, 0), "2026-10-08": (1, 1)}

    assert count_streak(vDays, vToday) == 2
    assert count_streak({}, vToday) == 0


def build_question(pId, **pValues):
    """Construit une question valide au format des fichiers livrés."""

    rQuestion = {
        "id": pId,
        "level": "débutant",
        "question": f"Que fait {pId} ?",
        "choices": ["a", "b", "c", "d"],
        "answer": 1,
        "explanation": "Parce que.",
    }
    rQuestion.update(pValues)

    return rQuestion


def test_import_questions_checks_each_question(database_file):
    """Vérifie l'import d'une réponse ChatGPT : valides gardées, autres listées."""

    vText = (
        "Voici :\n```json\n"
        + json.dumps(
            {
                "questions": [
                    build_question("kafka-topic"),
                    build_question("kafka-offset", extra="ignoré"),
                    build_question("kafka-bad", answer=7),
                    build_question("java-list-of"),
                    build_question("kafka-copie", question="Que fait kafka-topic ?"),
                    "pas une question",
                ]
            }
        )
        + "\n```"
    )

    vReport = import_questions(database_file, "Kafka", vText, NOW)
    vQuiz = load_active_quiz(database_file)

    assert vReport["added"] == 2
    assert vReport["themes"] == ["Kafka"]
    assert len(vReport["rejected"]) == 4
    assert "identifiant déjà utilisé" in " ".join(vReport["rejected"])
    assert "déjà présente" in " ".join(vReport["rejected"])
    assert [vQuestion["id"] for vQuestion in vQuiz["kafka"]["questions"]] == [
        "kafka-topic",
        "kafka-offset",
    ]
    assert "extra" not in vQuiz["kafka"]["questions"][1]
    assert "2 question(s) ajoutée(s) : Kafka. 4 écartée(s)" in describe_quiz_import(
        vReport
    )


def test_import_questions_uses_json_theme_and_existing_label(database_file):
    """Vérifie que le thème du JSON l'emporte et rejoint un thème existant."""

    vReport = import_questions(
        database_file,
        "",
        json.dumps({"theme": "java", "questions": [build_question("java-new-one")]}),
        NOW,
    )

    assert vReport["themes"] == ["Java"]
    assert "java-new-one" in [
        vQuestion["id"]
        for vQuestion in load_active_quiz(database_file)["java"]["questions"]
    ]


@pytest.mark.parametrize(
    "pTheme, pText, pMessage",
    [
        ("", json.dumps([build_question("x-one")]), "Indiquez le thème"),
        ("Kafka", "rien d'utile", "Aucune question"),
        ("Kafka", '{"questions": [1,}', "JSON illisible"),
        ("Kafka", "[]", "Aucune question"),
        (
            "Kafka",
            json.dumps([build_question(f"k-{vIndex}") for vIndex in range(201)]),
            "200 questions",
        ),
    ],
)
def test_import_questions_refuses_unreadable_text(
    database_file, pTheme, pText, pMessage
):
    """Vérifie les refus d'un import sans thème, sans JSON ou trop gros."""

    with pytest.raises(ValueError, match=pMessage):
        import_questions(database_file, pTheme, pText, NOW)


def build_zip(pFiles):
    """Construit une archive .zip en mémoire."""

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        for vName, vContent in pFiles.items():
            vArchive.writestr(vName, vContent)

    rContent = vBuffer.getvalue()

    return rContent


def test_import_questions_file_reads_zip_of_json(database_file):
    """Vérifie l'import d'une archive : un thème par fichier, erreurs par fichier."""

    vContent = build_zip(
        {
            "quiz/docker.json": json.dumps(
                {"theme": "Docker", "questions": [build_question("docker-new")]}
            ),
            "angular.json": json.dumps([build_question("angular-signal")]),
            "lisez-moi.txt": "ignoré",
            "casse.json": '{"questions": [}',
        }
    )

    vReport = import_questions_file(database_file, "", "questions.zip", vContent, NOW)

    assert vReport["added"] == 2
    assert vReport["themes"] == ["Docker", "angular"]
    assert vReport["rejected"][0].startswith("casse.json : JSON illisible")


@pytest.mark.parametrize(
    "pFileName, pContent, pMessage",
    [
        ("questions.pdf", b"x", "formats acceptés"),
        ("questions.zip", b"pas une archive", "illisible"),
        ("questions.zip", build_zip({"a.txt": "x"}), "aucun fichier .json"),
        (
            "questions.zip",
            build_zip({f"{vIndex}.json": "[]" for vIndex in range(301)}),
            "trop volumineuse",
        ),
    ],
    ids=["format", "zip-abime", "sans-json", "trop-de-fichiers"],
)
def test_import_questions_file_refuses_invalid_files(
    database_file, pFileName, pContent, pMessage
):
    """Vérifie le refus d'un format inconnu ou d'une archive inutilisable."""

    with pytest.raises(ValueError, match=pMessage):
        import_questions_file(database_file, "Kafka", pFileName, pContent, NOW)


def test_import_questions_file_reads_json_file(database_file):
    """Vérifie l'import d'un simple fichier JSON avec le thème saisi."""

    vReport = import_questions_file(
        database_file,
        "spring",
        "kafka.json",
        json.dumps([build_question("spring-boot-actuator")]).encode(),
        NOW,
    )

    assert vReport["themes"] == ["Spring"]


def test_flagged_question_leaves_the_quiz(database_file):
    """Vérifie qu'une question signalée n'est plus proposée."""

    flag_question(database_file, "java-optional")
    flag_question(database_file, "java-optional")

    vQuiz = load_active_quiz(database_file)

    assert "java-optional" not in [
        vQuestion["id"] for vQuestion in vQuiz["java"]["questions"]
    ]
    assert len(load_quiz()["java"]["questions"]) == len(vQuiz["java"]["questions"]) + 1


def test_flagged_list_unreadable_is_ignored(database_file, caplog):
    """Vérifie qu'une liste de signalements illisible ne bloque pas la révision."""

    save_setting_values(database_file, {"quiz_flagged": "{"})

    assert load_active_quiz(database_file)["java"]["questions"]
    assert "illisible" in caplog.text


def test_build_generation_prompt_lists_taken_ids():
    """Vérifie la demande : thème, niveau, format JSON et identifiants déjà pris."""

    vPrompt = build_generation_prompt(load_quiz(), "JAVA", "confirmé", 20)

    assert vPrompt.startswith("Écris 20 questions à choix multiple sur « Java »")
    assert '"level": "confirmé"' in vPrompt
    assert "java-list-of" in vPrompt
    assert (
        build_generation_prompt({}, "Spring Boot", "inconnu", 10).count("spring-boot-")
        == 2
    )
