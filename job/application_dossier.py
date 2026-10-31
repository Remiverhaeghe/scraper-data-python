"""Dossier de candidature en un PDF : offre, CV adapté, lettre, entreprise, questions

Le dossier rassemble ce qui existe déjà ailleurs, une partie par page : le
résumé de l'offre, le CV réordonné pour elle, la lettre (celle modifiée à
l'écran quand elle est fournie), la fiche de l'entreprise tirée de l'annuaire
public et les questions à poser en entretien. Rien n'est gardé : le fichier est
produit à la demande.
"""

from datetime import date

from job.company_info import lookup_company
from job.cv_export import build_cv_blocks, build_tailored_cv, to_pdf_blocks
from job.offer_summary import build_offer_summary
from job.pdf_document import PAGE_BREAK, write_pdf
from job.preparation import prepare_application
from job.presentation import can_lookup_company, clean_missing_values
from utils.logger import get_logger

logger = get_logger(__name__)

TITLE_SIZE = 16
HEADING_SIZE = 12
TEXT_SIZE = 10.5
PARTS = ("CV adapté", "Lettre de motivation", "Fiche entreprise", "Questions à poser")


def heading(pText, pSpaceBefore=12):
    """Retourne le bloc d'un titre de partie."""

    rBlock = (pText, HEADING_SIZE, True, pSpaceBefore)

    return rBlock


def text(pText, pSpaceBefore=0):
    """Retourne le bloc d'un paragraphe."""

    rBlock = (pText, TEXT_SIZE, False, pSpaceBefore)

    return rBlock


def describe_company_lines(pCompany):
    """Retourne les lignes de la fiche entreprise, sans les informations absentes."""

    vNearest = pCompany.get("nearest")

    rLines = [
        f"{vLabel} : {vValue}"
        for vLabel, vValue in (
            ("Activité", pCompany.get("activity")),
            ("Catégorie", pCompany.get("category")),
            ("Effectif", pCompany.get("employees")),
            ("Création", pCompany.get("created")),
            ("Siège", (pCompany.get("city") or "").title()),
            ("Chiffre d'affaires", pCompany.get("revenue")),
            ("Établissements ouverts", pCompany.get("sites")),
            (
                "Le plus proche",
                vNearest
                and f"{vNearest['city']}, {vNearest['distance_km']} km de chez vous",
            ),
            ("Fiche publique", pCompany.get("url")),
        )
        if vValue
    ]

    if not pCompany.get("active", True):
        rLines.append("Entreprise fermée d'après l'annuaire.")

    return rLines


def build_company_blocks(pOffer, pHome, pLookup):
    """Retourne la fiche de l'entreprise, ou la raison de son absence."""

    rBlocks = [heading(PARTS[2], 0)]

    if not can_lookup_company(pOffer):
        rBlocks.append(
            text("L'annuaire public ne décrit que les entreprises françaises.")
        )
        return rBlocks

    try:
        vCompanies = pLookup(pOffer.get("company"), pHome)

    except ValueError as vError:
        rBlocks.append(text(f"Fiche indisponible : {vError}"))
        return rBlocks

    if not vCompanies:
        rBlocks.append(text("Aucune entreprise trouvée sous ce nom dans l'annuaire."))
        return rBlocks

    # Le premier résultat est le plus probable, pas une certitude
    rBlocks += [
        (vCompanies[0]["name"], TEXT_SIZE, True, 0),
        *(text(vLine) for vLine in describe_company_lines(vCompanies[0])),
        text("Premier résultat de l'annuaire public sous ce nom : à vérifier.", 6),
    ]

    return rBlocks


def build_dossier_blocks(
    pProfile, pOffer, pLetter=None, pHome=None, pToday=None, *, pLookup=None
):
    """Retourne les blocs du dossier, une partie par page.

    pLookup remplace la recherche dans l'annuaire public, pour les tests.
    """

    # Une offre lue en base porte des valeurs manquantes en NaN
    pOffer = clean_missing_values(pOffer)
    vPreparation = prepare_application(pProfile, pOffer)
    vToday = pToday or date.today()
    vLetter = vPreparation["letter"] if pLetter is None else pLetter
    vTarget = " · ".join(
        vPart for vPart in (pOffer.get("title"), pOffer.get("company")) if vPart
    )

    rBlocks = [
        ("Dossier de candidature", TITLE_SIZE, True, 0),
        (vTarget, HEADING_SIZE, False, 0),
        text(f"Préparé le {vToday.strftime('%d/%m/%Y')} pour {pProfile.get('name')}"),
        text(f"Annonce : {pOffer.get('url')}" if pOffer.get("url") else ""),
        heading("Sommaire"),
        *(text(f"{vIndex}. {vPart}") for vIndex, vPart in enumerate(PARTS, 1)),
        heading("L'offre en bref"),
        *(
            vBlock
            for vName, vText in build_offer_summary(pOffer)
            for vBlock in ((vName, TEXT_SIZE, True, 6), text(vText))
        ),
        (PAGE_BREAK, TEXT_SIZE, False, 0),
        *to_pdf_blocks(build_cv_blocks(build_tailored_cv(pProfile, pOffer))),
        (PAGE_BREAK, TEXT_SIZE, False, 0),
        heading(PARTS[1], 0),
        *(text(vLine) for vLine in str(vLetter or "").splitlines()),
        (PAGE_BREAK, TEXT_SIZE, False, 0),
        *build_company_blocks(pOffer, pHome, pLookup or lookup_company),
        heading(PARTS[3], 18),
        *(
            text(f"• {vQuestion}")
            for vQuestion in vPreparation["interview"]["questions"]
        ),
    ]

    logger.info(
        "Dossier de candidature préparé pour %s/%s",
        pOffer.get("source"),
        pOffer.get("source_id"),
    )

    return rBlocks


def write_dossier_pdf(pProfile, pOffer, pLetter=None, pHome=None, pToday=None):
    """Retourne les octets du dossier de candidature en PDF."""

    rContent = write_pdf(
        build_dossier_blocks(pProfile, pOffer, pLetter, pHome, pToday),
        f"Dossier de candidature · {pOffer.get('title') or ''}",
    )

    return rContent
