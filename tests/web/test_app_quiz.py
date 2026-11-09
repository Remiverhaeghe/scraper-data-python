"""Tests web des quiz, examens et compétences"""

from datetime import datetime
import io
import json
import re
import zipfile

import pandas as pd

from job.quiz_generation import MIN_QUALITY_SAMPLE
from job.quiz_import import import_questions, import_questions_file
from storage.job_offers import save_offers
from tests.job.test_quiz_generation import build_lot_text, build_question
from tests.job.test_quiz_import import build_pack
from tests.job.test_quiz_types import NUMERIC, ORDER, PAIRS
from tools.quiz_lot import build_pack as build_lot_pack
from web.app import app, get_database_file
import job.quiz_packs as quiz_packs


def test_quiz_question_answer_and_review(client):
    """Vérifie une question, sa correction et la question ratée proposée à revoir."""

    vOverview = client.get("/quiz").text

    assert "Révision" in vOverview
    assert "?theme=sql&mode=spaced" in vOverview

    vQuestion = client.get("/quiz?theme=sql&mode=discover").text
    vQuestionId = re.search(r'name="question_id" value="([^"]+)"', vQuestion).group(1)

    assert vQuestion.count('name="choice"') >= 2

    vAnswer = client.post(
        "/quiz/answer",
        data={"question_id": "sql-null", "choice": "0", "mode": "discover"},
    ).text

    assert "Réponse incorrecte" in vAnswer
    assert "Réponse : Aucune ligne" in vAnswer
    assert "1 ratée(s)" in vAnswer
    assert vQuestionId.startswith("sql-")

    vReview = client.get("/quiz?theme=sql&mode=review").text

    assert 'name="question_id" value="sql-null"' in vReview

    vRefused = client.post(
        "/quiz/answer",
        data={"question_id": "inconnue", "choice": "0", "mode": "discover"},
    )

    assert vRefused.status_code == 400


def test_code_review_question_on_the_web(client):
    """Vérifie une revue de code : cases à cocher, réponse juste, case oubliée."""

    vRight = client.post(
        "/quiz/answer",
        data={
            "question_id": "ent-java-revue-equals",
            "indexes": ["1", "0"],
            "mode": "discover",
        },
    ).text
    vEmpty = client.post(
        "/quiz/answer",
        data={"question_id": "ent-java-revue-equals", "mode": "discover"},
    )

    assert "Bonne réponse" in vRight
    assert vEmpty.status_code == 400
    assert "Cochez au moins un constat." in vEmpty.text
    assert 'type="checkbox" name="indexes"' in vEmpty.text


def test_self_assessment_on_the_web(client):
    """Vérifie la grille d'auto-évaluation et les thèmes à renforcer en Révision."""

    assert "Auto-évaluation des compétences" in client.get("/profile").text

    vSaved = client.post(
        "/profile/levels",
        data={
            "skill": ["Java", "Android"],
            "level": ["8", "2"],
            "new_skill": "Kafka",
            "new_level": "4",
        },
        follow_redirects=False,
    )
    vQuiz = client.get("/quiz").text

    assert vSaved.status_code == 303
    assert 'name="skill" value="Kafka"' in client.get("/profile").text
    assert "Entretien Android · Android 2/10" in vQuiz
    assert (
        client.post(
            "/profile/levels", data={"skill": ["Java"], "level": ["12"]}
        ).status_code
        == 400
    )
    assert client.post("/profile/levels", data={"skill": ["Java"]}).status_code == 400


def test_quiz_questions_prompt_import_and_flag(client):
    """Vérifie la demande ChatGPT, l'import d'une archive et le signalement."""

    vPrompt = client.post(
        "/quiz/prompt", data={"theme": "Kafka", "level": "confirmé", "count": "20"}
    )

    assert "Thème : Kafka. Lot n° 1.\n20 questions : 20 confirmé." in vPrompt.text
    assert (
        client.post("/quiz/prompt", data={"theme": " ", "count": "20"}).status_code
        == 400
    )

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w") as vArchive:
        vArchive.writestr(
            "kafka.json",
            json.dumps(
                [
                    {
                        "id": "kafka-topic",
                        "level": "débutant",
                        "question": "Qu'est-ce qu'un topic ?",
                        "choices": ["Un flux de messages", "Une table"],
                        "answer": 0,
                        "explanation": "Un topic regroupe des messages.",
                    }
                ]
            ),
        )

    vImport = client.post(
        "/quiz/import",
        data={"theme": "Kafka"},
        files={"file": ("questions.zip", vBuffer.getvalue(), "application/zip")},
    )

    assert "1 question(s) ajoutée(s) : Kafka." in vImport.text
    assert "?theme=kafka&mode=spaced" in vImport.text

    vRefused = client.post("/quiz/import", data={"theme": "Kafka", "text": "rien"})

    assert vRefused.status_code == 400
    assert "Aucune question" in vRefused.text

    vFlag = client.post(
        "/quiz/flag",
        data={"question_id": "kafka-topic", "theme": "kafka", "mode": "discover"},
        follow_redirects=False,
    )

    assert vFlag.status_code == 303
    assert 'value="kafka-topic"' not in client.get(vFlag.headers["location"]).text


def test_quiz_pack_visual_references_and_guides(client):
    """Vérifie le schéma, les références et les guides d'un pack importé."""

    vPack = build_pack()

    client.post(
        "/quiz/import",
        files={"file": ("pack.zip", vPack, "application/zip")},
    )

    vResult = client.post(
        "/quiz/answer",
        data={"question_id": "ram-jvm-001", "choice": "0", "mode": "discover"},
    ).text

    assert '<img src="/quiz/asset/ram.svg" alt="RAM">' in vResult
    assert 'href="https://docs.oracle.com/"' in vResult
    assert "Guides pratiques" in vResult
    assert "/quiz/guide/ram-jvm-analyse" in vResult

    vAsset = client.get("/quiz/asset/ram.svg")

    assert vAsset.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in vAsset.headers["content-security-policy"]
    assert client.get("/quiz/asset/absent.svg").status_code == 404
    assert client.get("/quiz/asset/..%2Fscraper.db").status_code == 404

    vGuide = client.get("/quiz/guide/ram-jvm-analyse")

    assert "Analyser la RAM" in vGuide.text
    assert "<li>Heap</li>" in vGuide.text
    assert client.get("/quiz/guide/absent").status_code == 404


def test_quiz_pack_export(client):
    """Vérifie le téléchargement des questions importées, et son absence."""

    vEmpty = client.get("/quiz/export")

    assert vEmpty.status_code == 400
    assert "Aucune question importée" in vEmpty.text

    client.post(
        "/quiz/import", files={"file": ("pack.zip", build_pack(), "application/zip")}
    )

    vExport = client.get("/quiz/export")

    assert vExport.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(vExport.content)) as vArchive:
        assert "questions/ram-jvm.json" in vArchive.namelist()


def test_quiz_exam_on_the_web(client, qcm_only_quiz):
    """Vérifie l'examen sur le web : début, réponse, résultat et fermeture."""

    assert "Mode examen (20 questions)" in client.get("/quiz").text
    assert client.get("/quiz/exam", follow_redirects=False).status_code == 303

    vStart = client.post("/quiz/exam/start", data={"domain": "Informatique"})

    assert "Question 1 / 20" in vStart.text

    for vIndex in range(20):
        vPage = client.get("/quiz/exam").text
        vChoice = re.search(r'name="choice" value="(\d+)"', vPage).group(1)
        vAnswer = client.post("/quiz/exam/answer", data={"choice": vChoice}).text

        assert "Réponse :" in vAnswer

    vResult = client.get("/quiz/exam").text

    assert "Examen terminé" in vResult
    assert "Note :" in vResult
    assert "Fermer l'examen" in vResult

    client.post("/quiz/exam/stop")

    assert client.get("/quiz/exam", follow_redirects=False).status_code == 303
    assert client.post("/quiz/exam/start", data={"domain": "Autres"}).status_code == 400
    assert client.post("/quiz/exam/answer", data={"choice": "0"}).status_code == 400


def test_quiz_category_navigation(client):
    """Vérifie les catégories : filtre, second clic, statut des thèmes et examen."""

    vAll = client.get("/quiz").text

    assert 'class="quiz-tab is-active"' in vAll
    assert 'class="quiz-chip is-empty"' in vAll
    assert "Tous les thèmes (" in vAll
    assert "<h2>Informatique</h2>" in vAll
    assert "questions acquises" in vAll
    assert '<span class="subdomain-badge">' in vAll

    vFiltered = client.get(
        "/quiz", params={"domain": "Informatique", "subdomain": "Données"}
    ).text

    assert "<h2>Informatique › Données</h2>" in vFiltered
    assert ">SQL</h2>" in vFiltered
    assert ">Java</h2>" not in vFiltered
    # Lien de la catégorie active : il ramène au domaine, sans le sous-domaine.
    assert 'href="/quiz?domain=Informatique"' in vFiltered
    assert 'name="subdomain" value="Données"' in vFiltered

    vEmpty = client.get(
        "/quiz", params={"domain": "Industrie", "subdomain": "Électricité et énergie"}
    ).text

    assert "Aucune question dans cette rubrique" in vEmpty
    assert 'name="theme" value="' in vEmpty

    client.post(
        "/quiz/answer",
        data={"question_id": "sql-null", "choice": "1", "mode": "spaced"},
    )

    assert 'class="tone-primary" title="Révision commencée"' in client.get("/quiz").text


def test_quiz_imported_questions_cleared_after_confirmation(client):
    """Vérifie l'effacement des questions importées depuis le web, confirmé."""

    client.post(
        "/quiz/import", files={"file": ("pack.zip", build_pack(), "application/zip")}
    )

    vRefused = client.post("/quiz/clear", data={})

    assert vRefused.status_code == 400
    assert "Cochez la case" in vRefused.text

    vCleared = client.post("/quiz/clear", data={"confirm": "1"}).text

    assert "2 question(s) importée(s) effacée(s)" in vCleared
    assert "Analyse RAM et JVM" not in vCleared


def test_biased_lot_shows_a_correction_prompt(client):
    """Vérifie la demande de correction affichée après l'import d'un lot biaisé."""

    vResponse = client.post(
        "/quiz/import",
        data={
            "text": build_lot_text(
                [
                    build_question(vIndex, pAnswer=1, pLongest=True)
                    for vIndex in range(MIN_QUALITY_SAMPLE)
                ]
            )
        },
    )

    assert vResponse.status_code == 200
    assert "tone-warning" in vResponse.text
    assert 'id="quiz-correction"' in vResponse.text
    assert "Questions concernées : grafcet-l1-000" in vResponse.text


def test_validated_packs_are_imported_from_the_dashboard(client, tmp_path, monkeypatch):
    """Vérifie le bouton web des lots validés et le message sans archive."""

    vFolder = tmp_path / "packs"
    vFolder.mkdir()
    monkeypatch.setattr(quiz_packs, "QUIZ_PACKS_DIRECTORY", str(vFolder))

    assert "Importer les lots validés" not in client.get("/quiz").text
    assert client.post("/quiz/import-packs").status_code == 400

    vName, vContent = build_lot_pack("grafcet")
    (vFolder / vName).write_bytes(vContent)

    assert "Importer les lots validés (1)" in client.get("/quiz").text

    vResponse = client.post("/quiz/import-packs")

    assert vResponse.status_code == 200
    assert "100 question(s) ajoutée(s)" in vResponse.text


def test_priority_themes_are_shown_on_the_quiz_page(client):
    """Vérifie la carte des thèmes prioritaires et sa demande préparée."""

    assert "Aucun thème n'est encore demandé" in client.get("/quiz").text

    save_offers(
        app.dependency_overrides[get_database_file](),
        pd.DataFrame(
            [
                {
                    "source": "remotive",
                    "source_id": "99",
                    "title": "Dev",
                    "skills": ["SCADA"],
                }
            ]
        ),
        datetime.now(),
    )
    vPage = client.get("/quiz").text

    assert "<strong>Supervision, SCADA et IHM</strong>" in vPage
    assert '<input type="hidden" name="count" value="100">' in vPage


def test_typed_quiz_questions_on_the_web(client):
    """Vérifie les questions interactives sur le web : champs, saisie refusée, réussite."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    import_questions(
        vDatabaseFile,
        "",
        json.dumps({"theme": "Électricité", "questions": [NUMERIC, ORDER, PAIRS]}),
        datetime.now(),
    )

    vRetry = client.post(
        "/quiz/answer", data={"question_id": "ohm-courant", "text": "2,3 V"}
    )

    assert vRetry.status_code == 400
    assert "Unité attendue : A" in vRetry.text
    assert 'name="text"' in vRetry.text and "ohm-courant" in vRetry.text

    vOrder = client.post(
        "/quiz/answer",
        data={"question_id": "consignation-ordre", "indexes": ["0", "0", "1", "2"]},
    )

    assert vOrder.text.count('name="indexes"') == 4

    vPairs = client.post(
        "/quiz/answer", data={"question_id": "grandeurs-unites", "indexes": ["0"]}
    )

    assert "Réponse incomplète" in vPairs.text
    assert '<option value="">Choisir…</option>' in vPairs.text

    vSolved = client.post(
        "/quiz/answer", data={"question_id": "ohm-courant", "text": "2,3 mA"}
    )

    assert "Bonne réponse" in vSolved.text and "0,0023 A" in vSolved.text
    assert (
        client.post(
            "/quiz/answer", data={"question_id": "inconnue", "choice": "0"}
        ).status_code
        == 400
    )


def test_symbol_question_shows_its_visual_on_the_web(client):
    """Vérifie qu'un symbole à reconnaître est montré avec la question sur le web."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vPage = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-024", "indexes": ["0"]},
    ).text

    assert "Réponse incomplète" in vPage
    assert "electricite-symboles-commande.svg" in vPage


def test_zone_question_is_answered_by_clicking_the_image(client):
    """Vérifie une zone sur le web : image cliquable, coordonnées reçues et corrigées."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vRetry = client.post("/quiz/answer", data={"question_id": "electricite-l1-021"})

    assert vRetry.status_code == 400
    assert 'type="image" name="point"' in vRetry.text
    assert "Valider</button>" not in vRetry.text.split("quiz-flag")[0]

    vRight = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-021", "point.x": "390", "point.y": "115"},
    )

    assert "Bonne réponse" in vRight.text

    vWrong = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-021", "point.x": "80", "point.y": "115"},
    )

    assert "Votre réponse : Fusible" in vWrong.text


def test_schema_question_is_built_and_graded_on_the_web(client):
    """Vérifie un schéma à construire sur le web : éditeur, JSON reçu et correction."""

    import_questions_file(
        app.dependency_overrides[get_database_file](),
        "",
        *build_lot_pack("electricite"),
        datetime.now(),
    )

    vEditor = client.post(
        "/quiz/answer", data={"question_id": "electricite-l1-015", "text": ""}
    )

    assert vEditor.status_code == 400
    assert "Placez au moins un composant" in vEditor.text
    assert "data-schema-editor" in vEditor.text and 'data-type="prise"' in vEditor.text

    vChain = ["reseau", "differentiel", "disjoncteur", "prise"]
    vSchema = {
        "components": [
            {"type": vType, "x": 0, "y": vIndex} for vIndex, vType in enumerate(vChain)
        ],
        "wires": [
            ["reseau", "sortie", "differentiel", "1"],
            ["differentiel", "2", "disjoncteur", "1"],
            ["disjoncteur", "2", "prise", "entrée"],
        ],
    }
    vRight = client.post(
        "/quiz/answer",
        data={"question_id": "electricite-l1-015", "text": json.dumps(vSchema)},
    )

    assert "Bonne réponse" in vRight.text
    assert "schema-expected" in vRight.text and ">Votre schéma</text>" in vRight.text


def test_offer_revision_and_mock_exam(client):
    """Vérifie les thèmes à revoir sur la fiche d'offre et l'examen blanc associé."""

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Réviser pour l'entretien" in vPage
    assert "Examen blanc (16 questions)" in vPage
    assert 'name="id" value="new"' in vPage

    vStart = client.post("/quiz/exam/start", data={"source": "adzuna", "id": "new"})

    assert "Entretien : Développeur Python new chez Entreprise A" in vStart.text
    assert "Question 1 / 16" in vStart.text
    assert 'data-remaining="960"' in vStart.text or "Temps restant : 15:" in vStart.text

    client.post("/quiz/exam/stop")

    assert (
        client.post(
            "/quiz/exam/start", data={"source": "adzuna", "id": "inconnue"}
        ).status_code
        == 404
    )


def test_skills_page(client):
    """Vérifie le tableau des compétences : chiffres clés, actions et menu."""

    vPage = client.get("/skills").text

    assert "À travailler en premier" in vPage
    assert "<strong>Python</strong>" in vPage
    assert 'href="/skills"' in vPage
    assert "?theme=python" in vPage
    assert "Glossaire des compétences" in vPage
    assert 'title="Langage polyvalent' in vPage

    vPrompt = client.post("/quiz/prompt", data={"theme": "Cloud et infrastructure"})

    assert vPrompt.status_code == 200


def test_skill_is_added_to_profile_from_the_web(client):
    """Vérifie le formulaire d'ajout d'une compétence au profil."""

    vResponse = client.post("/skills/profile", data={"skill": "Python"})
    vPage = client.get("/skills").text

    assert vResponse.status_code == 200
    assert 'name="skill" value="Python"' not in vPage
    assert 'name="skill" value="Django"' in vPage


def test_offer_page_charts_mock_exam_scores(client, monkeypatch):
    """Vérifie le graphique des notes d'examen blanc à partir de deux examens."""

    vResults = [
        {"finished_at": "2026-10-14T10:00:00", "score": 80, "offer": ["adzuna", "new"]},
        {"finished_at": "2026-10-12T10:00:00", "score": 40, "offer": ["adzuna", "new"]},
    ]
    monkeypatch.setattr(
        "web.routes.offer_detail.load_exam_results",
        lambda pDatabaseFile, pKey: vResults,
    )

    vPage = client.get("/offer", params={"source": "adzuna", "id": "new"}).text

    assert "Notes des examens blancs" in vPage
    assert "meilleure note 80 %" in vPage


def test_quiz_exam_errors_are_reviewed_on_the_web(client):
    """Vérifie l'enchaînement sur les erreurs, refusé tant qu'il n'y en a pas."""

    assert client.post("/quiz/exam/errors").status_code == 400

    client.post("/quiz/exam/start", data={"source": "adzuna", "id": "new"})

    for _ in range(16):
        client.post("/quiz/exam/answer", data={"choice": "0"})

    vResult = client.get("/quiz/exam").text

    assert "Revoir les" in vResult

    vReview = client.post("/quiz/exam/errors")

    assert "Erreurs : Entretien" in vReview.text


def test_priority_skills_exam_is_started(client):
    """Vérifie l'examen blanc lancé sur des compétences, puis le refus sans thème."""

    vRefused = client.post("/quiz/exam/start", data={"skills": "Inconnue"})
    vStarted = client.post("/quiz/exam/start", data={"skills": "SQL"})

    assert vStarted.url.path == "/quiz/exam"
    assert vRefused.status_code == 400
    assert "Aucun thème de révision ne couvre ces compétences" in vRefused.text
