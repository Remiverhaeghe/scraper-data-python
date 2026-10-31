"""CV adapté à une offre et lettre de motivation, écrits au format Word (.docx)
ou PDF sans bibliothèque externe

Le CV reprend le profil tel quel, réordonné pour l'offre : compétences qu'elle
demande en tête, puis expériences qui les mobilisent le plus. Rien n'est inventé.
Le fichier n'est écrit qu'à la demande, à l'endroit choisi : il n'est pas gardé.
"""

import io
import re
import zipfile
from html import escape

from job.pdf_document import write_pdf
from job.preparation import get_offer_skills
from job.profile import split_list

# Caractères refusés dans un nom de fichier Windows
FILE_NAME_FORBIDDEN = re.compile(r'[\\/:*?"<>|]+')
MAX_FILE_NAME_LENGTH = 80

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELATIONSHIPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_START = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>"
)
DOCUMENT_END = "</w:body></w:document>"

# Tailles en demi-points : 16 pt pour le nom, 12 pour les titres, 10,5 pour le texte
NAME_SIZE = 32
HEADING_SIZE = 24
TEXT_SIZE = 21


def build_paragraph(pText, pSize=TEXT_SIZE, pBold=False, pSpaceBefore=0):
    """Retourne le XML d'un paragraphe Word d'un seul style."""

    vRunStyle = f'<w:rPr>{"<w:b/>" if pBold else ""}<w:sz w:val="{pSize}"/></w:rPr>'
    vSpacing = f'<w:pPr><w:spacing w:before="{pSpaceBefore}" w:after="60"/></w:pPr>'

    rXml = (
        f"<w:p>{vSpacing}<w:r>{vRunStyle}"
        f'<w:t xml:space="preserve">{escape(str(pText), quote=False)}</w:t></w:r></w:p>'
    )

    return rXml


def build_tailored_cv(pProfile, pOffer):
    """Retourne le contenu du CV réordonné pour l'offre : nom, titre, compétences, expériences."""

    vOfferSkills = get_offer_skills(pOffer)
    vWanted = {vSkill.lower() for vSkill in vOfferSkills}
    vSkills = list(pProfile.get("skills") or [])

    def count_matches(pExperience):
        """Compte les compétences de l'offre mobilisées par une expérience."""
        rCount = sum(
            1
            for vSkill in split_list(pExperience.get("skills") or "")
            if vSkill.lower() in vWanted
        )

        return rCount

    rCv = {
        "name": pProfile.get("name") or "",
        "headline": pProfile.get("headline") or "",
        "target": " · ".join(
            vPart for vPart in (pOffer.get("title"), pOffer.get("company")) if vPart
        ),
        # Ordre stable : à égalité, l'ordre du profil est gardé.
        "matching_skills": [vSkill for vSkill in vSkills if vSkill.lower() in vWanted],
        "other_skills": [vSkill for vSkill in vSkills if vSkill.lower() not in vWanted],
        "experiences": sorted(
            pProfile.get("experiences") or [], key=count_matches, reverse=True
        ),
    }

    return rCv


def build_cv_blocks(pCv):
    """Retourne le CV en blocs (texte, taille, gras, espace avant), communs au Word et au PDF."""

    rBlocks = [(pCv["name"], NAME_SIZE, True, 0)]

    if pCv["headline"]:
        rBlocks.append((pCv["headline"], HEADING_SIZE, False, 0))

    if pCv["target"]:
        rBlocks.append((f"Candidature : {pCv['target']}", TEXT_SIZE, False, 0))

    if pCv["matching_skills"]:
        rBlocks += [
            ("Compétences clés pour ce poste", HEADING_SIZE, True, 240),
            (", ".join(pCv["matching_skills"]), TEXT_SIZE, False, 0),
        ]

    if pCv["other_skills"]:
        rBlocks += [
            ("Autres compétences", HEADING_SIZE, True, 240),
            (", ".join(pCv["other_skills"]), TEXT_SIZE, False, 0),
        ]

    if pCv["experiences"]:
        rBlocks.append(("Expériences", HEADING_SIZE, True, 240))

    for vExperience in pCv["experiences"]:
        rBlocks.append((vExperience.get("title") or "", TEXT_SIZE, True, 120))

        for vField in ("skills", "achievement"):
            if vExperience.get(vField):
                rBlocks.append((f"• {vExperience[vField]}", TEXT_SIZE, False, 0))

    return rBlocks


def write_docx(pCv):
    """Retourne les octets d'un document Word contenant le CV."""

    rContent = write_document(
        [build_paragraph(*vBlock) for vBlock in build_cv_blocks(pCv)]
    )

    return rContent


def to_pdf_blocks(pBlocks):
    """Convertit des blocs Word (demi-points, vingtièmes de point) en points pour le PDF."""

    rBlocks = [
        (vText, vSize / 2, vBold, vSpaceBefore / 20)
        for vText, vSize, vBold, vSpaceBefore in pBlocks
    ]

    return rBlocks


def write_cv_pdf(pCv):
    """Retourne les octets d'un PDF contenant le CV, prêt à envoyer."""

    rContent = write_pdf(to_pdf_blocks(build_cv_blocks(pCv)), pCv["name"])

    return rContent


def write_document(pParagraphs):
    """Retourne les octets d'un document Word fait des paragraphes XML donnés."""

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr("[Content_Types].xml", CONTENT_TYPES)
        vArchive.writestr("_rels/.rels", RELATIONSHIPS)
        vArchive.writestr(
            "word/document.xml", DOCUMENT_START + "".join(pParagraphs) + DOCUMENT_END
        )

    rContent = vBuffer.getvalue()

    return rContent


def write_letter_docx(pText):
    """Retourne la lettre de motivation au format Word, un paragraphe par ligne."""

    rContent = write_document(
        [build_paragraph(vLine) for vLine in str(pText or "").splitlines()]
    )

    return rContent


def write_letter_pdf(pText):
    """Retourne la lettre de motivation en PDF, une ligne vide gardée entre paragraphes."""

    rContent = write_pdf(
        to_pdf_blocks(
            [(vLine, TEXT_SIZE, False, 0) for vLine in str(pText or "").splitlines()]
        ),
        "Lettre de motivation",
    )

    return rContent


def build_file_name(pOffer, pKind="CV", pExtension=".docx"):
    """Retourne un nom de fichier lisible et sûr pour un document lié à une offre."""

    vName = " - ".join(
        vPart for vPart in (pKind, pOffer.get("company"), pOffer.get("title")) if vPart
    )

    rFileName = (
        " ".join(FILE_NAME_FORBIDDEN.sub(" ", vName).split())[:MAX_FILE_NAME_LENGTH]
        + pExtension
    )

    return rFileName
