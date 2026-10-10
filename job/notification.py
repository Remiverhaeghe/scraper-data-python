"""Contenu des e-mails de notification des nouvelles offres"""

from html import escape

from config import APPLICATION_NAME
from job.presentation import clean_missing_values, format_net_salary, safe_url

# Au-delà, l'e-mail renvoie vers l'application plutôt que de tout lister
MAX_EMAIL_OFFERS = 20


def describe_offer(pOffer):
    """Résume une offre en une ligne : entreprise, lieu et salaire net."""

    rDetail = " · ".join(
        vPart
        for vPart in (
            pOffer.get("company"),
            pOffer.get("location"),
            format_net_salary(pOffer),
        )
        if vPart
    )

    return rDetail


def build_new_offers_email(pOffers, pSearchDescription):
    """Construit le sujet, le texte et le HTML de l'e-mail des nouvelles offres."""

    vOffers = [clean_missing_values(vOffer) for vOffer in pOffers]
    vShown = vOffers[:MAX_EMAIL_OFFERS]
    vHidden = len(vOffers) - len(vShown)

    vSubject = f"{APPLICATION_NAME} : {len(vOffers)} nouvelle(s) offre(s)"
    vIntroduction = f"Recherche planifiée : {pSearchDescription}"
    vMore = f"Et {vHidden} autre(s) offre(s), à consulter dans l'application."

    vTextLines = [vIntroduction, ""]
    vHtmlItems = []

    for vOffer in vShown:
        vTitle = vOffer.get("title") or "Titre non communiqué"
        vDetail = describe_offer(vOffer)
        vUrl = safe_url(vOffer.get("url"))

        vTextLines += [vTitle, vDetail, vUrl, ""]
        vHtmlItems.append(
            f'<li><a href="{escape(vUrl)}">{escape(vTitle)}</a>'
            f"<br><small>{escape(vDetail)}</small></li>"
        )

    vHtml = f"<p>{escape(vIntroduction)}</p><ul>{''.join(vHtmlItems)}</ul>"

    if vHidden:
        vTextLines.append(vMore)
        vHtml += f"<p>{escape(vMore)}</p>"

    rEmail = (vSubject, "\n".join(vTextLines), vHtml)

    return rEmail


def build_test_email():
    """Construit le sujet et le texte de l'e-mail de test."""

    rEmail = (
        f"{APPLICATION_NAME} : e-mail de test",
        "Les notifications de nouvelles offres sont correctement configurées.",
    )

    return rEmail
