"""Enrichissement des offres à partir de leur description"""

import re

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

# Textes analysés, du plus fiable au moins fiable
TEXT_COLUMNS = ["title", "salary_label", "description", "missions", "requirements"]

# Télétravail : « hybride » et un nombre de jours avant le plein télétravail, pour
# qu'une offre « 2 jours de télétravail » ne soit pas classée en télétravail complet.
REMOTE_DAYS_PATTERN = re.compile(
    r"\b([1-4])\s*(?:jours?|j)\s*(?:de\s+)?(?:télétravail|teletravail|remote)\b"
    r"|\b([1-4])\s*days?\s*(?:of\s+)?(?:remote|home\s*office|wfh)\b",
    re.IGNORECASE,
)
HYBRID_PATTERN = re.compile(
    r"\bhybride?\b|\bhybrid\b|\btélétravail\s+partiel\b", re.IGNORECASE
)
FULL_REMOTE_PATTERN = re.compile(
    r"\bfull[\s-]?remote\b|\bfully\s+remote\b|\b100\s*%\s*(?:en\s+)?(?:télétravail|remote)\b"
    r"|\btélétravail\s+(?:complet|total|intégral)\b|\bremote[\s-]first\b",
    re.IGNORECASE,
)
NO_REMOTE_PATTERN = re.compile(
    r"\bpas\s+de\s+télétravail\b|\bsans\s+télétravail\b|\b100\s*%\s*présentiel\b"
    r"|\bno\s+remote\b|\bon[\s-]?site\s+only\b",
    re.IGNORECASE,
)

# Expérience : un nombre d'années explicite, sinon un niveau nommé.
EXPERIENCE_YEARS_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:\+\s*)?(?:ans|années)\s+(?:minimum\s+)?d['’]\s*expérience\b"
    r"|\b(\d{1,2})\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
    re.IGNORECASE,
)
EXPERIENCE_LEVELS = (
    ("Débutant", re.compile(r"\bdébutants?\b|\bjunior\b|\bentry[\s-]level\b", re.I)),
    ("Senior", re.compile(r"\bsenior\b|\bexpert\b|\blead\b", re.I)),
    ("Confirmé", re.compile(r"\bconfirmée?s?\b|\bmid[\s-]level\b", re.I)),
)

# Salaire : seulement avec une devise et une unité explicites. « 45 » seul peut
# être un âge, un département ou un nombre d'heures.
# Devise en symbole ou en code : « 60-100k EUR », « 100k-160k GBP »
CURRENCY = r"(?:[€$£]|\b(?:EUR|USD|GBP)\b)"
# Milliers avec décimales éventuelles, au point ou à la virgule : « 35,3k », « 135.84k »
THOUSANDS = r"\d{2,3}(?:[.,]\d{1,2})?"
SALARY_RANGE_K_PATTERN = re.compile(
    rf"(?P<currency1>{CURRENCY})?\s*(?P<min>{THOUSANDS})\s*[kK]?\s*"
    rf"(?P<currency2>{CURRENCY})?\s*(?:-|–|à|to)\s*(?P<currency3>{CURRENCY})?\s*"
    rf"(?P<max>{THOUSANDS})\s*[kK]\s*(?P<currency4>{CURRENCY})?",
)
SALARY_SINGLE_K_PATTERN = re.compile(
    rf"(?P<currency1>[€$£])\s*(?P<min>{THOUSANDS})\s*[kK]\b"
    rf"|(?P<min2>{THOUSANDS})\s*[kK]\s*(?P<currency2>[€$£])",
)
# Taux horaire, devise obligatoire : « $45-$120/Hour », « $22 per hour », « 15 €/h »
HOURLY = r"\d{1,3}(?:[.,]\d{1,2})?"
SALARY_HOURLY_PATTERN = re.compile(
    rf"(?P<currency1>[€$£])?\s*(?P<min>{HOURLY})\s*(?P<currency2>[€$£])?"
    rf"(?:\s*(?:-|–|à|to)\s*(?P<currency3>[€$£])?\s*(?P<max>{HOURLY})"
    r"\s*(?P<currency4>[€$£])?)?"
    rf"(?:\s*(?P<currency5>{CURRENCY}))?"
    r"\s*(?:/|per|par)\s*(?:hour|hr|h|heure)\b",
    re.IGNORECASE,
)
# Montants complets à l'anglaise, virgule des milliers et symbole obligatoire :
# « $175,000 - $300,000 », « £80,000-150,000 », « $3,500-$5,000 USD/month »
FULL_AMOUNT = r"\d{1,3}(?:,\d{3})+"
SALARY_FULL_SYMBOL_PATTERN = re.compile(
    rf"(?P<currency1>[€$£])\s*(?P<min>{FULL_AMOUNT})"
    rf"(?:\s*(?:-|–|to)\s*(?P<currency2>[€$£])?\s*(?P<max>{FULL_AMOUNT}))?"
    rf"(?:\s*(?P<currency3>{CURRENCY}))?"
    r"(?P<period>\s*(?:/|per\s)\s*(?:month|mo)\b)?",
    re.IGNORECASE,
)
SALARY_FULL_PATTERN = re.compile(
    r"(?P<min>\d{1,3}[\s  ]?\d{3})\s*(?:€|euros?)"
    r"(?:\s*(?:-|–|à)\s*(?P<max>\d{1,3}[\s  ]?\d{3})\s*(?:€|euros?))?"
    r"(?P<period>\s*(?:brut\s+)?(?:/|par)?\s*(?:an|annuel|mois|mensuel))?",
    re.IGNORECASE,
)
# En dessous, un montant n'est retenu qu'avec une période explicite :
# « 1 000 € de prime » n'est pas un salaire.
MIN_AMOUNT_WITHOUT_PERIOD = 10000

# Libellés des champs complétés, pour un message de log lisible
FILLED_FIELD_LABELS = {
    "remote": "télétravail",
    "skills": "compétences",
    "experience_level": "expérience",
    "salary": "salaire",
    "title": "titre découpé",
}

# Séparateur des compléments ajoutés au titre par certaines sources (Arbeitnow, Jobicy)
TITLE_SEPARATOR = " | "
CURRENCIES = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "EUR": "EUR",
    "USD": "USD",
    "GBP": "GBP",
}

# Compétences techniques reconnues, avec leur forme affichée. Les mots trop
# courants (« go », « r ») ne sont cherchés qu'avec une forme non ambiguë.
SKILLS = {
    "Python": r"python",
    "Java": r"java(?!\s*script)",
    "JavaScript": r"javascript|\bjs\b",
    "TypeScript": r"typescript",
    "SQL": r"\bsql\b",
    "PostgreSQL": r"postgre(?:s|sql)",
    "MySQL": r"mysql",
    "SQL Server": r"\bsql\s*server\b|\bmssql\b",
    "MongoDB": r"mongo(?:db)?",
    "React": r"\breact(?:\.js|js)?\b",
    "Angular": r"\bangular\b",
    "Vue.js": r"\bvue(?:\.js|js)?\b",
    "Node.js": r"\bnode(?:\.js|js)\b",
    "Django": r"\bdjango\b",
    "Flask": r"\bflask\b",
    "FastAPI": r"\bfastapi\b",
    "Spring": r"\bspring(?:\s*boot)?\b",
    "Hibernate": r"\bhibernate\b",
    "JSF / PrimeFaces": r"\bjsf\b|\bjavaserver\s+faces\b|\bprimefaces\b",
    "Maven": r"\bmaven\b",
    "Tomcat": r"\btomcat\b",
    "JUnit": r"\bjunit\b",
    "PHP": r"\bphp\b",
    "Symfony": r"\bsymfony\b",
    "C#": r"(?<!\w)c#",
    ".NET": r"(?<!\w)\.net\b",
    "C++": r"(?<!\w)c\+\+",
    "Go": r"\bgolang\b",
    "Rust": r"\brust\b",
    "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b",
    "Scala": r"\bscala\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "AWS": r"\baws\b|amazon\s+web\s+services",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google\s+cloud",
    "Terraform": r"\bterraform\b",
    "Ansible": r"\bansible\b",
    "Linux": r"\blinux\b",
    "Git": r"\bgit\b",
    "Jira": r"\bjira\b",
    "CI/CD": r"\bci\s*/\s*cd\b",
    "Kafka": r"\bkafka\b",
    "Spark": r"\bspark\b",
    "Airflow": r"\bairflow\b",
    "Pandas": r"\bpandas\b",
    "TensorFlow": r"\btensorflow\b",
    "PyTorch": r"\bpytorch\b",
    "Power BI": r"\bpower\s*bi\b",
    "Tableau": r"\btableau\s+(?:software|desktop)\b",
    "Excel": r"\bexcel\b",
    "SAP": r"\bsap\b",
    "Salesforce": r"\bsalesforce\b",
    "HTML": r"\bhtml5?\b",
    "CSS": r"\bcss3?\b",
    "GraphQL": r"\bgraphql\b",
    # « REST API » en anglais, « API REST » en français
    "REST": r"\brest(?:ful)?\s+api|\bapis?\s+rest(?:ful)?\b",
    "XML": r"\bxml\b",
    "SFTP": r"\bsftp\b",
    "Agile": r"\bagile\b|\bscrum\b",
    # Industrie : automatisme, électricité et maintenance
    "Automates programmables": r"automates?\s+programmables?|\bplc\b",
    "Siemens TIA Portal": r"\btia\s*portal\b|\bstep\s*7\b|\bs7[\s-]?1[25]00\b",
    # Les produits, et non le nom seul : Schneider Electric est aussi un employeur.
    "Schneider": r"\bunity\s+pro\b|\bcontrol\s*expert\b|\bm[235][45]0\b|\bsomachine\b",
    "Rockwell": r"\brockwell\b|\ballen[\s-]bradley\b|\bstudio\s*5000\b|\brslogix\b",
    "Grafcet": r"\bgrafcet\b",
    "Supervision / IHM": r"\bscada\b|\bwincc\b|\bpcvue\b|\bihm\b|\bhmi\b",
    "Réseaux industriels": r"\bmodbus\b|\bprofinet\b|\bprofibus\b|\bethernet/ip\b",
    "Électrotechnique": r"[ée]lectrotechni",
    # Le métier, pas l'adjectif : facture, signature ou feuille de soin
    # « électronique » ne sont pas de l'électronique.
    "Électronique": (
        r"[ée]lectronicien|\b(?:en|l'|d')\s?[ée]lectronique\b"
        r"|[ée]lectronique\s+(?:num[ée]rique|analogique|de\s+puissance|embarqu[ée]e)"
        r"|\b(?:cartes?|composants?|circuits?|montages?)\s+[ée]lectroniques?"
    ),
    "Habilitation électrique": r"habilitations?\s+[ée]lectriques?|\bb[12]v\b|\bh0v\b",
    "Schémas électriques": r"sch[ée]mas?\s+[ée]lectriques?|\beplan\b",
    "Variateurs de vitesse": r"\bvariateurs?\b",
    "Pneumatique": r"\bpneumatique\b",
    "Hydraulique": r"\bhydrauliques?\b",
    "Mécanique": r"\bm[ée]caniques?\b",
    "Instrumentation et régulation": r"\binstrumentation\b|\br[ée]gulation\b",
    "Robotique": r"\brobotique\b|\bfanuc\b|\bkuka\b|\brobots?\s+industriels?\b",
    "Maintenance préventive et curative": (
        r"maintenance\s+(?:pr[ée]ventive|curative|corrective|conditionnelle)"
    ),
    "GMAO": r"\bgmao\b|\bcmms\b|\bmaximo\b",
    "Lean": r"\blean\b|\bkaizen\b|\bam[ée]lioration\s+continue\b",
    "TPM": r"\btpm\b",
    "AMDEC": r"\bamdec\b|\bfmea\b",
    "Lecture de plans": r"lecture\s+de\s+plans?|lire\s+(?:des|les)\s+plans",
    "CAO": r"\bcao\b|\bsolidworks\b|\bautocad\b|\bcatia\b",
    "Soudure": r"\bsoudure\b|\bsoudage\b",
    "CVC et froid": r"\bcvc\b|\bfrigorifiques?\b|\bclimatisation\b",
}
SKILL_PATTERNS = {
    vLabel: re.compile(vPattern, re.IGNORECASE) for vLabel, vPattern in SKILLS.items()
}


# Colonnes que l'enrichissement peut remplir
ENRICHED_COLUMNS = (
    "remote",
    "remote_type",
    "remote_days",
    "skills",
    "experience_level",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
)


def is_empty(pValue):
    """Indique si une valeur fournie par la source est absente."""

    rEmpty = pValue is None or (not isinstance(pValue, list) and pd.isna(pValue))

    if isinstance(pValue, (list, str)) and not pValue:
        rEmpty = True

    return rEmpty


def detect_remote(pText):
    """Retourne (télétravail, type, jours) détectés, ou None s'il n'est pas mentionné."""

    rRemote = None
    vDays = REMOTE_DAYS_PATTERN.search(pText)

    if NO_REMOTE_PATTERN.search(pText):
        rRemote = (False, None, None)
    elif vDays:
        rRemote = (True, "hybrid", int(vDays.group(1) or vDays.group(2)))
    elif FULL_REMOTE_PATTERN.search(pText):
        rRemote = (True, "full", None)
    elif HYBRID_PATTERN.search(pText):
        rRemote = (True, "hybrid", None)

    return rRemote


def detect_experience(pText):
    """Retourne l'expérience demandée, en années si elles sont précisées."""

    rExperience = None
    vYears = EXPERIENCE_YEARS_PATTERN.search(pText)

    if vYears:
        rExperience = f"{vYears.group(1) or vYears.group(2)} ans"
    else:
        rExperience = next(
            (
                vLabel
                for vLabel, vPattern in EXPERIENCE_LEVELS
                if vPattern.search(pText)
            ),
            None,
        )

    return rExperience


def detect_skills(pText):
    """Retourne les compétences techniques citées, dans l'ordre du dictionnaire."""

    rSkills = [
        vLabel for vLabel, vPattern in SKILL_PATTERNS.items() if vPattern.search(pText)
    ]

    return rSkills


def to_amount(pValue):
    """Convertit « 45 000 » ou « 45000 » en nombre."""

    rAmount = float(re.sub(r"[\s  ]", "", pValue))

    return rAmount


def to_decimal(pValue):
    """Convertit « 35,3 » ou « 35.3 » en nombre."""

    rNumber = float(pValue.replace(",", "."))

    return rNumber


def find_currency(pMatch):
    """Retourne la devise trouvée à l'un des emplacements du motif, ou None."""

    # Un code écrit « usd » dans le texte reste reconnu.
    rCurrency = next(
        (
            vValue.upper() if vValue.isalpha() else vValue
            for vName, vValue in pMatch.groupdict().items()
            if vName.startswith("currency") and vValue
        ),
        None,
    )

    return rCurrency


def detect_salary(pText):
    """Retourne (minimum, maximum, devise, période) d'un salaire explicite, ou None."""

    rSalary = None

    # Avant les milliers : dans « $45-$120/Hour », 45 et 120 sont des taux horaires.
    vMatch = SALARY_HOURLY_PATTERN.search(pText)

    if vMatch and find_currency(vMatch):
        rSalary = (
            to_decimal(vMatch.group("min")),
            to_decimal(vMatch.group("max")) if vMatch.group("max") else None,
            CURRENCIES[find_currency(vMatch)],
            "hour",
        )

    if rSalary is None:
        vMatch = SALARY_RANGE_K_PATTERN.search(pText)

        # Une fourchette en milliers n'est retenue qu'avec une devise.
        if vMatch and find_currency(vMatch):
            rSalary = (
                to_decimal(vMatch.group("min")) * 1000,
                to_decimal(vMatch.group("max")) * 1000,
                CURRENCIES[find_currency(vMatch)],
                "year",
            )

    if rSalary is None:
        vMatch = SALARY_SINGLE_K_PATTERN.search(pText)

        if vMatch:
            vCurrency = vMatch.group("currency1") or vMatch.group("currency2")
            vAmount = to_decimal(vMatch.group("min") or vMatch.group("min2")) * 1000
            rSalary = (vAmount, None, CURRENCIES[vCurrency], "year")

    if rSalary is None:
        vMatch = SALARY_FULL_SYMBOL_PATTERN.search(pText)

        if vMatch:
            rSalary = (
                to_amount(vMatch.group("min").replace(",", "")),
                (
                    to_amount(vMatch.group("max").replace(",", ""))
                    if vMatch.group("max")
                    else None
                ),
                CURRENCIES[find_currency(vMatch)],
                "month" if vMatch.group("period") else "year",
            )

    if rSalary is None:
        vMatch = SALARY_FULL_PATTERN.search(pText)

        if vMatch:
            vMinimum = to_amount(vMatch.group("min"))
            vMaximum = to_amount(vMatch.group("max")) if vMatch.group("max") else None
            vPeriod = vMatch.group("period") or ""
            vIsMonthly = re.search(r"mois|mensuel", vPeriod, re.IGNORECASE)

            if vPeriod.strip() or vMinimum >= MIN_AMOUNT_WITHOUT_PERIOD:
                rSalary = (
                    vMinimum,
                    vMaximum,
                    "EUR",
                    "month" if vIsMonthly else "year",
                )

    return rSalary


def enrich_offer(pOffer, pText):
    """Complète les champs vides d'une offre ; retourne les champs remplis."""

    rFilled = []

    if is_empty(pOffer.get("remote")):
        vRemote = detect_remote(pText)

        if vRemote is not None:
            pOffer["remote"], vType, vDays = vRemote
            pOffer["remote_type"] = pOffer.get("remote_type") or vType
            pOffer["remote_days"] = pOffer.get("remote_days") or vDays
            rFilled.append("remote")

    if is_empty(pOffer.get("skills")):
        vSkills = detect_skills(pText)

        if vSkills:
            pOffer["skills"] = vSkills
            rFilled.append("skills")

    if is_empty(pOffer.get("experience_level")):
        vExperience = detect_experience(pText)

        if vExperience:
            pOffer["experience_level"] = vExperience
            rFilled.append("experience_level")

    if is_empty(pOffer.get("salary_min")) and is_empty(pOffer.get("salary_max")):
        vSalary = detect_salary(pText)

        if vSalary is not None:
            (
                pOffer["salary_min"],
                pOffer["salary_max"],
                pOffer["salary_currency"],
                pOffer["salary_period"],
            ) = vSalary
            rFilled.append("salary")

    # « Data engineer (m/w/d) | Snowflake | Remote » : le premier segment est le
    # poste, les autres des compléments déjà lus ci-dessus dans le texte complet.
    vTitle = pOffer.get("title")

    if isinstance(vTitle, str) and TITLE_SEPARATOR in vTitle:
        pOffer["title"] = vTitle.split(TITLE_SEPARATOR)[0].strip() or vTitle
        rFilled.append("title")

    return rFilled


def is_unusable(pOffer):
    """Indique si une offre n'a pas de titre : réponse, remarque ou annonce tronquée.

    Une description seule ne suffit pas : sans poste, l'offre ne se trie ni ne
    se lit dans la liste.
    """

    rUnusable = is_empty(pOffer.get("title"))

    return rUnusable


def enrich_offers(pItems):
    """Écarte les offres inexploitables et complète les autres.

    Retourne aussi le nombre d'offres écartées par source.
    """

    vOffers = []
    vRejected = {}
    vFilledCounts = {}

    for vOffer in pItems.to_dict("records"):
        if is_unusable(vOffer):
            vSource = "inconnue" if is_empty(vOffer.get("source")) else vOffer["source"]
            vRejected[vSource] = vRejected.get(vSource, 0) + 1
            continue

        # Une phrase d'en-tête rangée à la fois en titre et en entreprise : seul
        # le titre a un sens.
        if vOffer.get("company") and vOffer.get("company") == vOffer.get("title"):
            vOffer["company"] = None
            vFilledCounts["company"] = vFilledCounts.get("company", 0) + 1

        vText = " ".join(
            str(vOffer.get(vColumn) or "")
            for vColumn in TEXT_COLUMNS
            if not is_empty(vOffer.get(vColumn))
        )

        for vField in enrich_offer(vOffer, vText):
            vFilledCounts[vField] = vFilledCounts.get(vField, 0) + 1

        vOffers.append(vOffer)

    logger.info(
        "Enrichissement de %s offre(s) : %s ; offre(s) sans titre écartée(s) : %s",
        len(vOffers),
        ", ".join(
            f"{FILLED_FIELD_LABELS.get(vField, vField)} {vCount}"
            for vField, vCount in vFilledCounts.items()
        )
        or "rien à compléter",
        ", ".join(f"{vSource} {vCount}" for vSource, vCount in vRejected.items())
        or "aucune",
    )

    # Les colonnes remplies sont garanties même si le tableau reçu ne les avait pas.
    vColumns = list(dict.fromkeys([*pItems.columns, *ENRICHED_COLUMNS]))

    rResult = (pd.DataFrame(vOffers, columns=vColumns), vRejected)

    return rResult
