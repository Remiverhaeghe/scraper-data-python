"""Tests web des défis, énigmes et exercices pratiques"""

from datetime import datetime
import json
import re

from job.aptitude import generate_session
from job.challenges import get_expected_answers, get_seed
from job.code_puzzles import SERIES_LENGTH, build_puzzle_view
from web.app import app, get_database_file


def test_challenges_are_listed_downloaded_and_answered(client):
    """Vérifie les défis sur le web : liste, données, réponses et refus."""

    vList = client.get("/challenges")

    assert vList.status_code == 200
    assert "Les arrêts de la ligne 3" in vList.text
    assert client.get("/challenges/inconnu").status_code == 404

    vPage = client.get("/challenges/engrenages?hints=1")

    assert "Partie 1" in vPage.text and "Partie 2" not in vPage.text
    assert "<li>Après t tours" in vPage.text
    assert "?hints=2" in vPage.text

    vInput = client.get("/challenges/engrenages/input")

    assert vInput.status_code == 200
    assert "engrenages.txt" in vInput.headers["content-disposition"]

    vWrong = client.post(
        "/challenges/engrenages/answer", data={"part": "1", "answer": "1"}
    )

    assert "Ce n&#39;est pas la bonne réponse." in vWrong.text
    assert (
        client.post(
            "/challenges/engrenages/answer", data={"part": "1", "answer": " "}
        ).status_code
        == 400
    )
    assert (
        client.post("/challenges/inconnu/answer", data={"answer": "1"}).status_code
        == 404
    )

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    vExpected = get_expected_answers(
        "pieces-bonnes", get_seed(vDatabaseFile, "pieces-bonnes", datetime.now())
    )

    for vPart, vAnswer in enumerate(vExpected, start=1):
        vSolved = client.post(
            "/challenges/pieces-bonnes/answer",
            data={"part": str(vPart), "answer": vAnswer},
        )

    assert "Solution commentée" in vSolved.text
    assert "★★" in vSolved.text


def test_code_puzzles_are_played_by_series(client):
    """Vérifie une série de puzzles sur le web : réponses, renvoi refusé, bilan."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()

    assert "Puzzles de code" in client.get("/challenges").text
    assert "Commencer une série" in client.get("/puzzles").text

    client.post("/puzzles/start")

    for vPosition in range(SERIES_LENGTH):
        vPuzzle = build_puzzle_view(vDatabaseFile)["puzzle"]
        vData = {"position": str(vPosition)}

        # Le premier puzzle reçoit une réponse fausse, les autres la bonne
        if vPuzzle["type"] == "ordre":
            vIndexes = list(range(len(vPuzzle["items"])))
            vData["indexes"] = [
                str(vIndex) for vIndex in vIndexes[:: -1 if vPosition == 0 else 1]
            ]
        elif vPuzzle["type"] == "saisie":
            vData["text"] = vPuzzle["accepted"][0] if vPosition else "faux"
        else:
            vLine = vPuzzle["line"] - 1
            vData["choice"] = str(
                vLine if vPosition else (vLine + 1) % len(vPuzzle["lines"])
            )

        vPage = client.post("/puzzles/answer", data=vData)

    assert client.post("/puzzles/answer", data={"position": "0"}).status_code == 400
    assert "Bilan de la série : 9 sur 10" in vPage.text
    assert "Réponse attendue" in vPage.text
    assert "Nouvelle série" in vPage.text


def test_git_levels_are_listed_played_and_solved(client):
    """Vérifie le bac à sable Git sur le web : liste, commandes, annulation et réussite."""

    vList = client.get("/git")

    assert vList.status_code == 200
    assert "Enregistrer son travail" in vList.text
    assert "git cherry-pick" in vList.text
    assert client.get("/git/inconnu").status_code == 404
    assert client.post("/git/inconnu/command", data={}).status_code == 404

    vPage = client.get("/git/premiers-commits")

    assert vPage.text.count("<svg") >= 2 and "Objectif" in vPage.text

    vFirst = client.post(
        "/git/premiers-commits/command", data={"command": "git commit"}
    )

    assert "Commit C1 enregistré" in vFirst.text
    assert 'name="history" value="git commit"' in vFirst.text

    vUndone = client.post(
        "/git/premiers-commits/command",
        data={"history": ["git commit"], "action": "undo"},
    )

    assert 'name="history"' not in vUndone.text

    vSolved = client.post(
        "/git/premiers-commits/command",
        data={"history": ["git commit"], "command": "git commit"},
    )

    assert "parcours optimal" in vSolved.text
    assert "Niveau suivant" in vSolved.text
    assert "Serveur attendu" not in vSolved.text
    assert "Serveur attendu" in client.get("/git/push").text
    assert (
        client.post(
            "/git/premiers-commits/command",
            data={"history": ["git bisect"], "command": "git commit"},
        ).status_code
        == 400
    )


def test_aptitude_session_is_played_and_corrected(client):
    """Vérifie le choix, la partie tirée, la correction côté serveur et le score."""

    assert "Raisonnement mécanique" in client.get("/aptitude").text

    vPage = client.get("/aptitude/play?category=plans").text
    vSeed = int(re.search(r'name="seed" value="(\d+)"', vPage).group(1))
    vStarted = re.search(r'name="started" value="([^"]+)"', vPage).group(1)
    vQuestions = generate_session("plans", vSeed)
    vData = {"category": "plans", "seed": str(vSeed), "started": vStarted}
    vData |= {
        f"answer-{vIndex}": str(vQuestion["answer"])
        for vIndex, vQuestion in enumerate(vQuestions[:9])
    }

    vResult = client.post("/aptitude/finish", data=vData).text

    assert "Lecture de plans : 9 / 10 (90 %)" in vResult
    assert "pas de réponse" in vResult
    assert client.get("/aptitude/play?category=inconnue").status_code == 404
    assert (
        client.post(
            "/aptitude/finish", data={"category": "plans", "seed": "x"}
        ).status_code
        == 400
    )


def test_troubleshooting_is_played_on_the_web(client):
    """Vérifie une mesure par lien, une mauvaise réparation puis la bonne."""

    assert (
        "Le vérin sort de plus en plus lentement" in client.get("/troubleshooting").text
    )

    vPage = client.get(
        "/troubleshooting/play?scenario=verin-lent&actions=check:silencieux"
    ).text

    assert "noirci et gras" in vPage

    vWrong = client.post(
        "/troubleshooting/repair",
        data={
            "scenario": "verin-lent",
            "actions": "check:silencieux",
            "cause": "joints",
        },
        follow_redirects=False,
    )

    assert vWrong.status_code == 303
    assert "repair%3Ajoints" in vWrong.headers["location"]

    vResult = client.post(
        "/troubleshooting/repair",
        data={
            "scenario": "verin-lent",
            "actions": "check:silencieux,repair:joints",
            "cause": "silencieux",
        },
    ).text

    assert "Le vérin sort de plus en plus lentement : " in vResult
    assert "1 pièce changée pour rien" in vResult
    assert client.get("/troubleshooting/play?scenario=inconnu").status_code == 404


def test_ladder_level_is_checked_on_the_web(client):
    """Vérifie le niveau, une faute d'écriture, puis la solution réussie et dessinée."""

    vPage = client.get("/ladder?level=marche-arret").text

    assert "Marche, arrêt et auto-maintien" in vPage
    assert "<svg" in vPage

    vError = client.post(
        "/ladder/check", data={"level": "marche-arret", "program": "marche = arret"}
    ).text

    assert "est une entrée" in vError

    vResult = client.post(
        "/ladder/check",
        data={
            "level": "marche-arret",
            "program": "moteur = (marche | moteur) & arret",
        },
    ).text

    assert "Niveau réussi · +25 XP" in vResult
    assert "Chronogramme du scénario de test" in vResult
    assert "<script" not in vResult.split("<main", 1)[-1]
    assert client.get("/ladder?level=inconnu").status_code == 404


def test_sql_level_is_run_on_the_web(client):
    """Vérifie le niveau, une erreur de dialecte, le changement de dialecte et la réussite."""

    vPage = client.get("/sql?level=plus-cheres").text

    assert "Les trois interventions les plus coûteuses" in vPage
    assert "Requête en MySQL" in vPage

    vError = client.post(
        "/sql/run",
        data={
            "level": "plus-cheres",
            "query": "SELECT TOP 3 id, cout FROM intervention",
        },
    ).text

    assert "MySQL n&#39;a pas TOP" in vError
    assert "Résultat attendu" in vError

    vRedirect = client.post(
        "/sql/dialect",
        data={"dialect": "sqlserver", "level": "plus-cheres"},
        follow_redirects=False,
    )

    assert vRedirect.status_code == 303
    assert vRedirect.headers["location"] == "/sql?level=plus-cheres"

    vResult = client.post(
        "/sql/run",
        data={
            "level": "plus-cheres",
            "query": "SELECT TOP 3 id, cout FROM intervention ORDER BY cout DESC",
        },
    ).text

    assert "Niveau réussi · +15 XP" in vResult
    assert "<td>2340</td>" in vResult
    assert client.get("/sql?level=inconnu").status_code == 404
    assert client.post("/sql/dialect", data={"dialect": "oracle"}).status_code == 400


def test_excel_level_is_checked_on_the_web(client):
    """Vérifie la feuille, un $ oublié signalé et la réussite enregistrée."""

    vPage = client.get("/excel?level=taux-fige").text

    assert "Prix TTC" in vPage
    assert 'class="excel-target "' in vPage

    vError = client.post(
        "/excel/run", data={"level": "taux-fige", "formula": "=B2*(1+F1)"}
    ).text

    assert "5 cellules sur 6" in vError
    assert "excel-target ko" in vError

    vResult = client.post(
        "/excel/run", data={"level": "taux-fige", "formula": "=B2*(1+$F$1)"}
    ).text

    assert "Niveau réussi · +15 XP" in vResult
    assert ">10,08 €</td>" in vResult
    assert "1 / " in client.get("/excel").text
    assert client.get("/excel?level=inconnu").status_code == 404


def test_circuit_is_checked_operated_saved_and_exported_on_the_web(client):
    """Vérifie un montage réussi, un poussoir manœuvré, un schéma libre et son export."""

    from job.circuit_levels import get_solution, load_levels

    vLevel = load_levels()["demarrage-moteur"]
    vComponents, vWires, _ = get_solution(vLevel)
    vAnswer = json.dumps({"components": vComponents, "wires": vWires})

    assert (
        "moteur avec auto-maintien"
        in client.get("/circuit?level=demarrage-moteur").text
    )

    vChecked = client.post(
        "/circuit/run",
        data={"level": "demarrage-moteur", "answer": vAnswer, "action": "check"},
    ).text

    assert "Montage réussi · +20 XP" in vChecked
    assert "<svg" in vChecked

    vStarted = client.post(
        "/circuit/run",
        data={
            "level": "demarrage-moteur",
            "answer": vAnswer,
            "action": "operate:bouton_marche",
            "inputs": "{}",
            "memory": "{}",
        },
    ).text

    assert "tourne" in vStarted
    assert (
        "Placez au moins un composant"
        in client.post(
            "/circuit/run",
            data={"level": "demarrage-moteur", "answer": "", "action": "check"},
        ).text
    )

    vFree = json.dumps(
        {
            "components": [{"id": "pile", "type": "pile", "x": 0, "y": 0}],
            "wires": [],
        }
    )
    vSaved = client.post(
        "/circuit/run",
        data={"answer": vFree, "action": "save", "name": "Ma pile", "value_pile": "12"},
        follow_redirects=False,
    )

    assert vSaved.status_code == 303
    assert "Ma pile" in client.get("/circuit?free=1&schema=Ma+pile").text

    vExport = client.post(
        "/circuit/run", data={"answer": vFree, "action": "export", "name": "Ma pile"}
    )

    assert vExport.headers["content-type"].startswith("image/svg+xml")
    assert 'filename="Ma-pile.svg"' in vExport.headers["content-disposition"]
    assert client.get("/circuit?level=inconnu").status_code == 404


def test_circuit_solution_rearm_and_free_schema_errors_on_the_web(client):
    """Vérifie la solution, le réarmement d'un disjoncteur, les refus et la suppression."""

    assert client.get("/circuit").status_code == 200

    vPartial = json.dumps(
        {"components": [{"id": "pile", "type": "alimentation", "x": 0, "y": 0}]}
    )
    vSolution = client.post(
        "/circuit/run",
        data={"level": "demarrage-moteur", "answer": vPartial, "action": "solution"},
    ).text

    assert "<svg" in vSolution

    assert (
        "Placez au moins un composant"
        in client.post(
            "/circuit/run",
            data={"level": "demarrage-moteur", "answer": "{", "action": "check"},
        ).text
    )

    vFree = json.dumps(
        {
            "components": [
                {"id": "pile", "type": "pile", "x": 0, "y": 0},
                {"id": "disj", "type": "disjoncteur", "x": 2, "y": 0},
            ],
            "wires": [],
        }
    )
    vRearmed = client.post(
        "/circuit/run",
        data={
            "answer": vFree,
            "action": "operate:disj",
            "inputs": json.dumps({"disj": False}),
            "memory": json.dumps({"tripped": ["disj"]}),
        },
    )

    assert vRearmed.status_code == 200
    assert client.post("/circuit/run", data={"answer": vFree}).status_code == 200
    assert (
        client.post(
            "/circuit/run",
            data={"answer": vFree, "action": "operate:inconnu"},
        ).status_code
        == 200
    )

    assert (
        "Donnez un nom au schéma."
        in client.post(
            "/circuit/run", data={"answer": vFree, "action": "save", "name": " "}
        ).text
    )

    client.post(
        "/circuit/run",
        data={"answer": vFree, "action": "save", "name": "A supprimer"},
        follow_redirects=False,
    )
    vDeleted = client.post(
        "/circuit/delete", data={"name": "A supprimer"}, follow_redirects=False
    )

    assert vDeleted.status_code == 303
    assert vDeleted.headers["location"].endswith("/circuit?free=1")
    assert "A supprimer" not in client.get("/circuit?free=1").text


def test_devops_level_is_played_on_the_web(client):
    """Vérifie une commande Docker refusée, la solution réussie et la remise à zéro."""

    from job.devops_levels import load_levels

    vLevel = load_levels()["docker-port-pris"]

    assert "Le port déjà pris" in client.get("/devops?level=docker-port-pris").text

    def run(pCommand):
        return client.post(
            "/devops/run",
            data={
                "level": vLevel["id"],
                "file": vLevel["solution"],
                "command": pCommand,
            },
        ).text

    run("docker build -t atelier:1.0 .")

    assert "port is already allocated" in run("docker run -d -p 8080:8080 atelier:1.0")

    run("docker run -d --name atelier -p 8081:8080 atelier:1.0")
    vResult = run("curl http://localhost:8081/")

    assert "Objectif atteint · +20 XP" in vResult
    assert "devops-console" in vResult

    vReset = client.post(
        "/devops/reset", data={"level": vLevel["id"]}, follow_redirects=False
    )

    assert vReset.status_code == 303
    assert "devops-console" not in client.get("/devops?level=docker-port-pris").text
    assert client.get("/devops?level=inconnu").status_code == 404
