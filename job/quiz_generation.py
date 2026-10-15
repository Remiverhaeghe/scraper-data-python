"""Demande de questions à ChatGPT et contrôle du respect de ses règles

Le catalogue des thèmes et le texte de la demande sont des fichiers de
assets/quiz_generation : ils évoluent sans toucher au code. Chaque lot importé
est ensuite mesuré, pour repérer un lot qui ne respecte pas la demande.
"""

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from string import Template

from config import QUIZ_GENERATION_DIRECTORY
from job.quiz import (
    QUIZ_LEVELS,
    count_theme_offers,
    find_theme,
    load_quiz,
    slugify,
)
from job.quiz_domains import DOMAIN_ORDER, OTHER_DOMAIN, classify_theme
from job.quiz_types import get_type
from storage.quiz_questions import get_imported_questions
from utils.logger import get_logger

logger = get_logger(__name__)

CATALOG_FILE = QUIZ_GENERATION_DIRECTORY / "catalog.json"
PROMPT_FILE = QUIZ_GENERATION_DIRECTORY / "prompt.txt"
CORRECTION_FILE = QUIZ_GENERATION_DIRECTORY / "correction.txt"

# Nombre de questions demandées à ChatGPT en une fois : 100 remplissent une
# réponse, ChatGPT continue sur demande si elle est coupée.
GENERATION_COUNTS = (10, 20, 30, 50, 100)
DEFAULT_GENERATION_COUNT = 100

# Niveau « tous » de la demande : répartition des questions par niveau, de
# débutant à expert (100 questions : 25, 40, 20, 15).
MIXED_LEVEL = "tous"
LEVEL_WEIGHTS = (0.25, 0.40, 0.20, 0.15)
GENERATION_LEVELS = {
    MIXED_LEVEL: "Tous les niveaux",
    **{vLevel: vLevel.capitalize() for vLevel in QUIZ_LEVELS},
}

# En dessous de ce nombre de questions, une proportion ne prouve rien.
MIN_QUALITY_SAMPLE = 20

# Au hasard, la bonne réponse est la plus longue, la plus courte ou à une
# position donnée une fois sur quatre : au-delà de ces parts, elle se devine.
MAX_LENGTH_SHARE = 0.4
MAX_POSITION_SHARE = 0.4

# Une explication plus courte ne détaille pas pourquoi les autres choix sont faux.
MIN_EXPLANATION_LENGTH = 80
MAX_SHORT_EXPLANATION_SHARE = 0.2

# Thèmes où un tiers des questions doit porter sur un extrait de code, de
# commande ou de programme automate : en dessous de cette part, le lot reste
# théorique.
CODE_SUBDOMAINS = (
    "Développement",
    "Données",
    "Exploitation et DevOps",
    "Réseau",
    "Automatisme",
)
MIN_CODE_SHARE = 0.15

# Un choix coupé par des points de suspension a été raccourci pour tromper la
# mesure des longueurs : il ne se lit plus.
TRUNCATED_ENDINGS = ("…", "...")

# Un énoncé qui s'appuie sur son extrait le cite, par un mot-repère, un
# démonstratif (« cette méthode ») ou un identifiant du code ; sinon l'extrait a
# été ajouté au hasard pour atteindre la part de cas concrets. Au-delà de cette
# part des questions avec code, le lot est signalé.
CODE_REFERENCE_PATTERN = re.compile(
    r"extrait|code|programme|instruction|ci-dessous|commande suivante|`"
    r"|\b(?:ce|cet|cette|ces)\s+\w+",
    re.I,
)
MIN_IDENTIFIER_LENGTH = 3
MAX_UNRELATED_CODE_SHARE = 0.25

# Mots de remplissage ajoutés pour égaliser les longueurs (« dans ce cas »,
# « pour ce besoin ») : une même fin de choix revient bien plus souvent que
# dans un texte rédigé.
FILLER_ENDING_WORDS = 3
FILLER_MIN_COUNT = 6
FILLER_SHARE = 0.1
MAX_FILLER_ISSUES = 3

# Deux questions qui partagent l'essentiel de leurs mots (énoncé, extrait et
# bonne réponse) testent la même chose : une reformulation n'apporte rien.
DUPLICATE_SIMILARITY = 0.8
MIN_SIGNIFICANT_LENGTH = 4

POSITION_LABELS = "ABCD"

# Objectif de questions par thème ; les thèmes à compléter en priorité sont
# les plus demandés dans les offres parmi ceux qui en sont loin.
TARGET_QUESTIONS = 100
PRIORITY_LIMIT = 5


@lru_cache
def load_catalog(pFile=CATALOG_FILE):
    """Retourne les thèmes du catalogue : domaine, sous-domaine et mots des offres."""

    vData = json.loads(Path(pFile).read_text(encoding="utf-8"))

    rThemes = tuple(
        {
            "id": vTheme["id"],
            "label": vTheme["label"],
            "domain": vDomain,
            "subdomain": vSubdomain,
            "skills": tuple(vTheme.get("skills", ())),
        }
        for vDomain, vSubdomains in vData.items()
        for vSubdomain, vThemes in vSubdomains.items()
        for vTheme in vThemes
    )

    return rThemes


def find_catalog_theme(pTheme):
    """Retourne le thème du catalogue nommé par son identifiant ou son libellé."""

    vKey = slugify(pTheme)

    rTheme = next(
        (
            vTheme
            for vTheme in load_catalog()
            if vKey in (vTheme["id"], slugify(vTheme["label"]))
        ),
        None,
    )

    return rTheme


def list_generation_themes(pThemes):
    """Retourne les libellés proposés pour une demande : thèmes existants et catalogue."""

    vLabels = {vTheme["label"] for vTheme in pThemes}
    vKeys = {vTheme["key"] for vTheme in pThemes}
    vLabels |= {
        vTheme["label"] for vTheme in load_catalog() if vTheme["id"] not in vKeys
    }

    rLabels = sorted(vLabels, key=str.casefold)

    return rLabels


def build_priority_themes(pDatabaseFile, pQuiz, pLimit=PRIORITY_LIMIT):
    """Retourne les thèmes à compléter en priorité : demandés et peu fournis.

    Les thèmes du catalogue encore vides comptent aussi : leurs mots des offres
    servent à mesurer la demande. Le classement suit la demande multipliée par
    le nombre de questions manquantes pour atteindre l'objectif.
    """

    vThemes = dict(pQuiz)

    for vCatalogTheme in load_catalog():
        if vCatalogTheme["id"] not in vThemes and vCatalogTheme["skills"]:
            vThemes[vCatalogTheme["id"]] = {
                "key": vCatalogTheme["id"],
                "label": vCatalogTheme["label"],
                "skills": list(vCatalogTheme["skills"]),
                "questions": [],
            }

    vCounts = count_theme_offers(pDatabaseFile, vThemes)
    vCandidates = [
        {
            "key": vKey,
            "label": vTheme["label"],
            "offer_count": vCounts[vKey],
            "questions": len(vTheme["questions"]),
            "missing": TARGET_QUESTIONS - len(vTheme["questions"]),
        }
        for vKey, vTheme in vThemes.items()
        if vCounts[vKey] and len(vTheme["questions"]) < TARGET_QUESTIONS
    ]

    rThemes = sorted(
        vCandidates,
        key=lambda pTheme: (
            -pTheme["offer_count"] * pTheme["missing"],
            -pTheme["offer_count"],
            pTheme["label"],
        ),
    )[:pLimit]

    return rThemes


def get_next_lot(pQuestions, pThemeKey):
    """Retourne le numéro du prochain lot d'un thème, d'après ses identifiants."""

    vLots = [get_lot_number(vQuestion["id"], pThemeKey) for vQuestion in pQuestions]

    rLot = max((vLot for vLot in vLots if vLot is not None), default=0) + 1

    return rLot


def split_levels(pLevel, pCount):
    """Retourne la répartition des questions par niveau : [(niveau, nombre)]."""

    if pLevel in QUIZ_LEVELS:
        rLevels = [(pLevel, pCount)]
    else:
        vCounts = [round(pCount * vWeight) for vWeight in LEVEL_WEIGHTS]
        # L'arrondi peut décaler le total : l'écart va au niveau intermédiaire.
        vCounts[1] += pCount - sum(vCounts)

        rLevels = [
            (vLevel, vCount) for vLevel, vCount in zip(QUIZ_LEVELS, vCounts) if vCount
        ]

    return rLevels


def resolve_generation_theme(pQuiz, pThemeLabel):
    """Retourne la clé, le libellé, le domaine et le sous-domaine d'un thème demandé.

    Le catalogue fixe la clé et le classement ; un thème hors catalogue garde
    son classement, ou (None, None) s'il reste à choisir.
    """

    vCatalogTheme = find_catalog_theme(pThemeLabel)

    if vCatalogTheme:
        vThemeKey = vCatalogTheme["id"]
        vThemeLabel = pQuiz.get(vThemeKey, {}).get("label", vCatalogTheme["label"])
        vDomain = (vCatalogTheme["domain"], vCatalogTheme["subdomain"])
    else:
        vThemeKey, vThemeLabel = find_theme(pQuiz, pThemeLabel)
        vTheme = pQuiz.get(vThemeKey, {})
        vDomain = vTheme.get("domain") or classify_theme(
            vThemeLabel, vTheme.get("skills") or [vThemeLabel]
        )

    if tuple(vDomain) == OTHER_DOMAIN:
        vDomain = (None, None)

    rTheme = (vThemeKey, vThemeLabel, *vDomain)

    return rTheme


def build_generation_prompt(pQuiz, pThemeLabel, pLevel, pCount):
    """Retourne la demande ChatGPT d'un lot de questions au format de l'import.

    Le lot suit les lots déjà importés du thème : ses identifiants ne peuvent
    pas reprendre ceux d'un lot précédent.
    """

    vThemeKey, vThemeLabel, vDomain, vSubdomain = resolve_generation_theme(
        pQuiz, pThemeLabel
    )
    vTheme = pQuiz.get(vThemeKey, {})
    vCatalogTheme = find_catalog_theme(vThemeKey)
    # Compétences du thème, sinon les mots du catalogue, sinon à faire choisir.
    vSkills = (
        vTheme.get("skills")
        or list(vCatalogTheme["skills"] if vCatalogTheme else ())
        or ["compétence 1", "compétence 2", "…"]
    )
    vLot = get_next_lot(vTheme.get("questions", []), vThemeKey)
    vLevels = split_levels(pLevel, pCount)
    vNeighbours = [
        vCatalogTheme["label"]
        for vCatalogTheme in load_catalog()
        if (vCatalogTheme["domain"], vCatalogTheme["subdomain"])
        == (vDomain, vSubdomain)
        and vCatalogTheme["id"] != vThemeKey
    ]

    if vDomain:
        vDomainRule = f'exactement "{vDomain}" et "{vSubdomain}".'
    else:
        vDomain = vSubdomain = "à choisir (règle 2)"
        vDomainRule = "à choisir dans cette liste :\n" + "\n".join(
            f"   {vName} : {', '.join(vSubdomains)}"
            for vName, vSubdomains in DOMAIN_ORDER.items()
            if vName != OTHER_DOMAIN[0]
        )

    vExample = {
        "theme": vThemeLabel,
        "domain": vDomain,
        "subdomain": vSubdomain,
        "skills": vSkills,
        "questions": [
            {
                "id": f"{vThemeKey}-l{vLot}-001",
                "level": vLevels[0][0],
                "type": "qcm",
                "question": "Énoncé de la question ?",
                "code": "facultatif : extrait de code, de configuration ou de "
                "programme automate",
                "choices": ["…", "…", "…", "…"],
                "answer": 2,
                "expectedAnswer": "texte exact de choices[answer]",
                "explanation": "3 à 5 phrases (règle 8)",
                "tags": ["…"],
                "visual": {
                    "type": "svg",
                    "path": f"../assets/schemas/{vThemeKey}-schema.svg",
                    "alt": "Description du schéma",
                },
                "references": [
                    {"title": "Titre exact de la page officielle", "url": "https://…"}
                ],
            }
        ],
    }

    rPrompt = Template(PROMPT_FILE.read_text(encoding="utf-8")).substitute(
        theme=vThemeLabel,
        key=vThemeKey,
        lot=vLot,
        count=pCount,
        levels=", ".join(f"{vCount} {vLevel}" for vLevel, vCount in vLevels),
        perimeter=(
            "Reste dans le périmètre du thème, sans empiéter sur les thèmes "
            f"voisins : {', '.join(vNeighbours)}."
            if vNeighbours
            else "Reste dans le périmètre du thème."
        ),
        manifest=json.dumps(
            {"themes": [{"id": vThemeKey, "file": f"questions/{vThemeKey}.json"}]},
            ensure_ascii=False,
            indent=2,
        ),
        example=json.dumps(vExample, ensure_ascii=False, indent=2),
        level_values=", ".join(f'"{vLevel}"' for vLevel in QUIZ_LEVELS),
        domain_rule=vDomainRule,
    )

    return rPrompt


def is_longest_answer(pQuestion):
    """Indique si la bonne réponse est strictement plus longue que les autres choix."""

    vLengths = [len(vChoice) for vChoice in pQuestion["choices"]]
    vRight = vLengths.pop(pQuestion["answer"])

    rLongest = all(vRight > vLength for vLength in vLengths)

    return rLongest


def is_shortest_answer(pQuestion):
    """Indique si la bonne réponse est strictement plus courte que les autres choix."""

    vLengths = [len(vChoice) for vChoice in pQuestion["choices"]]
    vRight = vLengths.pop(pQuestion["answer"])

    rShortest = all(vRight < vLength for vLength in vLengths)

    return rShortest


def format_share(pCount, pTotal):
    """Retourne une part en pourcentage arrondi."""

    rText = f"{round(100 * pCount / pTotal)} %"

    return rText


def get_choice_ending(pChoice):
    """Retourne les derniers mots d'un choix, en minuscules et sans ponctuation."""

    vWords = pChoice.lower().strip(" .;:!?").split()

    rEnding = " ".join(vWords[-FILLER_ENDING_WORDS:])

    return rEnding


def describe_measures(pQuestions):
    """Résume les mesures d'un lot en une ligne."""

    vTotal = len(pQuestions)
    vPositions = [
        sum(vQuestion["answer"] == vIndex for vQuestion in pQuestions)
        for vIndex in range(len(POSITION_LABELS))
    ]
    vLevels = [
        sum(vQuestion["level"] == vLevel for vQuestion in pQuestions)
        for vLevel in QUIZ_LEVELS
    ]
    vLongest = sum(is_longest_answer(vQuestion) for vQuestion in pQuestions)
    vShortest = sum(is_shortest_answer(vQuestion) for vQuestion in pQuestions)

    rSummary = (
        f"{vTotal} question(s), bonne réponse la plus longue "
        f"{format_share(vLongest, vTotal)}, la plus courte "
        f"{format_share(vShortest, vTotal)}, positions "
        + " ".join(
            f"{vLabel} {format_share(vCount, vTotal)}"
            for vLabel, vCount in zip(POSITION_LABELS, vPositions)
        )
        + ", niveaux "
        + "/".join(str(vCount) for vCount in vLevels)
        + f", avec code {sum('code' in vQuestion for vQuestion in pQuestions)}"
        f", schémas {sum('visual' in vQuestion for vQuestion in pQuestions)}"
        f", références {sum('references' in vQuestion for vQuestion in pQuestions)}"
    )

    return rSummary


def find_bias_issues(pQuestions, pDomain):
    """Retourne les écarts statistiques d'un lot : [(alerte, identifiants)].

    Ces proportions ne prouvent quelque chose qu'à partir de MIN_QUALITY_SAMPLE
    questions d'un même thème.
    """

    vTotal = len(pQuestions)
    rIssues = []

    for vLabel, vTest in (
        ("la plus longue", is_longest_answer),
        ("la plus courte", is_shortest_answer),
    ):
        vIds = [vQuestion["id"] for vQuestion in pQuestions if vTest(vQuestion)]

        if len(vIds) > MAX_LENGTH_SHARE * vTotal:
            rIssues.append(
                (
                    f"bonne réponse {vLabel} dans "
                    f"{format_share(len(vIds), vTotal)} des questions : elle se devine",
                    vIds,
                )
            )

    for vIndex, vLabel in enumerate(POSITION_LABELS):
        vIds = [
            vQuestion["id"] for vQuestion in pQuestions if vQuestion["answer"] == vIndex
        ]

        if len(vIds) > MAX_POSITION_SHARE * vTotal:
            rIssues.append(
                (
                    f"bonne réponse en position {vLabel} dans "
                    f"{format_share(len(vIds), vTotal)} des questions",
                    vIds,
                )
            )

    vShortIds = [
        vQuestion["id"]
        for vQuestion in pQuestions
        if len(vQuestion["explanation"].strip()) < MIN_EXPLANATION_LENGTH
    ]

    if len(vShortIds) > MAX_SHORT_EXPLANATION_SHARE * vTotal:
        rIssues.append(
            (
                f"{len(vShortIds)} explication(s) de moins de "
                f"{MIN_EXPLANATION_LENGTH} caractères",
                vShortIds,
            )
        )

    vCode = sum("code" in vQuestion for vQuestion in pQuestions)

    if pDomain and pDomain[1] in CODE_SUBDOMAINS and vCode < MIN_CODE_SHARE * vTotal:
        rIssues.append(
            (
                f"{vCode} question(s) avec code sur {vTotal} : moins de "
                f"{round(100 * MIN_CODE_SHARE)} % de cas concrets",
                [],
            )
        )

    return rIssues


def get_question_words(pQuestion):
    """Retourne les mots significatifs d'une question : énoncé, extrait, bonne réponse.

    Les nombres comptent quelle que soit leur longueur : deux calculs aux
    valeurs différentes ne sont pas des doublons.
    """

    vText = " ".join(
        (
            pQuestion["question"],
            pQuestion.get("code", ""),
            pQuestion["choices"][pQuestion["answer"]],
        )
    ).lower()

    rWords = {
        vWord
        for vWord in re.findall(r"\w+", vText)
        if len(vWord) >= MIN_SIGNIFICANT_LENGTH or vWord.isdigit()
    }

    return rWords


def is_near_duplicate(pWords, pOtherWords):
    """Indique si deux ensembles de mots sont assez proches pour un doublon."""

    vUnion = pWords | pOtherWords

    rDuplicate = bool(vUnion) and (
        len(pWords & pOtherWords) / len(vUnion) >= DUPLICATE_SIMILARITY
    )

    return rDuplicate


def find_duplicate_issue(pQuestions, pOthers=()):
    """Retourne l'alerte des quasi-doublons, ou None.

    Chaque question du lot est comparée aux autres questions du lot et à
    pOthers, les questions du thème déjà en place.
    """

    vWords = [
        (vQuestion["id"], get_question_words(vQuestion)) for vQuestion in pQuestions
    ]
    vOthers = [
        (vQuestion["id"], get_question_words(vQuestion)) for vQuestion in pOthers
    ]
    vPairs = [
        (vId, vOtherId)
        for vIndex, (vId, vSet) in enumerate(vWords)
        for vOtherId, vOtherSet in vWords[vIndex + 1 :] + vOthers
        if is_near_duplicate(vSet, vOtherSet)
    ]

    if not vPairs:
        return None

    vIds = sorted({vId for vId, _ in vPairs})

    rIssue = (
        f"{len(vIds)} question(s) presque identique(s) à une autre, par exemple "
        f"{vPairs[0][0]} et {vPairs[0][1]}",
        vIds,
    )

    return rIssue


def cites_code(pQuestion):
    """Indique si l'énoncé d'une question s'appuie sur son extrait de code."""

    vIdentifiers = {
        vWord
        for vWord in re.findall(r"\w+", pQuestion["code"])
        if len(vWord) >= MIN_IDENTIFIER_LENGTH
    }

    rCites = bool(CODE_REFERENCE_PATTERN.search(pQuestion["question"])) or bool(
        vIdentifiers & set(re.findall(r"\w+", pQuestion["question"]))
    )

    return rCites


def find_writing_issues(pQuestions, pOthers=()):
    """Retourne les défauts d'écriture d'un lot, quelle que soit sa taille.

    Choix tronqués, fins de choix répétées et extraits de code hors sujet sont
    les contournements habituels des règles de longueur et de cas concrets ;
    une reformulation d'une question existante n'apporte rien.
    """

    rIssues = []
    vDuplicate = find_duplicate_issue(pQuestions, pOthers)

    if vDuplicate:
        rIssues.append(vDuplicate)
    vTruncatedIds = [
        vQuestion["id"]
        for vQuestion in pQuestions
        if any(
            vChoice.rstrip().endswith(TRUNCATED_ENDINGS)
            for vChoice in vQuestion["choices"]
        )
    ]

    if vTruncatedIds:
        rIssues.append(
            (
                f"{len(vTruncatedIds)} question(s) aux choix coupés par « … »",
                vTruncatedIds,
            )
        )

    vEndings = Counter(
        get_choice_ending(vChoice)
        for vQuestion in pQuestions
        for vChoice in vQuestion["choices"]
    )
    vLimit = max(FILLER_MIN_COUNT, FILLER_SHARE * len(pQuestions))

    for vEnding, vCount in vEndings.most_common(MAX_FILLER_ISSUES):
        if vCount < vLimit or len(vEnding.split()) < FILLER_ENDING_WORDS:
            break

        rIssues.append(
            (
                f"{vCount} choix finissent par « {vEnding} » : remplissage probable",
                [
                    vQuestion["id"]
                    for vQuestion in pQuestions
                    if any(
                        get_choice_ending(vChoice) == vEnding
                        for vChoice in vQuestion["choices"]
                    )
                ],
            )
        )

    vCodeIds = [vQuestion["id"] for vQuestion in pQuestions if "code" in vQuestion]
    vUnrelatedIds = [
        vQuestion["id"]
        for vQuestion in pQuestions
        if "code" in vQuestion and not cites_code(vQuestion)
    ]

    if len(vUnrelatedIds) > MAX_UNRELATED_CODE_SHARE * len(vCodeIds):
        rIssues.append(
            (
                f"{len(vUnrelatedIds)} extrait(s) de code que l'énoncé ne cite pas",
                vUnrelatedIds,
            )
        )

    return rIssues


def assess_questions(pQuestions, pDomain=None, pOthers=()):
    """Mesure les questions d'un lot ; retourne leur résumé et leurs alertes.

    pOthers sont les autres questions du thème, comparées pour repérer les
    doublons. Chaque alerte garde les identifiants concernés : la demande de
    correction les cite.
    """

    # Les mesures portent sur les choix proposés : seuls les QCM sont concernés.
    vQuestions = [vQuestion for vQuestion in pQuestions if get_type(vQuestion) == "qcm"]
    vOthers = [vQuestion for vQuestion in pOthers if get_type(vQuestion) == "qcm"]
    vIssues = []

    if len(vQuestions) >= MIN_QUALITY_SAMPLE:
        vIssues += find_bias_issues(vQuestions, pDomain)

    vIssues += find_writing_issues(vQuestions, vOthers)

    if vIssues:
        logger.warning(
            "Lot de révision à vérifier : %s",
            " ; ".join(vWarning for vWarning, _ in vIssues),
        )

    rQuality = {
        "summary": (
            describe_measures(vQuestions)
            if vQuestions
            else f"{len(pQuestions)} question(s) interactive(s), sans choix à mesurer"
        ),
        "warnings": [vWarning for vWarning, _ in vIssues],
        "issues": vIssues,
    }

    return rQuality


def get_lot_number(pQuestionId, pThemeKey):
    """Retourne le numéro de lot d'un identifiant « thème-lN-… », ou None."""

    vMatch = re.match(rf"{re.escape(pThemeKey)}-l(\d+)-", pQuestionId)

    rLot = int(vMatch.group(1)) if vMatch else None

    return rLot


def apply_lot_quality(pDatabaseFile, pReport):
    """Mesure chaque lot touché par un import et complète le bilan.

    Un lot livré en plusieurs fichiers ou plusieurs archives se mesure en
    entier : ses questions déjà en base comptent avec les nouvelles.
    """

    vThemes = {}

    for vBatch in pReport["batches"]:
        vTheme = vThemes.setdefault(
            vBatch["key"], {**vBatch, "ids": set(), "lots": set()}
        )
        vTheme["ids"] |= set(vBatch["ids"])
        vTheme["lots"] |= {get_lot_number(vId, vBatch["key"]) for vId in vBatch["ids"]}
        vTheme["unknown_domain"] = vTheme["unknown_domain"] or vBatch["unknown_domain"]

    if not vThemes:
        return

    vImported = get_imported_questions(pDatabaseFile)

    for vKey, vTheme in vThemes.items():
        vQuestions = [
            vQuestion
            for vThemeKey, _, vQuestion in vImported
            if vThemeKey == vKey
            and (
                vQuestion["id"] in vTheme["ids"]
                or get_lot_number(vQuestion["id"], vKey) in vTheme["lots"] - {None}
            )
        ]
        vLotIds = {vQuestion["id"] for vQuestion in vQuestions}
        vOthers = [
            vQuestion
            for vThemeKey, _, vQuestion in vImported
            if vThemeKey == vKey and vQuestion["id"] not in vLotIds
        ] + load_quiz().get(vKey, {}).get("questions", [])
        vQuality = assess_questions(vQuestions, vTheme["domain"], vOthers)
        vIssues = list(vQuality["issues"])

        if vTheme["unknown_domain"]:
            vDomain, vSubdomain = vTheme["unknown_domain"]
            vIssues.append(
                (
                    f"domaine « {vDomain} / {vSubdomain} » inconnu : le thème a "
                    "été classé par mots-clés",
                    [],
                )
            )

        vLots = sorted(vLot for vLot in vTheme["lots"] if vLot is not None)
        vName = vTheme["label"] + (
            " (lot " + ", ".join(map(str, vLots)) + ")" if vLots else ""
        )

        pReport["quality"].append(f"{vName} : {vQuality['summary']}")
        pReport["warnings"] += [f"{vName} : {vWarning}" for vWarning, _ in vIssues]

        if vIssues:
            pReport["review"].append(
                {"key": vKey, "label": vTheme["label"], "issues": vIssues}
            )

        if vTheme["outside_catalog"]:
            pReport["notes"].append(vTheme["label"])


def build_correction_prompt(pReview):
    """Retourne la demande de correction des thèmes signalés à l'import d'un lot."""

    vThemes = "\n\n".join(
        f"Thème « {vTheme['label']} », fichier questions/{vTheme['key']}.json :\n"
        + "\n".join(
            f"- {vWarning}"
            + (f"\n  Questions concernées : {', '.join(vIds)}" if vIds else "")
            for vWarning, vIds in vTheme["issues"]
        )
        for vTheme in pReview
    )

    rPrompt = Template(CORRECTION_FILE.read_text(encoding="utf-8")).substitute(
        themes=vThemes
    )

    return rPrompt
