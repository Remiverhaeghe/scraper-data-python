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
    build_review_schedule,
    count_streak,
    describe_no_question,
    flag_question,
    get_next_review,
    load_active_quiz,
    load_quiz,
    pick_question,
)
from job.quiz_import import (
    build_generation_prompt,
    describe_quiz_import,
    import_questions,
    import_questions_file,
    split_levels,
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
    # Le graphique part du premier jour de révision, la veille.
    assert len(vStatistics["days"]) == 2
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
    """Vérifie la demande : thème, niveaux, modèle de pack et identifiants pris."""

    vPrompt = build_generation_prompt(load_quiz(), "JAVA", "confirmé", 20)

    assert "Thème : Java. 20 questions : 20 confirmé." in vPrompt
    assert "- questions/java.json" in vPrompt
    assert '"subdomain": "Développement"' in vPrompt
    assert '"level": "confirmé"' in vPrompt
    assert "java-list-of" in vPrompt

    vNew = build_generation_prompt({}, "Spring Boot", "tous", 30)

    assert "30 questions : 10 débutant, 10 intermédiaire, 7 confirmé, 3 expert." in vNew
    assert "Identifiants déjà pris : aucun" in vNew
    assert '"id": "spring-boot-001"' in vNew


def test_split_levels():
    """Vérifie la répartition par niveau, total conservé malgré les arrondis."""

    assert split_levels("tous", 10) == [
        ("débutant", 4),
        ("intermédiaire", 3),
        ("confirmé", 2),
        ("expert", 1),
    ]
    assert sum(vCount for _, vCount in split_levels("tous", 50)) == 50
    assert split_levels("expert", 20) == [("expert", 20)]


def test_review_schedule_moves_questions_between_boxes():
    """Vérifie Leitner : une bonne réponse monte d'une boîte, une erreur renvoie à 1."""

    vSchedule = build_review_schedule(
        [
            ("q-1", True, "2026-10-01T10:00:00"),
            ("q-1", True, "2026-10-02T10:00:00"),
            ("q-2", True, "2026-10-01T10:00:00"),
            ("q-2", False, "2026-10-05T10:00:00"),
        ]
        + [("q-3", True, f"2026-10-0{vDay}T10:00:00") for vDay in range(1, 8)]
    )

    assert vSchedule["q-1"] == {"box": 2, "due": date(2026, 10, 5)}
    assert vSchedule["q-2"] == {"box": 1, "due": date(2026, 10, 6)}
    assert vSchedule["q-3"]["box"] == 5
    assert vSchedule["q-3"]["due"] == date(2026, 10, 7) + timedelta(days=60)


def test_spaced_mode_offers_due_then_new_questions():
    """Vérifie le tirage : questions dues d'abord, puis nouvelles, puis rien."""

    vQuiz = {
        "t": {
            "key": "t",
            "label": "T",
            "questions": [
                {"id": vId, "choices": ["a", "b"], "answer": 0}
                for vId in ("due", "later", "new")
            ],
        }
    }
    vToday = date(2026, 10, 12)
    vSchedule = {
        "due": {"box": 1, "due": vToday},
        "later": {"box": 3, "due": vToday + timedelta(days=7)},
    }

    vFirst = pick_question(vQuiz, "t", "spaced", {}, pSchedule=vSchedule, pToday=vToday)

    assert vFirst["id"] == "due"

    vSchedule["due"]["due"] = vToday + timedelta(days=1)
    vSecond = pick_question(
        vQuiz, "t", "spaced", {}, pSchedule=vSchedule, pToday=vToday
    )

    assert vSecond["id"] == "new"

    vSchedule["new"] = {"box": 1, "due": vToday + timedelta(days=1)}

    assert (
        pick_question(vQuiz, "t", "spaced", {}, pSchedule=vSchedule, pToday=vToday)
        is None
    )
    assert get_next_review(vQuiz, "t", vSchedule) == vToday + timedelta(days=1)


@pytest.mark.parametrize(
    "pMode, pNext, pText",
    [
        ("review", None, "Aucune question ratée"),
        ("spaced", date(2026, 10, 13), "prochaine révision le 13/10/2026"),
        ("spaced", None, "Aucune question dans ce thème"),
    ],
)
def test_describe_no_question(pMode, pNext, pText):
    """Vérifie le message affiché quand aucune question n'est proposée."""

    assert pText in describe_no_question(pMode, pNext)


def test_overview_counts_questions_due_today(database_file):
    """Vérifie le nombre de questions à revoir aujourd'hui par thème."""

    vQuiz = load_quiz()
    answer_question(database_file, vQuiz, "java-optional", 1, NOW)

    vJava = next(
        vTheme
        for vTheme in build_quiz_overview(
            database_file, vQuiz, NOW.date() + timedelta(days=1)
        )
        if vTheme["key"] == "java"
    )

    assert vJava["due"] == 1
