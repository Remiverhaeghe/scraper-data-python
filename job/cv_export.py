"""CV adapté à une offre, écrit au format Word (.docx) sans bibliothèque externe

Le CV reprend le profil tel quel, réordonné pour l'offre : compétences qu'elle
demande en tête, puis expériences qui les mobilisent le plus. Rien n'est inventé.
Le fichier n'est écrit qu'à la demande, à l'endroit choisi : il n'est pas gardé.
"""

import io
import re
import zipfile
from html import escape

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


def write_docx(pCv):
    """Retourne les octets d'un document Word contenant le CV."""

    vParagraphs = [build_paragraph(pCv["name"], NAME_SIZE, True)]

    if pCv["headline"]:
        vParagraphs.append(build_paragraph(pCv["headline"], HEADING_SIZE))

    if pCv["target"]:
        vParagraphs.append(build_paragraph(f"Candidature : {pCv['target']}"))

    if pCv["matching_skills"]:
        vParagraphs += [
            build_paragraph("Compétences clés pour ce poste", HEADING_SIZE, True, 240),
            build_paragraph(", ".join(pCv["matching_skills"])),
        ]

    if pCv["other_skills"]:
        vParagraphs += [
            build_paragraph("Autres compétences", HEADING_SIZE, True, 240),
            build_paragraph(", ".join(pCv["other_skills"])),
        ]

    if pCv["experiences"]:
        vParagraphs.append(build_paragraph("Expériences", HEADING_SIZE, True, 240))

    for vExperience in pCv["experiences"]:
        vParagraphs.append(
            build_paragraph(vExperience.get("title") or "", TEXT_SIZE, True, 120)
        )

        for vField in ("skills", "achievement"):
            if vExperience.get(vField):
                vParagraphs.append(build_paragraph(f"• {vExperience[vField]}"))

    vBuffer = io.BytesIO()

    with zipfile.ZipFile(vBuffer, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr("[Content_Types].xml", CONTENT_TYPES)
        vArchive.writestr("_rels/.rels", RELATIONSHIPS)
        vArchive.writestr(
            "word/document.xml", DOCUMENT_START + "".join(vParagraphs) + DOCUMENT_END
        )

    rContent = vBuffer.getvalue()

    return rContent


def build_cv_file_name(pOffer):
    """Retourne un nom de fichier lisible et sûr pour le CV adapté à une offre."""

    vName = " - ".join(
        vPart for vPart in ("CV", pOffer.get("company"), pOffer.get("title")) if vPart
    )

    rFileName = (
        " ".join(FILE_NAME_FORBIDDEN.sub(" ", vName).split())[:MAX_FILE_NAME_LENGTH]
        + ".docx"
    )

    return rFileName
