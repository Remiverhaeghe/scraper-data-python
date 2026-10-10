"""Tests du contenu des e-mails de notification"""

import math

from job.notification import MAX_EMAIL_OFFERS, build_new_offers_email, build_test_email


def build_offer(**pValues):
    """Construit une offre telle que la renvoie le traitement des sources."""

    rOffer = {
        "title": "Développeur Java",
        "company": "Acme",
        "location": "Lille",
        "url": "https://example.com/offre",
        "salary_net_monthly_min": 2500,
        "salary_net_monthly_max": math.nan,
    }

    rOffer.update(pValues)

    return rOffer


def test_build_new_offers_email():
    """Vérifie le sujet, le texte et le HTML, valeurs manquantes comprises."""

    vSubject, vText, vHtml = build_new_offers_email([build_offer()], "Java · Lille")

    assert vSubject == "JobBoard Perso : 1 nouvelle(s) offre(s)"
    assert "Recherche planifiée : Java · Lille" in vText
    assert "Acme · Lille · 2 500 €" in vText
    assert '<a href="https://example.com/offre">Développeur Java</a>' in vHtml
    assert "nan" not in vText


def test_build_new_offers_email_protects_html():
    """Vérifie l'échappement du texte et la neutralisation des liens dangereux."""

    _, _, vHtml = build_new_offers_email(
        [build_offer(title="<script>x</script>", url="javascript:alert(1)")], ""
    )

    assert "<script>" not in vHtml
    assert "&lt;script&gt;" in vHtml
    assert 'href="#"' in vHtml


def test_build_new_offers_email_limits_listed_offers():
    """Vérifie qu'au-delà de la limite, l'e-mail résume les offres restantes."""

    vSubject, vText, _ = build_new_offers_email(
        [
            build_offer(title=f"Offre {vIndex}")
            for vIndex in range(MAX_EMAIL_OFFERS + 3)
        ],
        "",
    )

    assert f"{MAX_EMAIL_OFFERS + 3} nouvelle(s)" in vSubject
    assert f"Offre {MAX_EMAIL_OFFERS}" not in vText
    assert "Et 3 autre(s) offre(s)" in vText


def test_build_test_email():
    """Vérifie l'e-mail de test."""

    vSubject, vText = build_test_email()

    assert "e-mail de test" in vSubject
    assert vText
