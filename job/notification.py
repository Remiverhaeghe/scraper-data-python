"""Contenu des e-mails de notification : nouvelles offres et relances à faire"""

from html import escape

from config import APPLICATION_NAME
from job.geocoding import describe_location
from job.presentation import (
    clean_missing_values,
    format_date,
    format_net_salary,
    safe_url,
)

# Au-delà, l'e-mail renvoie vers l'application plutôt que de tout lister
MAX_EMAIL_OFFERS = 20


def describe_offer(pOffer):
    """Résume une offre en une ligne : entreprise, lieu, salaire net, score et,
    s'il y a plusieurs recherches, celle qui l'a trouvée.
    """

    vScore = pOffer.get("match_score")

    rDetail = " · ".join(
        vPart
        for vPart in (
            pOffer.get("company"),
            describe_location(pOffer),
            format_net_salary(pOffer),
            f"correspondance {vScore} %" if vScore is not None else None,
            f"recherche « {pOffer['found_by']} »" if pOffer.get("found_by") else None,
        )
        if vPart
    )

    return rDetail


def describe_offers_by_search(pOffers):
    """Compte les offres par recherche, si plusieurs recherches en ont trouvé ;
    sinon, efface la recherche des offres, inutile à répéter sur chacune.
    """

    vCounts = {}

    for vOffer in pOffers:
        if vOffer.get("found_by"):
            vCounts[vOffer["found_by"]] = vCounts.get(vOffer["found_by"], 0) + 1

    if len(vCounts) < 2:
        for vOffer in pOffers:
            vOffer.pop("found_by", None)

        return ""

    rText = "Par recherche : " + ", ".join(
        f"{vName} {vCount}" for vName, vCount in vCounts.items()
    )

    return rText


def build_list_email(pSubject, pIntroduction, pItems, pDescribe, pMoreLabel):
    """Construit le texte et le HTML d'un e-mail listant des offres, liens compris.

    pDescribe résume un élément en une ligne ; au-delà de MAX_EMAIL_OFFERS, les
    éléments restants sont seulement comptés, sous le libellé pMoreLabel.
    """

    vShown = pItems[:MAX_EMAIL_OFFERS]
    vHidden = len(pItems) - len(vShown)
    vMore = f"Et {vHidden} autre(s) {pMoreLabel}, à consulter dans l'application."

    vTextLines = [pIntroduction, ""]
    vHtmlItems = []

    for vItem in vShown:
        vTitle = vItem.get("title") or "Titre non communiqué"
        vDetail = pDescribe(vItem)
        vUrl = safe_url(vItem.get("url"))

        vTextLines += [vTitle, vDetail, vUrl, ""]
        # Tout texte venant d'une offre est échappé : l'e-mail est lu en HTML.
        vHtmlItems.append(
            f'<li><a href="{escape(vUrl)}">{escape(vTitle)}</a>'
            f"<br><small>{escape(vDetail)}</small></li>"
        )

    vHtml = f"<p>{escape(pIntroduction)}</p><ul>{''.join(vHtmlItems)}</ul>"

    if vHidden:
        vTextLines.append(vMore)
        vHtml += f"<p>{escape(vMore)}</p>"

    rEmail = (pSubject, "\n".join(vTextLines), vHtml)

    return rEmail


def build_new_offers_email(pOffers, pSearchDescription):
    """Construit le sujet, le texte et le HTML de l'e-mail des nouvelles offres."""

    vOffers = [clean_missing_values(vOffer) for vOffer in pOffers]

    rEmail = build_list_email(
        f"{APPLICATION_NAME} : {len(vOffers)} nouvelle(s) offre(s)",
        f"Recherche planifiée : {pSearchDescription}",
        vOffers,
        describe_offer,
        "offre(s)",
    )

    return rEmail


def build_test_email():
    """Construit le sujet et le texte de l'e-mail de test."""

    rEmail = (
        f"{APPLICATION_NAME} : e-mail de test",
        "Les notifications de nouvelles offres sont correctement configurées.",
    )

    return rEmail


def describe_follow_up(pApplication):
    """Résume une relance en une ligne : entreprise, date prévue et relances faites."""

    vDetail = [
        pApplication.get("company"),
        f"relance prévue le {format_date(pApplication.get('follow_up_date'))}",
    ]

    if pApplication.get("follow_up_count"):
        vDetail.append(f"{pApplication['follow_up_count']} relance(s) déjà faite(s)")

    rDetail = " · ".join(vPart for vPart in vDetail if vPart)

    return rDetail


def build_follow_ups_email(pApplications):
    """Construit le sujet, le texte et le HTML de l'e-mail des relances à faire."""

    rEmail = build_list_email(
        f"{APPLICATION_NAME} : {len(pApplications)} relance(s) à faire",
        "Ces candidatures attendent une relance :",
        pApplications,
        describe_follow_up,
        "relance(s)",
    )

    return rEmail
