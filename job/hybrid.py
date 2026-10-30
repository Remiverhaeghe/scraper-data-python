"""Offres à double profil : maintenance industrielle et informatique

Certains postes demandent les deux mondes : informatique industrielle, MES,
supervision, administration de GMAO, automatisme avec développement. Ce profil
est rare chez les candidats ; l'offre est signalée, filtrable, et la
préparation met ce double parcours en avant.

Un terme « pont » (MES, SCADA, informatique industrielle…) suffit. Sinon, il
faut à la fois un terme industriel et au moins deux termes informatiques
distincts : « maîtrise de l'outil informatique » ne fait pas un double profil.
"""

import re
from functools import lru_cache

# Termes qui désignent à eux seuls un poste entre l'atelier et l'informatique :
# (libellé affiché, mots déclencheurs en minuscules, motif sur le texte en minuscules)
BRIDGE_TERMS = (
    (
        "Informatique industrielle",
        ("informatique industrielle",),
        r"informatique industrielle",
    ),
    (
        "Supervision",
        ("scada", "wincc", "pcvue", "supervision industrielle"),
        r"\bscada\b|\bwincc\b|\bpcvue\b|supervision industrielle",
    ),
    ("Historian", ("historian", "pi system"), r"\bhistorian\b|\bpi system\b"),
    ("OPC UA", ("opc",), r"\bopc[ -]?ua\b"),
    ("IIoT", ("iiot", "4.0", "jumeau"), r"\biiot\b|\bindustrie 4\.0|jumeau numérique"),
    (
        "Cybersécurité OT",
        ("62443", "cybersécurité industrielle"),
        r"cybersécurité industrielle|\biec 62443\b",
    ),
    (
        "Administration GMAO",
        ("gmao",),
        r"(?:administrat\w*|paramétrage|référent|déploiement|chef de projet)"
        r" (?:de la |d'une |de |la )?gmao",
    ),
    ("SAP PM", ("sap pm",), r"\bsap pm\b"),
    ("MES", ("manufacturing execution",), r"manufacturing execution"),
)

# MES s'écrit en capitales : en minuscules, c'est un possessif. Seul, le sigle
# veut aussi dire « mise en service » : il faut un contexte logiciel.
MES_PATTERN = re.compile(
    r"\b(?:[Ss]ystèmes?|[Ss]olutions?|[Ll]ogiciels?|[Oo]utils?|[Pp]rojets?|"
    r"[Aa]pplications?|[Ii]ntégration|[Dd]éploiement) (?:de |d'un |du )?MES\b"
    r"|\bMES ?/ ?MOM\b|\bMES \(|\bMES/ERP\b|\bERP ?/ ?MES\b"
)

# Termes du monde industriel et du monde informatique, comptés séparément
INDUSTRY_TERMS = (
    (
        "Maintenance",
        ("maintenance",),
        r"maintenance (?:industrielle|curative|préventive|des équipements"
        r"|électrique|mécanique)|technicien de maintenance",
    ),
    (
        "Automatisme",
        ("automat", "plc", "tia portal", "grafcet"),
        r"automates? programmables?|\bautomaticien|\bautomatisme"
        r"|\bplc\b|tia portal|\bgrafcet\b",
    ),
    ("Électrotechnique", ("électrotechni",), r"électrotechni"),
    (
        "Production",
        ("production", "usine", "atelier"),
        r"ligne de production|site de production|\busine\b|atelier de production",
    ),
    ("GMAO", ("gmao",), r"\bgmao\b"),
)
IT_TERMS = (
    (
        "Développement",
        ("développ",),
        r"\bdéveloppement (?:logiciel|d'applications|informatique)|\bdéveloppeur",
    ),
    ("Python", ("python",), r"\bpython\b"),
    ("SQL", ("sql", "données"), r"\bsql\b|\bbases? de données"),
    ("Java ou .NET", ("java", "c#", ".net"), r"\bjava\b|\bc#|\.net\b"),
    (
        "Réseaux",
        ("réseau", "tcp", "vlan"),
        r"réseaux? informatiques?|\btcp/ip\b|\bvlan\b|administration réseau",
    ),
    (
        "Systèmes",
        ("système", "server", "linux", "virtualisation", "vmware"),
        r"administration système|windows server|\blinux\b|virtualisation|\bvmware\b",
    ),
    (
        "Scripts et API",
        ("script", "api", "powershell"),
        r"\bscripts?\b|\bapi\b|\bpowershell\b",
    ),
    (
        "Données",
        ("power bi", "etl", "analyse de données"),
        r"\bpower bi\b|\betl\b|analyse de données",
    ),
)

MIN_IT_TERMS = 2

DETECTION_CACHE_SIZE = 20000


def compile_terms(pTerms):
    """Compile les motifs, gardés avec leurs déclencheurs."""

    rPatterns = [
        (vLabel, vTriggers, re.compile(vPattern))
        for vLabel, vTriggers, vPattern in pTerms
    ]

    return rPatterns


BRIDGE_PATTERNS = compile_terms(BRIDGE_TERMS)
INDUSTRY_PATTERNS = compile_terms(INDUSTRY_TERMS)
IT_PATTERNS = compile_terms(IT_TERMS)


def find_terms(pText, pPatterns):
    """Retourne les libellés des motifs trouvés dans le texte, dans leur ordre.

    Un motif n'est lancé que si l'un de ses déclencheurs figure dans le texte :
    les descriptions pèsent des dizaines de mégaoctets.
    """

    rTerms = [
        vLabel
        for vLabel, vTriggers, vPattern in pPatterns
        if any(vTrigger in pText for vTrigger in vTriggers) and vPattern.search(pText)
    ]

    return rTerms


@lru_cache(maxsize=DETECTION_CACHE_SIZE)
def detect_hybrid(pText):
    """Retourne les termes qui font d'un texte un double profil, ou un tuple vide."""

    vOriginal = pText or ""
    vText = vOriginal.lower()
    vBridges = find_terms(vText, BRIDGE_PATTERNS)

    if "MES" not in vBridges and "MES" in vOriginal and MES_PATTERN.search(vOriginal):
        vBridges.append("MES")

    vIndustry = find_terms(vText, INDUSTRY_PATTERNS)
    vIt = find_terms(vText, IT_PATTERNS)

    if vBridges:
        rTerms = tuple(vBridges + vIt[:2])
    elif vIndustry and len(vIt) >= MIN_IT_TERMS:
        rTerms = tuple(vIndustry[:2] + vIt[:3])
    else:
        rTerms = ()

    return rTerms


def get_offer_hybrid(pOffer):
    """Retourne les termes de double profil d'une offre, titre et description."""

    rTerms = detect_hybrid(
        f"{pOffer.get('title') or ''} {pOffer.get('description') or ''}"
    )

    return rTerms


def describe_offer_hybrid(pOffer):
    """Retourne la ligne « double profil » d'une fiche d'offre, ou une chaîne vide."""

    vTerms = get_offer_hybrid(pOffer)

    rText = (
        "Poste entre maintenance et informatique, votre point fort : "
        + ", ".join(vTerms)
        if vTerms
        else ""
    )

    return rText


def mark_hybrid_offers(pOffers):
    """Ajoute à chaque offre la liste hybrid_terms, vide hors double profil."""

    for vOffer in pOffers:
        vOffer["hybrid_terms"] = list(get_offer_hybrid(vOffer))


# Mots qui rattachent un profil à chaque monde : les compétences d'un profil
# sont des mots isolés (« GMAO », « Python »), pas des phrases d'offre.
INDUSTRY_PROFILE_WORDS = (
    "maintenance",
    "gmao",
    "automat",
    "électrotech",
    "électricit",
    "mécani",
    "hydrauli",
    "pneumati",
    "plc",
    "industri",
    "production",
)
IT_PROFILE_WORDS = (
    "python",
    "java",
    "sql",
    "développ",
    "javascript",
    "typescript",
    "linux",
    "réseau",
    "docker",
    "spring",
    "php",
    "c#",
    ".net",
    "informatique",
    "api",
)
DEFAULT_HEADLINE = "Technicien de maintenance industrielle et informatique"


def to_words(pValue):
    """Retourne un texte en minuscules à partir d'une valeur ou d'une liste."""

    if isinstance(pValue, (list, tuple)):
        rText = " ".join(str(vItem) for vItem in pValue)
    else:
        rText = str(pValue or "")

    return rText.lower()


def has_words(pText, pWords):
    """Indique si le texte contient l'un des mots."""

    rFound = any(vWord in pText for vWord in pWords)

    return rFound


def find_world_title(pProfile, pWords):
    """Retourne le premier intitulé d'expérience rattaché à un monde, ou None."""

    rTitle = next(
        (
            vExperience["title"]
            for vExperience in pProfile.get("experiences") or []
            if vExperience.get("title")
            and has_words(
                to_words(vExperience["title"])
                + " "
                + to_words(vExperience.get("skills")),
                pWords,
            )
        ),
        None,
    )

    return rTitle


def is_profile_hybrid(pProfile):
    """Indique si le profil couvre la maintenance industrielle et l'informatique."""

    vText = " ".join(
        [
            to_words(pProfile.get("headline")),
            to_words(pProfile.get("skills")),
            *(
                to_words(vExperience.get("title"))
                + " "
                + to_words(vExperience.get("skills"))
                for vExperience in pProfile.get("experiences") or []
            ),
            *(
                to_words(vCv.get("name")) + " " + to_words(vCv.get("skills"))
                for vCv in pProfile.get("cv_variants") or []
            ),
        ]
    )

    rHybrid = has_words(vText, INDUSTRY_PROFILE_WORDS) and has_words(
        vText, IT_PROFILE_WORDS
    )

    return rHybrid


def build_hybrid_advice(pProfile, pOffer):
    """Retourne les conseils pour une offre à double profil, ou None.

    Avec un profil qui couvre les deux mondes : phrase de pitch et accroche de
    CV qui les réunissent. Sinon : comment montrer ce qui manque d'un côté.
    """

    vTerms = list(get_offer_hybrid(pOffer))

    if not vTerms:
        return None

    vFits = is_profile_hybrid(pProfile)
    vIndustryTitle = find_world_title(pProfile, INDUSTRY_PROFILE_WORDS)
    vItTitle = find_world_title(pProfile, IT_PROFILE_WORDS)

    if vFits:
        vAdvice = (
            "Votre double parcours est rare : citez-le dès l'accroche du CV et du "
            "pitch, avec un exemple concret de chaque côté."
        )
        vPitch = (
            "Mon parcours réunit la maintenance industrielle et l'informatique : je "
            "comprends les contraintes de l'atelier et je sais faire évoluer les "
            f"outils qui le pilotent ({', '.join(vTerms[:3])})."
        )
        vHeadline = (
            f"{vIndustryTitle} et {vItTitle[:1].lower() + vItTitle[1:]}"
            if vIndustryTitle and vItTitle and vIndustryTitle != vItTitle
            else DEFAULT_HEADLINE
        )
    else:
        vAdvice = (
            "Ce poste demande la maintenance et l'informatique : montrez ce que vous "
            "avez déjà fait dans chacun des deux domaines, même en formation."
        )
        vPitch = ""
        vHeadline = ""

    rAdvice = {
        "terms": vTerms,
        "profile_fits": vFits,
        "advice": vAdvice,
        "pitch": vPitch,
        "headline": vHeadline,
    }

    return rAdvice
