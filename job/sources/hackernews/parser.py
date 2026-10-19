"""Transformation des offres Hacker News vers le format Job commun"""

import re

import pandas as pd

from job.csv_schema import JOB_COLUMNS
from utils.helpers import html_to_text
from utils.logger import get_logger

logger = get_logger(__name__)

ITEM_URL = "https://news.ycombinator.com/item?id={id}"

# Séparateurs usuels de la ligne d'en-tête : « Entreprise | Poste | Lieu »
HEADER_SEPARATOR = re.compile(r"\s+[|–—]\s+")

REMOTE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)

# Lien vers le site de l'entreprise, parfois entre parenthèses, après son nom
COMPANY_URL_PATTERN = re.compile(r"\(?\s*https?://[^\s)]+\s*\)?")

# Les segments sont reconnus par leur début ou leur forme complète : un poste
# comme « Contract Manager » ne doit pas être pris pour un type de contrat.
URL_SEGMENT = re.compile(r"^(https?://|www\.)\S+$|^[\w-]+(\.[\w-]+)+(/\S*)?$")
WORK_MODE_SEGMENT = re.compile(
    r"^(remote|on-?site|hybrid|in[\s-]office)\b", re.IGNORECASE
)
EMPLOYMENT_WORDS = r"(full|part)[\s-]?time|contract(or)?|intern(ship)?|freelance"
EMPLOYMENT_SEGMENT = re.compile(
    rf"^(full|part)[\s-]?time\b|^({EMPLOYMENT_WORDS})([\s,/&+]+(or\s+)?"
    rf"({EMPLOYMENT_WORDS}))*(\s*\(.*\))?$",
    re.IGNORECASE,
)
SALARY_SEGMENT = re.compile(r"[$€£]\s?\d|\d\s?k\b", re.IGNORECASE)
VISA_SEGMENT = re.compile(r"\bvisa\b", re.IGNORECASE)

# Mot qui désigne un poste : sert à reconnaître un titre parmi d'autres segments
ROLE_PATTERN = re.compile(
    r"\b(engineers?|developers?|designers?|managers?|scientists?|analysts?"
    r"|architects?|leads?|devops|sre|interns?|researchers?|recruiters?"
    r"|consultants?|administrators?|technicians?|cto|head of)\b",
    re.IGNORECASE,
)

# Lieu placé là où on attend le poste : « San Francisco, CA (Onsite) »
LOCATION_HINT = re.compile(
    r"\((remote|on-?site|hybrid|in[\s-](office|person))[^)]*\)"
    r"|\b(on-?site|in[\s-]person)\b",
    re.IGNORECASE,
)

# En-tête rédigé en lignes étiquetées : « Company: … », « Location: … »
LABELED_LINE = re.compile(
    r"^\s*(company|location|role|roles|position|positions|title|job"
    r"|salary|compensation)\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
LABELED_FIELDS = {
    "company": "company",
    "location": "location",
    "role": "title",
    "roles": "title",
    "position": "title",
    "positions": "title",
    "title": "title",
    "job": "title",
    "salary": "salary",
    "compensation": "salary",
}

# Annonce sans séparateur mais explicite : « We're hiring… », « X is hiring… »
HIRING_PATTERN = re.compile(r"\b(we'?re|we are|is|are)\s+hiring\b", re.IGNORECASE)

# Longueur maximale d'une ligne du texte reprise comme titre de poste
MAX_ROLE_LINE_LENGTH = 100

# Après le poste, un segment plus long est le début du texte de l'annonce, collé à
# l'en-tête faute de saut de paragraphe.
MAX_SEGMENT_LENGTH = 80


def split_header(pText):
    """Sépare la première ligne d'une offre, du reste de son contenu."""

    vParts = (pText or "").split("<p>", 1)

    vHeader = html_to_text(vParts[0]) or ""
    vBody = vParts[1] if len(vParts) > 1 else ""

    rHeader = (vHeader, vBody)

    return rHeader


def classify_segments(pSegments):
    """Répartit les segments de l'en-tête entre poste, lieu, contrat et salaire."""

    vTitles = []
    vLocations = []
    vEmployments = []
    vSalaries = []

    for vSegment in pSegments:
        if URL_SEGMENT.match(vSegment) or VISA_SEGMENT.search(vSegment):
            continue

        if vTitles and len(vSegment) > MAX_SEGMENT_LENGTH:
            continue

        if WORK_MODE_SEGMENT.match(vSegment) or (
            LOCATION_HINT.search(vSegment) and not ROLE_PATTERN.search(vSegment)
        ):
            vLocations.append(vSegment)
        elif EMPLOYMENT_SEGMENT.match(vSegment):
            vEmployments.append(vSegment)
        elif SALARY_SEGMENT.search(vSegment):
            vSalaries.append(vSegment)
        elif not vTitles:
            vTitles.append(vSegment)
        else:
            vLocations.append(vSegment)

    rSegments = {
        "title": vTitles[0] if vTitles else None,
        "location": " | ".join(vLocations) or None,
        "employment": " | ".join(vEmployments) or None,
        "salary": " | ".join(vSalaries) or None,
    }

    return rSegments


def parse_header(pHeader):
    """Extrait de l'en-tête l'entreprise, le poste, le lieu, le contrat et le salaire.

    Sert aussi à la reprise des offres enregistrées avant ce découpage.
    """

    vSegments = HEADER_SEPARATOR.split(pHeader)
    vDetails = classify_segments(vSegments[1:])

    rHeader = {
        **vDetails,
        "company": COMPANY_URL_PATTERN.sub("", vSegments[0]).strip() or None,
        # Sans séparateur, l'en-tête est une phrase libre qui tient lieu de titre.
        "title": (vDetails["title"] or (pHeader if len(vSegments) == 1 else ""))[:200]
        or None,
        "location": (vDetails["location"] or "")[:200] or None,
    }

    return rHeader


def parse_labeled_lines(pText):
    """Retourne les champs d'un en-tête en lignes « Étiquette: valeur »."""

    rFields = {}

    for vLabel, vValue in LABELED_LINE.findall(pText):
        rFields.setdefault(LABELED_FIELDS[vLabel.lower()], vValue[:200])

    return rFields


def find_role_line(pText):
    """Retourne la première ligne courte du texte qui nomme un poste, ou None."""

    rLine = next(
        (
            vLine.strip()
            for vLine in pText.splitlines()
            if 0 < len(vLine.strip()) <= MAX_ROLE_LINE_LENGTH
            and ROLE_PATTERN.search(vLine)
        ),
        None,
    )

    return rLine


def is_job_post(pComment):
    """Indique si un commentaire de premier niveau est une offre d'emploi.

    Une offre suit la convention « Entreprise | Poste | Lieu », ou étiquette
    ses lignes, ou annonce explicitement un recrutement. Les autres messages
    (remarques sur le fil, candidats qui se présentent, publicités) sont écartés.
    """

    vHeader, _ = split_header(pComment.get("text"))

    rJobPost = bool(
        len(HEADER_SEPARATOR.split(vHeader)) > 1
        or {"company", "location"} & set(parse_labeled_lines(vHeader))
        or HIRING_PATTERN.search(vHeader)
    )

    return rJobPost


def parse_job(pComment):
    """Transforme un commentaire du fil « Who is hiring? » en dictionnaire Job.

    Les offres sont rédigées en texte libre : seule la convention de la
    première ligne permet d'en extraire l'entreprise et le poste.
    """

    vHeader, vBody = split_header(pComment.get("text"))
    # Une ligne par paragraphe : html_to_text les réunirait en une seule.
    vBodyLines = "\n".join(
        html_to_text(vParagraph) or "" for vParagraph in vBody.split("<p>")
    )
    vDetails = parse_header(vHeader)
    vLabeled = parse_labeled_lines(f"{vHeader}\n{vBodyLines}")

    # En-tête étiqueté : les étiquettes remplacent le découpage par séparateurs.
    if {"company", "location"} & set(parse_labeled_lines(vHeader)):
        vDetails = {
            **vDetails,
            "title": vLabeled.get("title"),
            "company": vLabeled.get("company"),
            "location": vLabeled.get("location"),
            "salary": vLabeled.get("salary") or vDetails["salary"],
        }

    # Poste absent de l'en-tête : il est souvent nommé en tête du texte.
    if not vDetails["title"]:
        vDetails["title"] = vLabeled.get("title") or find_role_line(vBodyLines)

    vJob = {
        # Identification
        "title": vDetails["title"],
        "company": vDetails["company"],
        "company_id": None,
        "source": "hackernews",
        "source_id": str(pComment.get("id")),
        "url": ITEM_URL.format(id=pComment.get("id")),
        # Localisation : mentionnée librement dans l'en-tête
        "location": vDetails["location"],
        "city": None,
        "postal_code": None,
        "country": None,
        "distance_km": None,
        # Contrat
        "contract": None,
        "contract_type": vDetails["employment"],
        "employment_type": vDetails["employment"],
        # Rémunération
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "salary_label": vDetails["salary"],
        # Télétravail
        "remote": True if REMOTE_PATTERN.search(vHeader) else None,
        "remote_days": None,
        "remote_type": None,
        # Transport
        "nearest_metro": None,
        "metro_distance_km": None,
        # Dates fournies par Hacker News
        "date": pComment.get("created_at"),
        "published_at": pComment.get("created_at"),
        "updated_at": None,
        # Dates gérées par notre application
        "scraped_at": None,
        "first_seen_at": None,
        # Contenu
        "description": html_to_text(vBody),
        "missions": None,
        "requirements": None,
        "education": None,
        "skills": None,
        # Informations complémentaires
        "department": None,
        "experience_level": None,
        "job_type": None,
    }

    rJob = vJob

    return rJob


def parse_jobs(pComments):
    """Transforme les offres d'un fil en DataFrame normalisé.

    Les commentaires supprimés n'ont pas de texte et sont ignorés, comme ceux
    qui n'ont pas la forme d'une offre.
    """

    vComments = [vComment for vComment in pComments if vComment.get("text")]
    vPosts = [vComment for vComment in vComments if is_job_post(vComment)]

    if len(vPosts) < len(vComments):
        logger.info(
            "Hacker News : %s commentaire(s) écarté(s), sans forme d'offre",
            len(vComments) - len(vPosts),
        )

    vJobs = [parse_job(vComment) for vComment in vPosts]

    vDataFrame = pd.DataFrame(vJobs, columns=JOB_COLUMNS)

    rDataFrame = vDataFrame

    return rDataFrame
