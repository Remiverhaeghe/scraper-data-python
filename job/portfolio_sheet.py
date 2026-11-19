"""Fiche « projet portfolio » : un projet public présenté pour une candidature

La fiche reprend les faits du README (job/portfolio_projects.py) sans rien
ajouter. Elle donne aussi deux textes prêts à coller : une ligne pour la rubrique
Projets du CV et un paragraphe pour la lettre de motivation.
"""

from job.pdf_document import write_pdf
from job.portfolio_projects import CHECKED_ON, THEMES, get_facts
from utils.logger import get_logger

logger = get_logger(__name__)

# Tailles des blocs du PDF : titre, intertitre, texte
TITLE_SIZE = 18
HEADING_SIZE = 13
BODY_SIZE = 10.5


def build_cv_line(pProject):
    """Retourne la ligne du projet pour la rubrique Projets du CV."""

    rLine = (
        f"{pProject['name']} ({', '.join(pProject['stack'])}) : "
        f"{pProject['summary']} Code public : {pProject['url']}"
    )

    return rLine


def build_letter_paragraph(pProject):
    """Retourne le paragraphe de lettre de motivation qui présente le projet."""

    # Le fait de qualité le plus parlant est le premier du thème tests : il
    # montre une méthode, pas seulement un résultat.
    vProof = (get_facts(pProject, "tests") or get_facts(pProject, "architecture"))[:1]

    rParagraph = " ".join(
        [
            f"Sur mon temps personnel, j'ai développé {pProject['name']}, "
            f"{pProject['letter']}.",
            *vProof,
            f"Le code est public : {pProject['url']}.",
        ]
    )

    return rParagraph


def build_portfolio_sheet(pProject):
    """Retourne la fiche d'un projet : titre, rubriques et textes à reprendre."""

    vSections = [
        ("En bref", [pProject["summary"]]),
        ("Technologies", [", ".join(pProject["stack"])]),
        ("Ce que fait le projet", list(pProject["features"])),
    ]

    for vTheme, vLabel in THEMES.items():
        vFacts = get_facts(pProject, vTheme)

        if vFacts:
            vSections.append((vLabel, vFacts))

    vSections.append(
        (
            "À montrer dans le code",
            [f"{vPath} : {vRole}" for vPath, vRole in pProject["code_tour"]],
        )
    )

    if pProject["next"]:
        vSections.append(("Suite prévue", list(pProject["next"])))

    rSheet = {
        "id": pProject["id"],
        "title": pProject["name"],
        "subtitle": pProject["kind"],
        "url": pProject["url"],
        "sections": vSections,
        "cv_line": build_cv_line(pProject),
        "letter_paragraph": build_letter_paragraph(pProject),
        "source": (
            f"Faits tirés du README public ({pProject['url']}), relevés le "
            f"{CHECKED_ON[8:10]}/{CHECKED_ON[5:7]}/{CHECKED_ON[:4]}. "
            f"Licence : {pProject['license']}."
        ),
    }

    return rSheet


def render_sheet_text(pSheet):
    """Retourne la fiche en texte brut, à coller dans un mail ou un formulaire."""

    vLines = [f"{pSheet['title']} - {pSheet['subtitle']}", pSheet["url"], ""]

    for vHeading, vItems in pSheet["sections"]:
        vLines.append(vHeading)
        vLines.extend(f"- {vItem}" for vItem in vItems)
        vLines.append("")

    vLines.append(pSheet["source"])

    rText = "\n".join(vLines)

    return rText


def write_sheet_pdf(pSheet):
    """Retourne la fiche en PDF A4, à joindre à une candidature."""

    vBlocks = [
        (pSheet["title"], TITLE_SIZE, True, 0),
        (f"{pSheet['subtitle']} · {pSheet['url']}", BODY_SIZE, False, 4),
    ]

    for vHeading, vItems in pSheet["sections"]:
        vBlocks.append((vHeading, HEADING_SIZE, True, 14))
        vBlocks.extend((f"• {vItem}", BODY_SIZE, False, 3) for vItem in vItems)

    vBlocks.append((pSheet["source"], BODY_SIZE - 1.5, False, 16))

    rContent = write_pdf(vBlocks, f"{pSheet['title']} - fiche projet")

    logger.info("Fiche projet exportée en PDF : %s", pSheet["title"])

    return rContent
