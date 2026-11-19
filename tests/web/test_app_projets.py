"""Tests web de la page Projets et des formations visées"""


def test_portfolio_page_shows_sheet_texts_and_questions(client):
    """Vérifie la fiche, les textes à copier et les questions d'entretien."""

    vResponse = client.get("/portfolio")

    assert vResponse.status_code == 200
    assert 'aria-current="page"' in vResponse.text
    assert "Atelier · Application Android" in vResponse.text
    assert "Ligne pour la rubrique Projets du CV" in vResponse.text
    assert "Sur mon temps personnel, j&#39;ai développé Atelier" in vResponse.text
    assert "Comment savez-vous que ça marche ?" in vResponse.text

    vKalkul = client.get("/portfolio?project=kalkul").text

    assert "MoteurCalcul.java" in vKalkul
    assert "Où sont les données" not in vKalkul
    assert client.get("/portfolio?project=inconnu").status_code == 404


def test_portfolio_downloads(client):
    """Vérifie les téléchargements : PDF, fiche et questions en texte."""

    vPdf = client.get("/portfolio/pdf?project=kalkul")

    assert vPdf.headers["content-type"] == "application/pdf"
    assert vPdf.content.startswith(b"%PDF")
    assert "Fiche%20projet%20Kalkul.pdf" in vPdf.headers["content-disposition"]

    vSheet = client.get("/portfolio/text?project=tremplin")

    assert vSheet.text.startswith("Tremplin - ")
    assert vSheet.headers["content-type"].startswith("text/plain")

    vQuestions = client.get("/portfolio/text?project=atelier&kind=questions")

    assert vQuestions.text.startswith("Entretien : questions probables sur Atelier")
    assert client.get("/portfolio/text?project=atelier&kind=autre").status_code == 422
    assert client.get("/portfolio/pdf?project=inconnu").status_code == 404


def test_offer_page_suggests_projects_to_cite(client):
    """Vérifie que la fiche d'une offre propose les projets aux compétences proches."""

    client.post("/profile", data={"skills": "Python"})

    vPage = client.get("/offer?source=adzuna&id=new").text

    assert "Projets à citer" in vPage
    assert "?project=tremplin" in vPage


def test_training_goal_is_added_listed_then_removed(client):
    """Vérifie l'ajout d'un objectif, son affichage, puis son retrait."""

    vSaved = client.post(
        "/certifications/goals/save",
        data={
            "title": "Cours <b>Python</b>",
            "organism": "Organisme fictif",
            "status": "in_progress",
            "target": "2020-01-01",
            "skills": "python, django",
        },
        follow_redirects=False,
    )

    assert vSaved.status_code == 303
    assert vSaved.headers["location"] == "/certifications#objectifs"

    vPage = client.get("/certifications").text

    assert "Cours &lt;b&gt;Python&lt;/b&gt;" in vPage
    assert "En retard" in vPage
    assert "Python (1), Django (1)" in vPage

    vId = vPage.split('name="id" value="', 1)[1].split('"', 1)[0]

    assert (
        client.post(
            "/certifications/goals/delete", data={"id": vId}, follow_redirects=False
        ).status_code
        == 303
    )
    assert "Aucun objectif pour le moment." in client.get("/certifications").text
    assert (
        client.post("/certifications/goals/delete", data={"id": vId}).status_code == 404
    )
    assert (
        client.post(
            "/certifications/goals/save", data={"link": "javascript:x", "title": "A"}
        ).status_code
        == 400
    )
