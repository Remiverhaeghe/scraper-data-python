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
from job.profile import EXPERIENCE_FIELDS, format_lines, split_list
from utils.logger import get_logger

logger = get_logger(__name__)

CV_EXTENSIONS = (".pdf", ".docx", ".txt")

# Une photo suffit à alourdir un CV : les images d'un document Word ne sont pas
# lues, seul son texte est plafonné (MAX_DOCX_TEXT_BYTES).
MAX_CV_BYTES = 20 * 1024 * 1024
MAX_DOCX_TEXT_BYTES = 10 * 1024 * 1024

# Au-delà, le texte envoyé à ChatGPT est coupé : un CV tient en deux pages.
MAX_PROMPT_CV_LENGTH = 8000

# Un PDF de CV a une ou deux pages ; au-delà, le reste est ignoré.
MAX_PDF_PAGES = 5

# Un nom tient en quelques mots, sans chiffre ni arobase, parmi les premières
# lignes : les coordonnées le précèdent parfois.
NAME_PATTERN = re.compile(r"^[^\W\d_][^\d@|:/]{1,48}$")
MAX_NAME_WORDS = 4
NAME_SEARCH_LINES = 10
MAX_HEADLINE_LENGTH = 120
MIN_SINGLE_WORD_HEADLINE = 6

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

# Période d'une expérience en début de ligne : « 2022 – aujourd'hui »,
# « mars 2019 - juin 2021 » ; une année seule ne suffit pas.
PERIOD_PATTERN = re.compile(
    r"^(?:[a-zéû]+\.?\s+)?(?:19|20)\d{2}\s*(?:-|–|—|à)\s*"
    r"(?:(?:[a-zéû]+\.?\s+)?(?:19|20)\d{2}|aujourd['’]hui|à ce jour|ce jour"
    r"|pr[ée]sent|actuellement|en cours)",
    re.IGNORECASE,
)
BULLET_PATTERN = re.compile(r"^[•●▪◦‣*·-]\s*")
TITLE_SEPARATOR_PATTERN = re.compile(r"\s[-–—]\s|\s(?:chez|at)\s", re.IGNORECASE)
MAX_TITLE_LENGTH = 80
MAX_ACHIEVEMENTS = 3

DOCX_TEXT_FILE = "word/document.xml"

# Une zone de texte Word est enregistrée deux fois : la version moderne et une
# copie de secours (mc:Fallback) pour les anciens logiciels, ignorée ici.
DOCX_FALLBACK_PATTERN = re.compile(r"<mc:Fallback>.*?</mc:Fallback>", re.DOTALL)

# Seuls les éléments w:t portent du texte : les positions des dessins, elles
# aussi écrites en texte dans le XML, sont ainsi écartées.
DOCX_TEXT_PATTERN = re.compile(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>|(<w:tab/>)|</w:p>")


def read_docx(pContent):
    """Retourne le texte d'un document Word, un paragraphe par ligne."""

    with zipfile.ZipFile(io.BytesIO(pContent)) as vArchive:
        if vArchive.getinfo(DOCX_TEXT_FILE).file_size > MAX_DOCX_TEXT_BYTES:
            raise ValueError("Texte du document trop volumineux.")

        vXml = vArchive.read(DOCX_TEXT_FILE).decode("utf-8")

    vParts = []

    for vMatch in DOCX_TEXT_PATTERN.finditer(DOCX_FALLBACK_PATTERN.sub("", vXml)):
        if vMatch.group(1) is not None:
            vParts.append(vMatch.group(1))
        else:
            vParts.append(" " if vMatch.group(2) else "\n")

    rText = unescape("".join(vParts))

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

    # Un mot d'une lettre trahit une mention comme « Permis B », une compétence
    # un intitulé comme « Développeur Java ».
    rName = (
        bool(NAME_PATTERN.match(pLine))
        and 1 < len(pLine.split()) <= MAX_NAME_WORDS
        and all(len(vWord) > 1 for vWord in pLine.split())
        and not detect_skills(pLine)
    )

    return rName


def is_headline(pLine):
    """Indique si une ligne peut servir de présentation."""

    # Un seul mot suffit pour un métier (« Électrotechnicien »), pas pour une
    # compétence comme « Python ».
    vSingleWord = len(pLine.split()) == 1
    rHeadline = (
        len(pLine) <= MAX_HEADLINE_LENGTH
        and (
            not vSingleWord
            or (
                pLine.isalpha()
                and len(pLine) >= MIN_SINGLE_WORD_HEADLINE
                and pLine.lower()
                not in {vSkill.lower() for vSkill in detect_skills(pLine)}
            )
        )
        and not CONTACT_PATTERN.search(pLine)
        and not PERIOD_PATTERN.match(pLine)
        and not BULLET_PATTERN.match(pLine)
        and pLine.lower().strip(" :") not in SECTION_TITLES
    )

    return rHeadline


def extract_profile(pText):
    """Repère le nom, la présentation et les compétences en tête du CV."""

    vLines = [vLine.strip() for vLine in pText.splitlines() if vLine.strip()]

    # Le nom ouvre le CV, parfois après les coordonnées, suivi du titre visé.
    vNameIndex = next(
        (
            vIndex
            for vIndex, vLine in enumerate(vLines[:NAME_SEARCH_LINES])
            if is_name(vLine)
        ),
        None,
    )
    vName = "" if vNameIndex is None else vLines[vNameIndex]
    vStart = 0 if vNameIndex is None else vNameIndex + 1
    vHeadline = next(
        (vLine for vLine in vLines[vStart : vStart + 5] if is_headline(vLine)), ""
    )

    rProfile = {
        "name": vName,
        "headline": vHeadline,
        "skills": detect_skills(pText),
        "experiences": extract_experiences(pText),
    }

    logger.info(
        "CV analysé : nom %s, présentation %s, %s compétence(s)",
        "trouvé" if vName else "absent",
        "trouvée" if vHeadline else "absente",
        len(rProfile["skills"]),
    )

    return rProfile


def find_experience_title(pLines):
    """Retourne l'intitulé d'une expérience : « Poste - Entreprise » de préférence."""

    vCandidates = [
        vLine
        for vLine in pLines
        if not BULLET_PATTERN.match(vLine) and len(vLine) <= MAX_TITLE_LENGTH
    ]

    rTitle = next(
        (vLine for vLine in vCandidates if TITLE_SEPARATOR_PATTERN.search(vLine)),
        vCandidates[0] if vCandidates else "",
    )

    return rTitle.rstrip(" :")


def extract_experiences(pText):
    """Repère les expériences : une période, un intitulé et des puces de réalisations.

    Le texte est découpé aux lignes de période (« 2022 – aujourd'hui ») ; une
    tranche sans puce, comme une formation, est ignorée. L'intitulé peut suivre
    les puces : les zones de texte d'un document Word mélangent l'ordre.
    """

    vLines = [vLine.strip() for vLine in pText.splitlines() if vLine.strip()]
    vStarts = [
        vIndex for vIndex, vLine in enumerate(vLines) if PERIOD_PATTERN.match(vLine)
    ]
    rExperiences = []

    for vPosition, vStart in enumerate(vStarts):
        vEnd = vStarts[vPosition + 1] if vPosition + 1 < len(vStarts) else len(vLines)
        vBlock = vLines[vStart + 1 : vEnd]
        vBullets = [
            BULLET_PATTERN.sub("", vLine)
            for vLine in vBlock
            if BULLET_PATTERN.match(vLine)
        ]

        if not vBullets:
            continue

        vPeriod = PERIOD_PATTERN.match(vLines[vStart]).group(0).strip()
        vTitle = find_experience_title(vBlock)

        rExperiences.append(
            {
                "title": f"{vTitle} ({vPeriod})" if vTitle else vPeriod,
                # Intitulé et puces seulement : un encadré voisin, intercalé par
                # les zones de texte, prêterait ses compétences à l'expérience.
                "skills": detect_skills(" ".join([vTitle, *vBullets])),
                "achievement": " ; ".join(vBullets[:MAX_ACHIEVEMENTS]),
            }
        )

    logger.info("CV : %s expérience(s) repérée(s)", len(rExperiences))

    return rExperiences


def merge_profile_texts(pTexts, pExtracted):
    """Complète les textes du formulaire sans écraser ce qui est déjà saisi."""

    rTexts = dict(pTexts)

    for vKey in ("name", "headline"):
        if not rTexts.get(vKey, "").strip():
            rTexts[vKey] = pExtracted[vKey]

    if not rTexts.get("experiences", "").strip() and pExtracted.get("experiences"):
        rTexts["experiences"] = format_lines(
            pExtracted["experiences"], EXPERIENCE_FIELDS
        )

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
