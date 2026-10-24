"""Fiche de préparation d'entretien d'une offre, à imprimer ou à garder en PDF

La fiche rassemble sur une page ce qui sert le jour J : l'offre en bref,
l'adéquation au profil, les exemples à citer, les réponses préparées et les
questions déjà posées par l'entreprise.
"""

from html import escape

from job.application_tracking import describe_status_history
from job.agencies import load_interim_agencies
from job.interview_journal import collect_asked_questions, collect_company_questions
from job.offer_summary import build_offer_summary
from job.preparation import prepare_application
from job.presentation import format_date
from job.profile import is_profile_empty, load_profile
from job.star_answers import load_star_answers
from storage.job_applications import get_application, get_status_history


def describe_interview_date(pInterviewAt):
    """Retourne « 25/10/2026 à 14:00 », ou la date seule sans heure."""

    rText = format_date(pInterviewAt)

    if pInterviewAt and len(pInterviewAt) >= 16:
        rText += f" à {pInterviewAt[11:16]}"

    return rText


def build_header(pDatabaseFile, pOffer):
    """Retourne les lignes d'en-tête : entreprise, lieu, entretien, historique."""

    vApplication = get_application(pDatabaseFile, pOffer["source"], pOffer["source_id"])
    vHistory = describe_status_history(
        get_status_history(pDatabaseFile, pOffer["source"], pOffer["source_id"])
    )

    rLines = [
        vLine
        for vLine in (
            " · ".join(
                str(pOffer[vField])
                for vField in ("company", "location", "contract")
                if pOffer.get(vField)
            ),
            (
                f"Entretien le {describe_interview_date(vApplication['interview_at'])}"
                if vApplication and vApplication.get("interview_at")
                else ""
            ),
            f"Historique : {vHistory}" if vHistory else "",
            pOffer.get("url") or "",
        )
        if vLine
    ]

    return rLines


def build_preparation_sections(pPreparation):
    """Retourne les sections tirées de la préparation : (titre, lignes)."""

    vInterview = pPreparation["interview"]
    vMatch = pPreparation["match"]

    rSections = [
        (
            "Mon pitch",
            [
                f"30 secondes : {vInterview['pitch']['short']}",
                f"2 minutes : {vInterview['pitch']['long']}",
            ],
        ),
        (
            "Adéquation à mon profil",
            [
                (
                    f"{vMatch['score']} % des compétences repérées"
                    if vMatch["score"] is not None
                    else "Aucune compétence technique repérée"
                ),
                f"Couvertes : {', '.join(vMatch['covered']) or 'aucune'}",
                f"Manquantes : {pPreparation['missing_text']}",
            ]
            + (
                [f"CV conseillé : {pPreparation['cv']['name']}"]
                if pPreparation["cv"]
                else []
            ),
        ),
        (
            "Exemples à citer",
            [
                f"{vStrength['skill']} : {' ; '.join(vStrength['examples'])}"
                for vStrength in vInterview["strengths"]
                if vStrength["examples"]
            ],
        ),
        ("Points à préparer", vInterview["gaps"]),
        (
            "Questions classiques",
            [
                f"{vAnswer['question']} {vAnswer['hint']}"
                for vAnswer in vInterview["answers"]
            ],
        ),
        (
            "Mes réponses STAR",
            [
                f"{vAnswer['question']} {vAnswer['text']}"
                for vAnswer in vInterview["star"]
            ],
        ),
        (
            f"Questions pièges · {vInterview['tricky']['employer']}",
            [
                f"{vItem['question']} {vItem['hint']}"
                for vItem in vInterview["tricky"]["questions"]
            ],
        ),
        ("Questions à poser", vInterview["questions"]),
    ]

    return rSections


def build_preparation_sheet(pDatabaseFile, pOffer):
    """Construit la fiche : titre, en-tête et sections non vides (titre, lignes)."""

    vProfile = load_profile(pDatabaseFile)
    vSections = [(vName, [vText]) for vName, vText in build_offer_summary(pOffer)]

    if is_profile_empty(vProfile):
        vSections.append(
            ("Préparation", ["Remplissez la page Profil pour compléter la fiche."])
        )
    else:
        vSections += build_preparation_sections(
            prepare_application(
                vProfile,
                pOffer,
                load_star_answers(pDatabaseFile),
                collect_asked_questions(pDatabaseFile),
                load_interim_agencies(pDatabaseFile),
            )
        )

    vSections.append(
        (
            "Déjà posées par cette entreprise",
            [
                f"{vItem['question']} ({vItem['context']})"
                for vItem in collect_company_questions(pDatabaseFile, pOffer)
            ],
        )
    )

    rSheet = {
        "title": pOffer.get("title") or "Offre sans titre",
        "header": build_header(pDatabaseFile, pOffer),
        "sections": [(vName, vLines) for vName, vLines in vSections if vLines],
    }

    return rSheet


def render_sheet_html(pSheet):
    """Met la fiche en HTML simple, lisible par QTextDocument pour l'export PDF."""

    rHtml = (
        f"<h1>{escape(pSheet['title'])}</h1>"
        + "".join(f"<p>{escape(vLine)}</p>" for vLine in pSheet["header"])
        + "".join(
            f"<h2>{escape(vName)}</h2><ul>"
            + "".join(f"<li>{escape(vLine)}</li>" for vLine in vLines)
            + "</ul>"
            for vName, vLines in pSheet["sections"]
        )
    )

    return rHtml
