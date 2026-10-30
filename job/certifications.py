"""Certifications citées par les offres, celles du candidat et leur validité

Chaque certification du catalogue est repérée dans le titre et la description
des offres. Les comptes montrent lesquelles reviennent le plus, en particulier
dans les offres proches du profil, et un plan propose les trois qui couvriraient
le plus d'offres restantes. Durées et coûts sont des ordres de grandeur : la
fiche de l'organisme fait foi.
"""

import calendar
import re
from datetime import date, timedelta
from functools import lru_cache

from storage.attachments import count_attachments
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

OWNED_KEY = "certifications_owned"
DETAILS_KEY = "certifications_details"

# Source des documents joints dans job_attachment, l'identifiant étant celui
# de la certification : copie du certificat, attestation, carte CACES…
DOCUMENT_SOURCE = "certification"

# Informations saisies par le candidat ; expires est une date ISO
DETAIL_FIELDS = (
    "organism",
    "number",
    "level",
    "expires",
    "verify_link",
    "funding_used",
    "notes",
)
MAX_DETAIL_LENGTH = 1000

# Offre jugée proche du profil à partir de ce score de correspondance
CLOSE_MATCH = 50

# Certifications proposées par le plan
PLAN_SIZE = 3

# État d'une certification citée par une offre, selon que le candidat l'a ou non
OWNED_LABELS = {True: "vous l'avez", False: "à passer"}

# Une certification expire bientôt dans ce délai : il faut prévoir le recyclage.
RENEWAL_NOTICE_DAYS = 90

CATEGORIES = ("Industrie et sécurité", "Qualité", "Informatique", "Langues et permis")

CPF = "CPF possible selon l'organisme"
SELF_STUDY = "Préparation gratuite en ligne, examen payant"

# id, libellé, catégorie, motif insensible à la casse, motif sensible à la
# casse (sigles courts), durée, coût indicatif, financement, validité en mois
# (None : sans limite ou selon l'employeur), lien, conseil pour le CV
CATALOG = (
    (
        "habilitation-electrique",
        "Habilitation électrique (B1V, B2V, BR, BC, H0V)",
        "Industrie et sécurité",
        r"habilitations?\s+(?:é|e)lectriques?",
        r"\b(?:B1V|B2V|BR|BC|B0|H0V|H1V|H2V|HC)\b",
        "2 à 4 jours",
        "300 à 900 €",
        CPF,
        36,
        "https://fr.wikipedia.org/wiki/Habilitation_%C3%A9lectrique",
        "Écrire « Formation habilitation électrique B2V-BR (année) » : l'habilitation est délivrée par l'employeur.",
    ),
    (
        "sst",
        "Sauveteur secouriste du travail (SST)",
        "Industrie et sécurité",
        r"sauveteur\s+secouriste|secouriste du travail",
        r"\bSST\b",
        "2 jours",
        "150 à 350 €",
        CPF,
        24,
        "https://www.inrs.fr/services/formation/demultiplication/sst.html",
        "Recyclage (MAC SST) tous les 24 mois.",
    ),
    (
        "caces-r489",
        "CACES R489 chariots élévateurs",
        "Industrie et sécurité",
        r"caces\s*(?:r\s?)?489|chariots? (?:é|e)l(?:é|e)vateurs?.{0,40}caces|caces.{0,40}chariot",
        None,
        "3 à 5 jours",
        "600 à 1 200 €",
        CPF,
        60,
        "https://www.inrs.fr/services/formation/caces.html",
        "Préciser les catégories obtenues (1, 3, 5…).",
    ),
    (
        "caces-r486",
        "CACES R486 nacelles (PEMP)",
        "Industrie et sécurité",
        r"caces\s*(?:r\s?)?486|nacelles?.{0,40}caces|caces.{0,40}nacelle|\bpemp\b",
        None,
        "2 à 3 jours",
        "500 à 1 000 €",
        CPF,
        60,
        "https://www.inrs.fr/services/formation/caces.html",
        "Souvent demandé en maintenance de bâtiments et d'installations en hauteur.",
    ),
    (
        "caces-autres",
        "CACES autres engins (R482, R490…)",
        "Industrie et sécurité",
        r"caces\s*(?:r\s?)?(?:482|490|483|484|485|487)",
        None,
        "2 à 5 jours",
        "500 à 1 500 €",
        CPF,
        60,
        "https://fr.wikipedia.org/wiki/Certificat_d%27aptitude_%C3%A0_la_conduite_en_s%C3%A9curit%C3%A9",
        "Validité de 5 ans, 10 ans pour les engins de chantier (R482).",
    ),
    (
        "caces",
        "CACES (type non précisé par l'offre)",
        "Industrie et sécurité",
        r"\bcaces\b",
        None,
        "2 à 5 jours",
        "500 à 1 200 €",
        CPF,
        60,
        "https://www.inrs.fr/services/formation/caces.html",
        "L'offre ne précise pas l'engin : le R489 (chariots) est le plus courant.",
    ),
    (
        "aipr",
        "AIPR (travaux à proximité des réseaux)",
        "Industrie et sécurité",
        r"\baipr\b|proximit(?:é|e) des r(?:é|e)seaux",
        None,
        "1 jour avec examen",
        "100 à 300 €",
        CPF,
        60,
        "https://www.reseaux-et-canalisations.ineris.fr/gu-portail/",
        "Obligatoire pour intervenir près de réseaux enterrés ou aériens.",
    ),
    (
        "atex",
        "Formation ATEX (niveau 1 ou 2)",
        "Industrie et sécurité",
        r"\batex\b",
        None,
        "1 à 3 jours",
        "300 à 900 €",
        CPF,
        36,
        "https://fr.wikipedia.org/wiki/ATEX",
        "Utile en chimie, agroalimentaire et énergie (zones explosives).",
    ),
    (
        "travail-hauteur",
        "Travail en hauteur et port du harnais",
        "Industrie et sécurité",
        r"travail en hauteur|port du harnais",
        None,
        "1 à 2 jours",
        "200 à 500 €",
        CPF,
        None,
        "https://www.inrs.fr/risques/chutes-hauteur/ce-qu-il-faut-retenir.html",
        "Recyclage conseillé, à la fréquence fixée par l'employeur.",
    ),
    (
        "gies",
        "GIES 1 ou 2 (sécurité des sites chimiques)",
        "Industrie et sécurité",
        r"\bgies\s?[12]?\b",
        None,
        "1 à 2 jours",
        "200 à 500 €",
        CPF,
        36,
        "https://www.mase-asso.fr/",
        "Exigé pour intervenir en entreprise extérieure sur les sites pétrochimiques.",
    ),
    (
        "risque-chimique",
        "Risque chimique N1 ou N2",
        "Industrie et sécurité",
        r"risque chimique\s*n\s?[12]",
        None,
        "1 à 2 jours",
        "200 à 500 €",
        CPF,
        36,
        "https://www.mase-asso.fr/",
        "Souvent couplé au GIES pour les sites Seveso.",
    ),
    (
        "mase",
        "Sensibilisation MASE",
        "Industrie et sécurité",
        r"\bmase\b",
        None,
        "1 jour",
        "150 à 300 €",
        CPF,
        None,
        "https://www.mase-asso.fr/",
        "Rassure les donneurs d'ordre sur la sécurité des intervenants.",
    ),
    (
        "nucleaire",
        "Habilitations nucléaires (RP1, CSQ, SAN)",
        "Industrie et sécurité",
        r"habilitations? nucl(?:é|e)aires?|radioprotection",
        r"\b(?:RP1|RP2|CSQ)\b",
        "2 à 5 jours",
        "500 à 1 500 €",
        CPF,
        36,
        "https://fr.wikipedia.org/wiki/Radioprotection",
        "Indispensable pour la maintenance en centrale.",
    ),
    (
        "soudure",
        "Qualification soudeur (ISO 9606)",
        "Industrie et sécurité",
        r"soudeur qualifi(?:é|e)|qualification (?:de )?soud|iso\s?9606",
        None,
        "Variable selon le procédé",
        "500 à 1 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/Soudage",
        "Préciser le procédé et la position qualifiés.",
    ),
    (
        "fluides-frigorigenes",
        "Attestation d'aptitude fluides frigorigènes",
        "Industrie et sécurité",
        r"fluides? frigorig(?:è|e)nes?|attestation d'aptitude",
        None,
        "3 à 5 jours",
        "800 à 1 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/Fluide_frigorig%C3%A8ne",
        "Obligatoire pour intervenir sur les circuits frigorifiques.",
    ),
    (
        "tia-portal",
        "Formation Siemens TIA Portal (SITRAIN)",
        "Industrie et sécurité",
        r"tia\s?portal|step\s?7|sitrain",
        None,
        "3 à 5 jours",
        "1 500 à 3 000 €",
        CPF,
        None,
        "https://www.siemens.com/sitrain",
        "Une attestation de formation constructeur valorise bien un profil automatisme.",
    ),
    (
        "iso-9001",
        "Auditeur interne ISO 9001",
        "Qualité",
        r"iso\s?9001|auditeur interne",
        None,
        "2 à 3 jours",
        "800 à 1 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/ISO_9001",
        "Montre que vous savez lire une procédure et traiter une non-conformité.",
    ),
    (
        "qse",
        "Auditeur interne QSE (ISO 14001, ISO 45001)",
        "Qualité",
        r"iso\s?14001|iso\s?45001|ohsas|\bqse\b|\bqhse\b",
        None,
        "3 à 5 jours",
        "1 000 à 2 000 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/ISO_45001",
        "Recherché quand le poste touche la sécurité et l'environnement.",
    ),
    (
        "iatf",
        "IATF 16949 (automobile)",
        "Qualité",
        r"\biatf\b|16949",
        None,
        "2 à 3 jours",
        "800 à 1 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/IATF_16949",
        "Utile chez les équipementiers automobiles (PPAP, AMDEC, MSP).",
    ),
    (
        "green-belt",
        "Lean Six Sigma Green Belt",
        "Qualité",
        r"green belt|yellow belt|black belt|six sigma|lean six",
        None,
        "5 à 10 jours",
        "1 500 à 3 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/Six_Sigma",
        "Associer un projet mené et son gain chiffré.",
    ),
    (
        "iso-27001",
        "ISO 27001 Foundation ou Lead Implementer",
        "Informatique",
        r"iso\s?27001",
        None,
        "2 à 5 jours",
        "1 000 à 3 500 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/ISO/CEI_27001",
        "Sécurité de l'information, utile aussi en OT.",
    ),
    (
        "itil",
        "ITIL 4 Foundation",
        "Informatique",
        r"\bitil\b",
        None,
        "2 à 3 jours ou autoformation",
        "300 à 1 200 €",
        SELF_STUDY,
        None,
        "https://fr.wikipedia.org/wiki/Information_Technology_Infrastructure_Library",
        "Support, exploitation et gestion des incidents.",
    ),
    (
        "az-900",
        "Microsoft Azure Fundamentals (AZ-900)",
        "Informatique",
        r"\baz-?900\b|azure fundamentals",
        None,
        "2 à 4 semaines d'autoformation",
        "Environ 100 €",
        SELF_STUDY,
        None,
        "https://learn.microsoft.com/fr-fr/credentials/certifications/azure-fundamentals/",
        "Accessible seul, bonne porte d'entrée vers le cloud.",
    ),
    (
        "az-104",
        "Microsoft Azure Administrator (AZ-104)",
        "Informatique",
        r"\baz-?104\b|azure administrator",
        None,
        "1 à 3 mois d'autoformation",
        "Environ 160 €",
        SELF_STUDY,
        12,
        "https://learn.microsoft.com/fr-fr/credentials/certifications/azure-administrator/",
        "Renouvellement annuel gratuit en ligne.",
    ),
    (
        "aws-ccp",
        "AWS Certified Cloud Practitioner",
        "Informatique",
        r"aws certified|certification aws|cloud practitioner",
        None,
        "2 à 4 semaines d'autoformation",
        "Environ 100 €",
        SELF_STUDY,
        36,
        "https://aws.amazon.com/fr/certification/certified-cloud-practitioner/",
        "Bases du cloud AWS, valable 3 ans.",
    ),
    (
        "psm",
        "Professional Scrum Master (PSM I)",
        "Informatique",
        r"\bpsm\b|professional scrum|scrum master certifi|certification scrum",
        None,
        "Quelques semaines d'autoformation",
        "Environ 200 €",
        SELF_STUDY,
        None,
        "https://www.scrum.org/assessments/professional-scrum-master-i-certification",
        "Valable à vie, montre la pratique des méthodes agiles.",
    ),
    (
        "ccna",
        "Cisco CCNA",
        "Informatique",
        r"\bccna\b",
        None,
        "2 à 4 mois",
        "Environ 300 € l'examen",
        SELF_STUDY,
        36,
        "https://fr.wikipedia.org/wiki/Cisco_Certified_Network_Associate",
        "Réseaux, utile en informatique industrielle.",
    ),
    (
        "ocp-java",
        "Oracle Certified Professional Java (OCP)",
        "Informatique",
        r"\bocp\b|oracle certified",
        None,
        "2 à 3 mois",
        "Environ 250 €",
        SELF_STUDY,
        None,
        "https://education.oracle.com/",
        "Valorise un profil de développeur Java.",
    ),
    (
        "istqb",
        "ISTQB Foundation (tests logiciels)",
        "Informatique",
        r"\bistqb\b",
        None,
        "3 jours ou autoformation",
        "250 à 1 200 €",
        SELF_STUDY,
        None,
        "https://www.istqb.org/",
        "Utile pour un poste de testeur ou de qualité logicielle.",
    ),
    (
        "pmp",
        "Gestion de projet (PMP, PRINCE2)",
        "Informatique",
        r"\bpmp\b|prince\s?2",
        None,
        "5 jours à plusieurs mois",
        "1 000 à 3 000 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/Project_Management_Institute",
        "Pour les postes de chef de projet.",
    ),
    (
        "kubernetes",
        "Kubernetes (CKA, CKAD)",
        "Informatique",
        r"\bcka\b|\bckad\b|certified kubernetes",
        None,
        "1 à 3 mois",
        "Environ 400 €",
        SELF_STUDY,
        24,
        "https://www.cncf.io/training/certification/cka/",
        "Examen pratique, très reconnu en DevOps.",
    ),
    (
        "terraform",
        "HashiCorp Terraform Associate",
        "Informatique",
        r"terraform associate|certification terraform",
        None,
        "1 mois d'autoformation",
        "Environ 70 €",
        SELF_STUDY,
        24,
        "https://developer.hashicorp.com/certifications",
        "Infrastructure as code.",
    ),
    (
        "pix",
        "Certification Pix (compétences numériques)",
        "Informatique",
        r"\bpix\b",
        None,
        "Autoformation",
        "Gratuit ou peu coûteux selon le centre",
        CPF,
        36,
        "https://pix.fr/",
        "Utile pour les postes administratifs ou de support.",
    ),
    (
        "anglais",
        "Anglais : TOEIC ou équivalent",
        "Langues et permis",
        r"\btoeic\b|\bbulats\b|linguaskill|anglais (?:courant|technique|professionnel|lu|(?:é|e)crit|op(?:é|e)rationnel)|niveau d'anglais|ma(?:î|i)trise de l'anglais",
        None,
        "Selon votre niveau",
        "Environ 150 € l'examen",
        CPF,
        24,
        "https://fr.wikipedia.org/wiki/Test_of_English_for_International_Communication",
        "Un score chiffré rassure plus que « anglais courant ».",
    ),
    (
        "permis-b",
        "Permis B",
        "Langues et permis",
        r"permis\s+b\b|permis de conduire",
        None,
        "Variable",
        "1 000 à 2 000 €",
        CPF,
        None,
        "https://fr.wikipedia.org/wiki/Permis_de_conduire_en_France",
        "Souvent exigé pour les postes itinérants ou d'astreinte.",
    ),
)

CERTIFICATIONS = {
    vItem[0]: {
        "id": vItem[0],
        "label": vItem[1],
        "category": vItem[2],
        "duration": vItem[5],
        "cost": vItem[6],
        "funding": vItem[7],
        "validity_months": vItem[8],
        "link": vItem[9],
        "advice": vItem[10],
    }
    for vItem in CATALOG
}

# Mots déclencheurs, en minuscules : l'expression d'une certification ne
# parcourt le texte que si l'un d'eux y figure. Les descriptions pèsent des
# dizaines de mégaoctets ; une recherche de sous-chaîne est presque gratuite.
TRIGGERS = {
    "habilitation-electrique": ("habilitation",),
    "sst": ("secouriste", "sst"),
    "caces-r489": ("caces",),
    "caces-r486": ("caces", "pemp"),
    "caces-autres": ("caces",),
    "caces": ("caces",),
    "aipr": ("aipr", "proximit"),
    "atex": ("atex",),
    "travail-hauteur": ("hauteur", "harnais"),
    "gies": ("gies",),
    "risque-chimique": ("chimique",),
    "mase": ("mase",),
    "nucleaire": ("nucl", "radioprot"),
    "soudure": ("soud", "9606"),
    "fluides-frigorigenes": ("frigorig", "aptitude"),
    "tia-portal": ("tia", "step", "sitrain"),
    "iso-9001": ("9001", "auditeur"),
    "qse": ("14001", "45001", "ohsas", "qse", "qhse"),
    "iatf": ("iatf", "16949"),
    "green-belt": ("belt", "sigma", "lean six"),
    "iso-27001": ("27001",),
    "itil": ("itil",),
    "az-900": ("900", "azure fundamentals"),
    "az-104": ("104", "azure administrator"),
    "aws-ccp": ("aws", "cloud practitioner"),
    "psm": ("psm", "scrum"),
    "ccna": ("ccna",),
    "ocp-java": ("ocp", "oracle certified"),
    "istqb": ("istqb",),
    "pmp": ("pmp", "prince"),
    "kubernetes": ("cka", "certified kubernetes"),
    "terraform": ("terraform",),
    "pix": ("pix",),
    "anglais": ("toeic", "bulats", "linguaskill", "anglais"),
    "permis-b": ("permis",),
}

# Sigles cherchés tels quels dans le texte d'origine, s'il en contient un
CODE_TRIGGERS = (
    "SST",
    "B1V",
    "B2V",
    "BR",
    "BC",
    "B0",
    "H0V",
    "H1V",
    "H2V",
    "HC",
    "RP1",
    "RP2",
    "CSQ",
)

# Motifs appliqués au texte en minuscules ; les sigles, au texte d'origine
PATTERNS = {vItem[0]: re.compile(vItem[3]) for vItem in CATALOG}
CODE_PATTERNS = {vItem[0]: re.compile(vItem[4]) for vItem in CATALOG if vItem[4]}

DETECTION_CACHE_SIZE = 20000

PRECISE_CACES = {"caces-r489", "caces-r486", "caces-autres"}


@lru_cache(maxsize=DETECTION_CACHE_SIZE)
def detect_certifications(pText):
    """Retourne les certifications citées dans un texte."""

    vText = pText or ""
    vLower = vText.lower()
    vHasCode = any(vCode in vText for vCode in CODE_TRIGGERS)

    vFound = {
        vId
        for vId, vPattern in PATTERNS.items()
        if (
            any(vTrigger in vLower for vTrigger in TRIGGERS[vId])
            and vPattern.search(vLower)
        )
        or (vHasCode and vId in CODE_PATTERNS and CODE_PATTERNS[vId].search(vText))
    }

    # Le CACES non précisé ne compte que si aucun CACES précis n'est cité.
    if vFound & PRECISE_CACES:
        vFound.discard("caces")

    rFound = frozenset(vFound)

    return rFound


def get_offer_certifications(pOffer):
    """Retourne les certifications citées par une offre, titre et description."""

    rFound = detect_certifications(
        f"{pOffer.get('title') or ''} {pOffer.get('description') or ''}"
    )

    return rFound


def load_owned(pDatabaseFile):
    """Retourne les certifications du candidat : date d'obtention par identifiant."""

    vOwned = load_json_setting(pDatabaseFile, OWNED_KEY, {}, dict)

    rOwned = {vId: vDate for vId, vDate in vOwned.items() if vId in CERTIFICATIONS}

    return rOwned


def save_owned(pDatabaseFile, pId, pObtained):
    """Enregistre une certification obtenue à une date, ou la retire avec None."""

    if pId not in CERTIFICATIONS:
        raise ValueError(f"Certification inconnue : {pId}")

    vOwned = load_owned(pDatabaseFile)

    if pObtained is None:
        vOwned.pop(pId, None)
    else:
        vOwned[pId] = pObtained.isoformat()

    save_json_setting(pDatabaseFile, OWNED_KEY, vOwned)
    logger.info(
        "Certification %s : %s",
        "retirée" if pObtained is None else "enregistrée",
        CERTIFICATIONS[pId]["label"],
    )


def load_details(pDatabaseFile):
    """Retourne les informations saisies par certification : organisme, numéro…"""

    vDetails = load_json_setting(pDatabaseFile, DETAILS_KEY, {}, dict)

    rDetails = {
        vId: vDetail
        for vId, vDetail in vDetails.items()
        if vId in CERTIFICATIONS and isinstance(vDetail, dict)
    }

    return rDetails


def clean_details(pDetails):
    """Retourne les informations nettoyées ; lève ValueError si l'une est invalide."""

    rDetails = {}

    for vField in DETAIL_FIELDS:
        vValue = str(pDetails.get(vField) or "").strip()[:MAX_DETAIL_LENGTH]

        if vValue:
            rDetails[vField] = vValue

    if "expires" in rDetails:
        try:
            date.fromisoformat(rDetails["expires"])

        except ValueError as vException:
            raise ValueError("Date d'expiration invalide.") from vException

    # Le lien est ouvert d'un clic : seule une adresse web est acceptée.
    if not rDetails.get("verify_link", "https://").startswith(("https://", "http://")):
        raise ValueError("Le lien de vérification doit commencer par https://.")

    return rDetails


def save_details(pDatabaseFile, pId, pDetails):
    """Enregistre les informations d'une certification, ou les efface si vides."""

    if pId not in CERTIFICATIONS:
        raise ValueError(f"Certification inconnue : {pId}")

    vClean = clean_details(pDetails)
    vDetails = load_details(pDatabaseFile)

    if vClean:
        vDetails[pId] = vClean
    else:
        vDetails.pop(pId, None)

    save_json_setting(pDatabaseFile, DETAILS_KEY, vDetails)
    logger.info("Informations enregistrées : %s", CERTIFICATIONS[pId]["label"])


def count_documents(pDatabaseFile):
    """Retourne le nombre de documents joints par certification."""

    rCounts = count_attachments(pDatabaseFile, DOCUMENT_SOURCE)

    return rCounts


def add_months(pDate, pMonths):
    """Retourne la date décalée de pMonths mois, au dernier jour si besoin."""

    vMonth = pDate.month - 1 + pMonths
    vYear = pDate.year + vMonth // 12
    vMonth = vMonth % 12 + 1
    vDay = min(pDate.day, calendar.monthrange(vYear, vMonth)[1])

    rDate = date(vYear, vMonth, vDay)

    return rDate


def describe_validity(pId, pObtained, pToday, pExpires=None):
    """Retourne la date de fin de validité et l'état : valid, soon, expired ou None.

    La date d'expiration lue sur le certificat l'emporte sur la durée habituelle.
    """

    vMonths = CERTIFICATIONS[pId]["validity_months"]

    if not pObtained:
        return None, None

    if pExpires:
        vEnd = date.fromisoformat(pExpires)
    elif vMonths is None:
        return None, "valid"
    else:
        vEnd = add_months(date.fromisoformat(pObtained), vMonths)

    if vEnd < pToday:
        rStatus = "expired"
    elif vEnd <= pToday + timedelta(days=RENEWAL_NOTICE_DAYS):
        rStatus = "soon"
    else:
        rStatus = "valid"

    return vEnd, rStatus


def build_plan(pOfferSets, pOwned):
    """Retourne jusqu'à PLAN_SIZE certifications à passer et la couverture obtenue.

    Une offre est couverte quand le candidat a l'une des certifications qu'elle
    cite. Chaque étape choisit celle qui couvre le plus d'offres restantes.
    """

    vCiting = [vSet for vSet in pOfferSets if vSet]
    vCovered = {vIndex for vIndex, vSet in enumerate(vCiting) if vSet & set(pOwned)}
    vBefore = len(vCovered)
    vPlan = []

    for _ in range(PLAN_SIZE):
        vGains = {}

        for vIndex, vSet in enumerate(vCiting):
            if vIndex not in vCovered:
                for vId in vSet - set(pOwned) - set(vPlan):
                    vGains[vId] = vGains.get(vId, 0) + 1

        if not vGains:
            break

        vBest = max(sorted(vGains), key=vGains.get)
        vPlan.append(vBest)
        vCovered |= {vIndex for vIndex, vSet in enumerate(vCiting) if vBest in vSet}

    vTotal = len(vCiting) or 1

    rPlan = {
        "plan": vPlan,
        "citing": len(vCiting),
        "covered_before": round(100 * vBefore / vTotal),
        "covered_after": round(100 * len(vCovered) / vTotal),
    }

    return rPlan


def build_overview(pDatabaseFile, pOffers, pToday):
    """Retourne les certifications avec leurs comptes, leur état et le plan conseillé.

    pOffers sont les offres notées (match_score) : celles à CLOSE_MATCH et plus
    comptent comme proches du profil.
    """

    vOwned = load_owned(pDatabaseFile)
    vDetails = load_details(pDatabaseFile)
    vDocumentCounts = count_documents(pDatabaseFile)
    vSets = [get_offer_certifications(vOffer) for vOffer in pOffers]
    vCloseSets = [
        vSet
        for vOffer, vSet in zip(pOffers, vSets)
        if (vOffer.get("match_score") or 0) >= CLOSE_MATCH
    ]
    vRows = []

    for vId, vItem in CERTIFICATIONS.items():
        vDetail = vDetails.get(vId, {})
        vEnd, vStatus = describe_validity(
            vId, vOwned.get(vId), pToday, vDetail.get("expires")
        )
        vRows.append(
            {
                **vItem,
                "count": sum(vId in vSet for vSet in vSets),
                "close_count": sum(vId in vSet for vSet in vCloseSets),
                "obtained": vOwned.get(vId),
                "details": vDetail,
                "documents": vDocumentCounts.get(vId, 0),
                "valid_until": vEnd.isoformat() if vEnd else None,
                "status": vStatus,
            }
        )

    vRows.sort(key=lambda pRow: (-pRow["close_count"], -pRow["count"], pRow["label"]))

    rOverview = {
        "rows": vRows,
        "offers": len(pOffers),
        "close_offers": len(vCloseSets),
        **build_plan(vCloseSets or vSets, vOwned),
        "plan_labels": [],
    }
    rOverview["plan_labels"] = [
        CERTIFICATIONS[vId]["label"] for vId in rOverview["plan"]
    ]

    return rOverview


def describe_offer_certifications(pOffer, pOwned):
    """Retourne les certifications citées par une offre, marquées si le candidat les a."""

    rText = " · ".join(
        f"{CERTIFICATIONS[vId]['label']} ({OWNED_LABELS[vId in pOwned]})"
        for vId in sorted(get_offer_certifications(pOffer))
    )

    return rText


def find_renewals(pDatabaseFile, pToday):
    """Retourne les certifications expirées ou à renouveler bientôt."""

    rRenewals = []
    vDetails = load_details(pDatabaseFile)

    for vId, vObtained in load_owned(pDatabaseFile).items():
        vEnd, vStatus = describe_validity(
            vId, vObtained, pToday, vDetails.get(vId, {}).get("expires")
        )

        if vStatus in ("soon", "expired"):
            rRenewals.append(
                {
                    "label": CERTIFICATIONS[vId]["label"],
                    "valid_until": vEnd.isoformat(),
                    "status": vStatus,
                }
            )

    return rRenewals
