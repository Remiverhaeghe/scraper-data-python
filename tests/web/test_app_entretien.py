"""Tests web des entretiens et de la négociation"""




def test_interview_simulation_on_the_web(client):
    """Vérifie une série de simulation sur le web jusqu'au bilan."""

    assert "Simulation d'entretien technique" in client.get("/profile").text
    assert (
        client.post("/profile/simulation/start", data={"theme": "Cobol"}).status_code
        == 400
    )

    client.post("/profile/simulation/start", data={"theme": "Android"})

    for vIndex in range(5):
        vPage = client.get("/profile").text

        assert f"question {vIndex + 1} sur 5" in vPage

        client.post("/profile/simulation/answer", data={"points": ["0", "1"]})

    vSummary = client.get("/profile").text

    assert "Série terminée" in vSummary
    assert "Dernières séries : Android" in vSummary
    assert client.post("/profile/simulation/answer", data={}).status_code == 400

    client.post("/profile/simulation/stop")

    assert "Série terminée" not in client.get("/profile").text


def test_interview_date_and_calendar_export(client):
    """Vérifie la date d'entretien saisie et le fichier agenda téléchargé."""

    vOfferUrl = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    ).headers["location"]
    vSourceId = vOfferUrl.rsplit("=", 1)[1]

    client.post(
        "/offer/application",
        data={
            "source": "manual",
            "id": vSourceId,
            "status": "INTERVIEW",
            "interview_at": "2026-10-20T14:30",
        },
    )

    assert 'value="2026-10-20T14:30"' in client.get(vOfferUrl).text

    vCalendar = client.get("/applications/calendar.ics")

    assert vCalendar.headers["content-type"].startswith("text/calendar")
    assert "SUMMARY:Entretien : Analyste Kotlin – Data SA" in vCalendar.text


def test_profile_star_answers(client):
    """Vérifie l'enregistrement d'une réponse STAR et son refus si invalide."""

    vSaved = client.post(
        "/profile/star",
        data={"question": "echec", "experience": "", "action": "Revu les tests"},
    )
    vRefused = client.post("/profile/star", data={"question": "inconnue"})

    assert "Réponse enregistrée." in vSaved.text
    assert "1 réponse(s) préparée(s) sur 7" in vSaved.text
    assert vRefused.status_code == 400


def test_interview_journal_on_offer_page(client):
    """Vérifie l'ajout d'une entrée au journal depuis la fiche d'une offre."""

    vEmpty = client.post(
        "/offer/interview-note", data={"source": "adzuna", "id": "new"}
    )
    vAdded = client.post(
        "/offer/interview-note",
        data={"source": "adzuna", "id": "new", "questions": "Votre plus grand défi ?"},
    )
    client.post("/profile", data={"skills": "Java"})
    vPage = client.get("/offer", params={"source": "adzuna", "id": "old"}).text

    assert vEmpty.status_code == 400
    assert "Entrée ajoutée au journal." in vAdded.text
    assert "Votre plus grand défi ?" in vAdded.text
    assert "Questions déjà posées en entretien" in vPage


def test_interview_mission_steps_are_ticked_on_the_offer_page(client):
    """Vérifie la mission d'entretien de la fiche : absente sans profil, étape cochée, boss refusé."""

    assert "Mission entretien" not in client.get("/offer?source=adzuna&id=new").text

    client.post("/profile", data={"skills": "Python"})

    assert "Mission entretien · " in client.get("/offer?source=adzuna&id=new").text

    vTicked = client.post(
        "/offer/mission",
        data={"source": "adzuna", "id": "new", "step": "pitch", "done": "true"},
    )

    assert 'id="mission-pitch" checked' in vTicked.text
    assert "1 étape(s) sur 6" in vTicked.text or "2 étape(s) sur 6" in vTicked.text
    assert (
        client.post(
            "/offer/mission",
            data={"source": "adzuna", "id": "new", "step": "boss", "done": "true"},
        ).status_code
        == 400
    )


def test_oral_interview_is_played_on_the_profile_page(client):
    """Vérifie une séance d'entretien oral sur le web : choix refusé, notes, bilan."""

    assert 'id="oral"' in client.get("/profile").text
    assert (
        client.post(
            "/profile/oral/start", data={"mode": "x", "duration": "90"}
        ).status_code
        == 400
    )

    client.post("/profile/oral/start", data={"mode": "tricky", "duration": "60"})

    for vPosition in range(5):
        vPage = client.post(
            "/profile/oral/answer",
            data={"position": vPosition, "seconds": 45, "structure": 2, "example": 1},
        )

    assert "Dernière séance terminée : 83 %" in vPage.text
    assert (
        client.post(
            "/profile/oral/answer",
            data={"position": 0, "seconds": 45, "structure": 2, "example": 1},
        ).status_code
        == 400
    )

    client.post("/profile/oral/start", data={"mode": "general", "duration": "90"})
    vPage = client.post(
        "/profile/oral/answer",
        data={"position": 0, "seconds": 5, "structure": 0, "example": 0},
    )

    assert "Réponse précédente notée 0 %" in vPage.text
    assert "Nouvelle séance" in client.post("/profile/oral/stop").text


def test_salary_negotiation_is_played_on_the_offer_page(client, monkeypatch):
    """Vérifie le jeu de négociation : sans marché, puis une partie jouée jusqu'au score."""

    vStart = {"source": "adzuna", "id": "new"}

    assert (
        "Simuler la négociation salariale"
        in client.get("/offer?source=adzuna&id=new").text
    )

    monkeypatch.setattr(
        "job.salary_negotiation.load_market_median", lambda *pArgs: None
    )
    monkeypatch.setattr(
        "job.salary_negotiation.find_market_salary", lambda *pArgs: None
    )

    assert (
        "Pas encore assez d"
        in client.post("/offer/negotiation/start", data=vStart).text
    )

    monkeypatch.setattr(
        "job.salary_negotiation.load_market_median", lambda *pArgs: 2500
    )
    client.post("/offer/negotiation/start", data=vStart)

    for vChoice in ("range", "argue", "accept"):
        vPage = client.post("/offer/negotiation/play", data={"choice": vChoice})

    assert "Accord à" in vPage.text and "score" in vPage.text
    assert '"source": "adzuna"' in vPage.text
    assert (
        "1 partie(s) · meilleur score" in client.get("/offer?source=adzuna&id=new").text
    )
    assert (
        client.post("/offer/negotiation/play", data={"choice": "accept"}).status_code
        == 400
    )


def test_interview_drill_on_the_web(client):
    """Vérifie la question affichée puis notée depuis la page Profil."""

    client.post("/profile/star", data={"question": "echec", "result": "Leçon"})

    vPage = client.get("/profile").text
    vCard = vPage.split('name="card" value="')[1].split('"')[0]
    vGraded = client.post("/profile/drill", data={"card": vCard, "known": "1"})

    assert "Racontez un échec" in vPage
    assert "Aucune question à revoir aujourd" in vGraded.text
