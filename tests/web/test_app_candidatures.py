"""Tests web du suivi des candidatures et des documents"""

from datetime import datetime
import io
import re

from pypdf import PdfReader

from job.education import save_education_levels
from storage.job_applications import get_application
from web.app import app, get_database_file
import web.routes.applications as web_applications
import web.routes.offer_detail as web_offer_detail


def test_show_offer_displays_application_form(client):
    """Vérifie la présence du formulaire de suivi sur la fiche."""

    vResponse = client.get("/offer", params={"source": "adzuna", "id": "new"})

    assert "Aucun suivi" in vResponse.text
    assert 'name="follow_up_date"' in vResponse.text


def test_update_application_saves_status_and_notes(client):
    """Vérifie l'enregistrement d'un statut et de notes."""

    vResponse = client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": "",
            "notes": "Envoyée via le site",
        },
    )

    assert vResponse.status_code == 200
    assert "Suivi enregistré" in vResponse.text
    assert "Envoyée via le site" in vResponse.text
    assert "Candidature envoyée le" in vResponse.text
    assert "relancé aujourd" in vResponse.text

    vList = client.get("/offers", params={"status": "APPLIED"})

    assert "1 offre" in vList.text
    assert "Postulé" in vList.text


def test_update_application_without_status_deletes_tracking(client):
    """Vérifie qu'un statut vide supprime le suivi."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "IGNORED"},
    )

    assert "2 offres" in client.get("/offers").text

    client.post(
        "/offer/application", data={"source": "adzuna", "id": "new", "status": ""}
    )

    assert "3 offres" in client.get("/offers").text


def test_update_application_rejects_unknown_values(client):
    """Vérifie le refus d'un statut ou d'une offre inconnus."""

    vBadStatus = client.post(
        "/offer/application", data={"source": "adzuna", "id": "new", "status": "HACK"}
    )
    vUnknownOffer = client.post(
        "/offer/application", data={"source": "adzuna", "id": "x", "status": "APPLIED"}
    )

    assert vBadStatus.status_code == 400
    assert vUnknownOffer.status_code == 404


def test_add_follow_up(client):
    """Vérifie l'enregistrement d'une relance."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "APPLIED"},
    )

    vResponse = client.post("/offer/follow-up", data={"source": "adzuna", "id": "new"})

    assert "Relance enregistrée" in vResponse.text
    assert "1 relance" in vResponse.text


def test_add_follow_up_requires_tracking(client):
    """Vérifie qu'une relance exige un suivi existant."""

    vResponse = client.post("/offer/follow-up", data={"source": "adzuna", "id": "new"})

    assert vResponse.status_code == 400


def test_list_offers_shows_follow_ups_due(client):
    """Vérifie le filtre des candidatures à relancer."""

    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": "2020-01-01",
        },
    )

    vResponse = client.get("/offers", params={"status": "FOLLOW_UP"})

    assert "1 offre" in vResponse.text
    assert "Relance le 01/01/2020" in vResponse.text


def test_profile_page_and_offer_preparation(client):
    """Vérifie l'enregistrement du profil et la préparation affichée sur la fiche."""

    vEmpty = client.get("/offer?source=adzuna&id=new").text

    vSaved = client.post(
        "/profile",
        data={
            "skills": "Python, Django",
            "experiences": "Développeur | Python | Livré une API",
            "cv_variants": "CV Python | Python, Django",
        },
    )
    vOffer = client.get("/offer?source=adzuna&id=new").text

    assert "Renseignez d'abord vos compétences" in vEmpty
    assert "Profil enregistré : 2 compétence(s)" in vSaved.text
    assert "CV conseillé : <strong>CV Python</strong>" in vOffer
    assert "Brouillon de lettre de motivation" in vOffer
    assert "Pourquoi ce score ?" in vOffer
    assert client.post("/profile", data={"skills": "x" * 30000}).status_code == 400


def test_diploma_is_compared_to_the_offer(client):
    """Vérifie le diplôme du profil, son écart sur l'offre et le filtre « À ma portée »."""

    vDatabaseFile = app.dependency_overrides[get_database_file]()
    save_education_levels(vDatabaseFile, [(7, "adzuna", "new")])

    client.post(
        "/profile",
        data={
            "skills": "Java",
            "diploma": "Bac pro MEI\nBTS Maintenance industrielle",
            "education_level": "",
        },
    )
    vProfile = client.get("/profile").text
    vOffer = client.get("/offer?source=adzuna&id=new").text
    vList = client.get("/offers").text
    vReachable = client.get("/offers?reach=1").text

    assert "Bac pro MEI\nBTS Maintenance industrielle</textarea>" in vProfile
    assert "Niveau retenu : Bac+2 (BTS, DUT)" in vProfile
    assert "Bac+5 (master, ingénieur) · Diplôme probablement bloquant" in vOffer
    assert "Diplôme demandé au-dessus du vôtre" in vList
    assert "Diplôme demandé au-dessus du vôtre" not in vReachable


def test_preparation_sheet_page(client):
    """Vérifie la fiche imprimable : lien depuis l'offre, contenu échappé, 404."""

    client.post(
        "/profile",
        data={
            "skills": "Python",
            "experiences": "Développeur | Python | Livré une API",
        },
    )

    vOffer = client.get("/offer?source=adzuna&id=new").text
    vSheet = client.get("/offer/sheet?source=adzuna&id=new")
    vXss = client.get("/offer/sheet?source=hackernews&id=xss").text

    assert "/offer/sheet?source=adzuna&amp;id=new" in vOffer
    assert vSheet.status_code == 200
    assert "Exemples à citer" in vSheet.text
    assert "Python : Développeur : Livré une API" in vSheet.text
    assert "<script>alert(1)</script>" not in vXss
    assert client.get("/offer/sheet?source=adzuna&id=absent").status_code == 404


def test_spontaneous_draft_is_prepared_without_saving(client):
    """Vérifie le brouillon renvoyé à part, sans candidature enregistrée."""

    vBoard = client.get("/applications").text
    vDraft = client.get(
        "/applications/spontaneous/draft", params={"company": "Acme", "title": "Dev"}
    ).text

    assert "Préparer le message" in vBoard
    assert "candidature spontanée chez Acme pour un poste de Dev." in vDraft
    assert client.get("/applications").text == vBoard


def test_company_rules_from_offer_and_settings(client):
    """Vérifie l'avertissement, l'exclusion depuis la fiche et les listes des Paramètres."""

    vCreated = []

    for vTitle in ("Analyste Kotlin", "Architecte Rust"):
        vResponse = client.post(
            "/offers/new",
            data={"title": vTitle, "company": "Acme", "url": "https://a.example"},
            follow_redirects=False,
        )
        vCreated.append(vResponse.headers["location"])

    vFirstId = vCreated[0].rsplit("=", 1)[1]
    client.post(
        "/offer/application",
        data={"source": "manual", "id": vFirstId, "status": "APPLIED"},
    )

    vOffer = client.get(vCreated[1]).text

    assert "Déjà 1 candidature(s) dans cette entreprise : Analyste Kotlin" in vOffer

    vSecondId = vCreated[1].rsplit("=", 1)[1]
    vExcluded = client.post(
        "/offer/company",
        data={"source": "manual", "id": vSecondId, "kind": "excluded"},
        headers={"HX-Request": "true"},
    )

    assert vExcluded.headers["HX-Redirect"] == "/offers"
    assert "Architecte Rust" not in client.get("/offers").text

    vSettings = client.post(
        "/settings/companies", data={"excluded": "Acme", "preferred": "acme sas"}
    )

    assert vSettings.status_code == 400
    assert "à la fois exclue et privilégiée" in vSettings.text


def test_applications_page_and_status_change(client):
    """Vérifie les colonnes, les statistiques et le changement de statut."""

    vCreated = client.post(
        "/offers/new",
        data={
            "title": "Analyste Kotlin",
            "company": "Data SA",
            "url": "https://d.example",
        },
        follow_redirects=False,
    )
    vSourceId = vCreated.headers["location"].rsplit("=", 1)[1]
    client.post(
        "/offer/application",
        data={"source": "manual", "id": vSourceId, "status": "APPLIED"},
    )

    vPage = client.get("/applications").text

    assert 'Postulé <span class="muted">(1)</span>' in vPage
    assert "Analyste Kotlin" in vPage
    assert "data-autosubmit" in vPage

    vMoved = client.post(
        "/applications/status",
        data={"source": "manual", "id": vSourceId, "status": "INTERVIEW"},
        follow_redirects=False,
    )

    assert vMoved.status_code == 303
    assert (
        'Entretien <span class="muted">(1)</span>' in client.get("/applications").text
    )

    vRefused = client.post(
        "/applications/status",
        data={"source": "manual", "id": vSourceId, "status": "IGNORED"},
    )

    assert vRefused.status_code == 400


def test_attachments_upload_download_delete(client):
    """Vérifie l'envoi, le téléchargement et la suppression d'une pièce jointe."""

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

    vUploaded = client.post(
        "/offer/attachments",
        data={"source": "manual", "id": vSourceId},
        files={"file": ("../CV Rémi.pdf", b"%PDF", "application/pdf")},
        follow_redirects=False,
    )

    assert vUploaded.status_code == 303

    vPage = client.get(vOfferUrl).text
    vAttachmentId = re.search(r"/attachment\?id=(\d+)", vPage).group(1)

    assert "CV Rémi.pdf" in vPage

    vDownload = client.get(f"/attachment?id={vAttachmentId}")

    assert vDownload.content == b"%PDF"
    assert vDownload.headers["content-disposition"].startswith("attachment;")

    vRefused = client.post(
        "/offer/attachments",
        data={"source": "manual", "id": vSourceId},
        files={"file": ("outil.exe", b"MZ", "application/octet-stream")},
    )

    assert vRefused.status_code == 400

    client.post("/attachment/delete", data={"id": vAttachmentId})

    assert client.get(f"/attachment?id={vAttachmentId}").status_code == 404


def test_chatgpt_prompts_and_company_info(client, monkeypatch):
    """Vérifie les demandes affichées et la recherche d'entreprise qui les complète."""

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

    vPage = client.get(vOfferUrl).text

    assert 'data-copy="prompt-interview"' in vPage
    assert "Tu es recruteur pour le poste ci-dessous" in vPage

    monkeypatch.setattr(
        web_offer_detail,
        "lookup_company",
        lambda pName, _pHome: [
            {
                "name": "DATA SA",
                "siren": "123456789",
                "activity": "Information et communication",
                "activity_code": "62.01Z",
                "employees": "10 à 19 salariés",
                "category": "PME",
                "created": "2015",
                "city": "LILLE",
                "revenue": None,
                "active": True,
                "url": "https://annuaire.example/123456789",
            }
        ],
    )

    vInfo = client.get(f"/offer/company-info?source=manual&id={vSourceId}").text

    assert "Information et communication, PME, 10 à 19 salariés" in vInfo
    assert "https://annuaire.example/123456789" in vInfo
    assert 'id="prompt-company" class="prompt" hx-swap-oob="true"' in vInfo
    assert "Informations publiques déjà trouvées : DATA SA" in vInfo

    monkeypatch.setattr(
        web_offer_detail,
        "lookup_company",
        lambda pName, _pHome: (_ for _ in ()).throw(
            ValueError("Service indisponible.")
        ),
    )

    assert (
        "Service indisponible."
        in client.get(f"/offer/company-info?source=manual&id={vSourceId}").text
    )


def test_calendar_subscription_requires_valid_token(client):
    """Vérifie la création de l'adresse, sa lecture sans session et le refus du reste."""

    assert "Aucune adresse créée." in client.get("/settings").text

    vPage = client.post("/settings/calendar").text
    vUrl = re.search(r"http://testserver/calendar/[\w-]+\.ics", vPage).group(0)
    vPath = vUrl.removeprefix("http://testserver")

    client.cookies.clear()

    vCalendar = client.get(vPath)

    assert vCalendar.status_code == 200
    assert vCalendar.headers["content-type"].startswith("text/calendar")
    assert vCalendar.text.startswith("BEGIN:VCALENDAR")
    assert client.get("/calendar/mauvais-jeton.ics").status_code == 404


def test_profile_cv_import_prefills_without_saving(client):
    """Vérifie le pré-remplissage depuis un CV envoyé, sans enregistrement."""

    vResponse = client.post(
        "/profile/cv",
        files={"file": ("cv.txt", "Rémi Verhaeghe\nJava, SQL".encode(), "text/plain")},
    )

    assert vResponse.status_code == 200
    assert 'value="Rémi Verhaeghe"' in vResponse.text
    assert "--- Mon CV ---" in vResponse.text
    assert 'value=""' in client.get("/profile").text

    vRefused = client.post(
        "/profile/cv", files={"file": ("cv.odt", b"x", "application/octet-stream")}
    )

    assert vRefused.status_code == 400
    assert "formats acceptés" in vRefused.text


def test_week_follow_ups_on_applications_page(client):
    """Vérifie le brouillon de relance affiché et la relance notée."""

    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": datetime.now().date().isoformat(),
        },
    )

    vPage = client.get("/applications")
    vMissing = client.post(
        "/applications/follow-up", data={"source": "adzuna", "id": "old"}
    )
    vDone = client.post(
        "/applications/follow-up",
        data={"source": "adzuna", "id": "new"},
        follow_redirects=False,
    )

    assert "Relances de la semaine" in vPage.text
    assert "Objet : ma candidature au poste de" in vPage.text
    assert vMissing.status_code == 400
    assert vDone.status_code == 303
    assert "1 relance(s) déjà faite(s)" in client.get("/applications").text


def test_follow_up_is_sent_from_applications_page(client, monkeypatch):
    """Vérifie l'envoi d'une relance : formulaire, messages fixes, adresse gardée."""

    vSent = []

    monkeypatch.setattr(web_applications, "get_missing_email_settings", lambda: [])
    monkeypatch.setattr(
        "job.application_tracking.send_email",
        lambda pRecipient, pSubject, pText: vSent.append(pRecipient),
    )
    client.post(
        "/offer/application",
        data={
            "source": "adzuna",
            "id": "new",
            "status": "APPLIED",
            "follow_up_date": datetime.now().date().isoformat(),
        },
    )

    vForm = client.get("/applications").text
    vInvalid = client.post(
        "/applications/follow-up/send",
        data={"source": "adzuna", "id": "new", "recipient": "x", "draft": "Bonjour"},
        follow_redirects=False,
    )
    vSentPage = client.post(
        "/applications/follow-up/send",
        data={
            "source": "adzuna",
            "id": "new",
            "recipient": "rh@acme.fr",
            "draft": "Objet : relance\n\nBonjour",
        },
    )

    assert "Envoyer et noter la relance" in vForm
    assert vInvalid.headers["location"].endswith("?follow_up=invalid")
    assert "Relance envoyée et notée" in vSentPage.text
    assert vSent == ["rh@acme.fr"]

    def fail(*_pArgs):
        raise OSError("hors ligne")

    monkeypatch.setattr("job.application_tracking.send_email", fail)
    vFailed = client.post(
        "/applications/follow-up/send",
        data={
            "source": "adzuna",
            "id": "new",
            "recipient": "rh@acme.fr",
            "draft": "Objet : relance\n\nBonjour",
        },
        follow_redirects=False,
    )

    assert vFailed.headers["location"].endswith("?follow_up=failed")

    monkeypatch.setattr(
        web_applications, "get_missing_email_settings", lambda: ["GMAIL_ADDRESS"]
    )
    vUnconfigured = client.post(
        "/applications/follow-up/send",
        data={"source": "adzuna", "id": "new", "recipient": "rh@acme.fr"},
    )

    assert "Envoyer et noter la relance" not in vUnconfigured.text
    assert "renseignez GMAIL_ADDRESS" in vUnconfigured.text
    assert (
        client.post(
            "/applications/follow-up/send",
            data={"source": "adzuna", "id": "absente"},
        ).status_code
        == 400
    )


def test_settings_company_pages_saved_and_checked(client, monkeypatch):
    """Vérifie l'enregistrement des pages carrière suivies et leur vérification."""

    monkeypatch.delenv("LEVER_COMPANIES", raising=False)

    vSaved = client.post("/settings/company-pages", data={"lever": "qonto, inconnue"})

    assert "Listes enregistrées" in vSaved.text
    assert 'value="qonto, inconnue"' in vSaved.text

    def count(_pPlatform, pCompany):
        if pCompany == "inconnue":
            raise ValueError("404")
        return 7

    monkeypatch.setattr("job.company_pages.count_published_offers", count)

    vChecked = client.post(
        "/settings/company-pages/check", data={"lever": "qonto, inconnue"}
    )

    assert "Lever · qonto : 7 offre(s)" in vChecked.text
    assert "Lever · inconnue : introuvable" in vChecked.text


def test_recruiter_replies_are_read_and_handled(client, monkeypatch):
    """Vérifie la lecture des réponses Gmail, puis leur application ou leur oubli."""

    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)

    assert "À renseigner dans .env" in client.post("/applications/replies").text
    assert "Lire mes réponses Gmail" in client.get("/applications").text

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "old", "status": "APPLIED"},
    )
    monkeypatch.setattr(
        web_applications,
        "check_replies",
        lambda pDatabaseFile, pNow: [
            {
                "message_id": "<1>",
                "subject": "Votre candidature",
                "date": datetime(2026, 10, 22),
                "source": "adzuna",
                "source_id": "old",
                "title": "Développeur Java",
                "company": "Entreprise A",
                "current_status": "APPLIED",
                "status": "INTERVIEW",
            }
        ],
    )

    vReplies = client.post("/applications/replies").text
    vApplied = client.post(
        "/applications/replies/handle",
        data={
            "action": "apply",
            "message_id": "<1>",
            "source": "adzuna",
            "id": "old",
            "status": "INTERVIEW",
        },
    ).text
    vIgnored = client.post(
        "/applications/replies/handle",
        data={
            "action": "ignore",
            "message_id": "<2>",
            "source": "adzuna",
            "id": "old",
            "status": "REJECTED",
        },
    ).text

    assert "« Votre candidature »" in vReplies
    assert "Statut « Entretien » appliqué." in vApplied
    assert "Réponse ignorée." in vIgnored
    assert (
        get_application(app.dependency_overrides[get_database_file](), "adzuna", "old")[
            "status"
        ]
        == "INTERVIEW"
    )


def test_tailored_cv_is_downloaded(client):
    """Vérifie le CV adapté : refusé sans profil, puis fichier Word nommé d'après l'offre."""

    assert client.get("/offer/cv?source=adzuna&id=new").status_code == 400

    client.post("/profile", data={"skills": "Python, Django", "experiences": ""})
    vResponse = client.get("/offer/cv?source=adzuna&id=new")

    assert vResponse.status_code == 200
    assert vResponse.content[:2] == b"PK"
    assert "CV%20-%20Entreprise%20A" in vResponse.headers["content-disposition"]

    vPdf = client.get("/offer/cv?source=adzuna&id=new&format=pdf")

    assert vPdf.content[:4] == b"%PDF"
    assert vPdf.headers["content-type"] == "application/pdf"
    assert vPdf.headers["content-disposition"].endswith(".pdf")
    assert client.get("/offer/cv?source=adzuna&id=new&format=odt").status_code == 422
    assert (
        "Mots de l'annonce à reprendre"
        in client.get("/offer?source=adzuna&id=new").text
    )


def test_company_page_is_added_from_its_address(client, monkeypatch):
    """Vérifie l'ajout d'une entreprise depuis l'adresse de son site carrière."""

    monkeypatch.setattr(
        "job.company_pages.count_published_offers", lambda pPlatform, pCompany: 5
    )

    vAdded = client.post(
        "/settings/company-pages/url", data={"url": "https://jobs.lever.co/doctolib"}
    ).text
    vRefused = client.post(
        "/settings/company-pages/url", data={"url": "https://www.exemple.fr"}
    ).text

    assert "doctolib ajoutée : 5 offre(s)" in vAdded
    assert "Adresse non reconnue" in vRefused


def test_letter_is_downloaded_as_edited(client):
    """Vérifie la lettre téléchargée telle que modifiée dans la page."""

    vResponse = client.post(
        "/offer/letter",
        data={"source": "adzuna", "id": "new", "letter": "Bonjour,\nMa lettre"},
    )

    assert vResponse.status_code == 200
    assert vResponse.content[:2] == b"PK"
    assert "Lettre%20-%20Entreprise%20A" in vResponse.headers["content-disposition"]

    vPdf = client.post(
        "/offer/letter",
        data={"source": "adzuna", "id": "new", "letter": "Bonjour,", "format": "pdf"},
    )

    assert vPdf.content[:4] == b"%PDF"


def test_application_dossier_is_downloaded(client, monkeypatch):
    """Vérifie le dossier : refusé sans profil, puis PDF avec la lettre modifiée."""

    monkeypatch.setattr("job.application_dossier.lookup_company", lambda *pArgs: [])
    vData = {"source": "adzuna", "id": "new", "letter": "Bonjour,\nMa lettre"}

    assert client.post("/offer/dossier", data=vData).status_code == 400
    client.post("/profile", data={"skills": "Python, Django", "experiences": ""})

    assert "Dossier complet (PDF)" in client.get("/offer?source=adzuna&id=new").text

    vResponse = client.post("/offer/dossier", data=vData)
    vPages = PdfReader(io.BytesIO(vResponse.content)).pages

    assert vResponse.headers["content-type"] == "application/pdf"
    assert "Dossier%20-%20Entreprise%20A" in vResponse.headers["content-disposition"]
    assert len(vPages) == 4
    assert vPages[2].extract_text() == "Lettre de motivation\nBonjour,\nMa lettre"


def test_search_journal_is_downloaded(client):
    """Vérifie le téléchargement du journal de recherche pour une période."""

    client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "old", "status": "APPLIED"},
    )

    vResponse = client.get("/applications/journal.csv?start=2000-01-01&end=2100-01-01")

    assert vResponse.status_code == 200
    assert "Candidature envoyée" in vResponse.content.decode("utf-8-sig")
    assert "journal-recherche-20000101-21000101.csv" in (
        vResponse.headers["content-disposition"]
    )
    assert "Journal de recherche" in client.get("/applications").text


def test_spontaneous_application_is_added(client):
    """Vérifie la candidature spontanée ajoutée à la colonne Postulé."""

    vPage = client.post(
        "/applications/spontaneous",
        data={"company": "OVHcloud", "title": "Développeur Java"},
    ).text

    assert "Candidature spontanée · Développeur Java" in vPage
    assert client.post("/applications/spontaneous", data={}).status_code == 400


def test_status_history_is_shown_on_the_offer(client):
    """Vérifie l'historique des statuts dans le bloc de suivi de la fiche."""

    vPage = client.post(
        "/offer/application",
        data={"source": "adzuna", "id": "new", "status": "APPLIED"},
    ).text

    assert "Historique : Postulé le" in vPage
