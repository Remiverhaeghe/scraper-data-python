"""Import d'un CV : lecture du fichier et pré-remplissage du profil

Le nom, la présentation et les compétences sont repérés par des règles. Les
expériences, rédigées trop différemment d'un CV à l'autre, sont confiées à une
demande prête pour ChatGPT qui les remet au format du profil.
"""

import io
import re
import zipfile
from html import unescape
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from job.enrichment import detect_skills
from job.profile import split_list
from utils.logger import get_logger

logger = get_logger(__name__)

CV_EXTENSIONS = (".pdf", ".docx", ".txt")

MAX_CV_BYTES = 5 * 1024 * 1024

# Au-delà, le texte envoyé à ChatGPT est coupé : un CV tient en deux pages.
MAX_PROMPT_CV_LENGTH = 8000

# Un PDF de CV a une ou deux pages ; au-delà, le reste est ignoré.
MAX_PDF_PAGES = 5

# Un nom tient en quelques mots, sans chiffre ni arobase.
NAME_PATTERN = re.compile(r"^[^\W\d_][^\d@|:/]{1,48}$")
MAX_NAME_WORDS = 4
MAX_HEADLINE_LENGTH = 120

# Lignes à ne pas prendre pour une présentation : coordonnées, titres de rubrique
CONTACT_PATTERN = re.compile(r"@|\+?\d[\d .-]{7,}|https?://|linkedin", re.IGNORECASE)
SECTION_TITLES = {
    "profil",
    "contact",
    "compétences",
    "expériences",
    "expérience professionnelle",
    "formation",
    "langues",
    "centres d'intérêt",
}

DOCX_TEXT_FILE = "word/document.xml"
DOCX_PARAGRAPH_PATTERN = re.compile(r"</w:p>")
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


def read_docx(pContent):
    """Retourne le texte d'un document Word, un paragraphe par ligne."""

    with zipfile.ZipFile(io.BytesIO(pContent)) as vArchive:
        vXml = vArchive.read(DOCX_TEXT_FILE).decode("utf-8")

    rText = unescape(XML_TAG_PATTERN.sub("", DOCX_PARAGRAPH_PATTERN.sub("\n", vXml)))

    return rText


def read_pdf(pContent):
    """Retourne le texte des premières pages d'un PDF."""

    vReader = PdfReader(io.BytesIO(pContent))

    rText = "\n".join(
        vPage.extract_text() or "" for vPage in vReader.pages[:MAX_PDF_PAGES]
    )

    return rText


def read_cv_text(pFileName, pContent):
    """Retourne le texte d'un CV ; lève ValueError si le fichier est refusé."""

    vExtension = Path(str(pFileName or "")).suffix.lower()

    if vExtension not in CV_EXTENSIONS:
        raise ValueError("CV refusé : formats acceptés " + ", ".join(CV_EXTENSIONS))

    if not pContent:
        raise ValueError("CV refusé : le fichier est vide.")

    if len(pContent) > MAX_CV_BYTES:
        raise ValueError(f"CV refusé : {MAX_CV_BYTES // (1024 * 1024)} Mo au maximum.")

    try:
        if vExtension == ".pdf":
            rText = read_pdf(pContent)
        elif vExtension == ".docx":
            rText = read_docx(pContent)
        else:
            rText = pContent.decode("utf-8", errors="replace")

    except (PdfReadError, zipfile.BadZipFile, KeyError, ValueError) as vException:
        raise ValueError("CV illisible : le fichier semble endommagé.") from vException

    if not rText.strip():
        # Un PDF scanné ne contient que des images : aucun texte à lire.
        raise ValueError("CV sans texte lisible : un PDF scanné ne peut pas être lu.")

    return rText


def is_name(pLine):
    """Indique si une ligne ressemble à un prénom et un nom."""

    rName = bool(NAME_PATTERN.match(pLine)) and (
        1 < len(pLine.split()) <= MAX_NAME_WORDS
    )

    return rName


def is_headline(pLine):
    """Indique si une ligne peut servir de présentation."""

    rHeadline = (
        len(pLine) <= MAX_HEADLINE_LENGTH
        and len(pLine.split()) > 1
        and not CONTACT_PATTERN.search(pLine)
        and pLine.lower().strip(" :") not in SECTION_TITLES
    )

    return rHeadline


def extract_profile(pText):
    """Repère le nom, la présentation et les compétences en tête du CV."""

    vLines = [vLine.strip() for vLine in pText.splitlines() if vLine.strip()]

    # Le nom ouvre presque toujours le CV, suivi du titre visé.
    vName = vLines[0] if vLines and is_name(vLines[0]) else ""
    vHeadline = next(
        (vLine for vLine in vLines[1 if vName else 0 : 6] if is_headline(vLine)), ""
    )

    rProfile = {
        "name": vName,
        "headline": vHeadline,
        "skills": detect_skills(pText),
    }

    logger.info(
        "CV analysé : nom %s, présentation %s, %s compétence(s)",
        "trouvé" if vName else "absent",
        "trouvée" if vHeadline else "absente",
        len(rProfile["skills"]),
    )

    return rProfile


def merge_profile_texts(pTexts, pExtracted):
    """Complète les textes du formulaire sans écraser ce qui est déjà saisi."""

    rTexts = dict(pTexts)

    for vKey in ("name", "headline"):
        if not rTexts.get(vKey, "").strip():
            rTexts[vKey] = pExtracted[vKey]

    rTexts["skills"] = ", ".join(
        split_list(", ".join([rTexts.get("skills", ""), *pExtracted["skills"]]))
    )

    return rTexts


def build_cv_prompt(pText):
    """Retourne la demande ChatGPT qui convertit le CV au format du profil."""

    vText = pText.strip()

    if len(vText) > MAX_PROMPT_CV_LENGTH:
        vText = vText[:MAX_PROMPT_CV_LENGTH] + " […]"

    rPrompt = (
        "Voici mon CV. Convertis-le au format ci-dessous, sans rien inventer, "
        "sans phrase d'introduction ni de conclusion :\n"
        "1. Une expérience par ligne : Poste | compétences séparées par des "
        "virgules | réalisation marquante en une phrase.\n"
        "2. Puis, après une ligne vide, deux ou trois variantes de CV pertinentes, "
        "une par ligne : Nom du CV | compétences mises en avant.\n"
        "Exemple : Développeur backend | Java, Spring | Réduit de 40 % le temps "
        "de réponse\n"
        "Réponds en français.\n\n"
        f"--- Mon CV ---\n{vText}"
    )

    return rPrompt
