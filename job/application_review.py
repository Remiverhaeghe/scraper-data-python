"""Relecture d'une lettre de candidature avant envoi : longueur, mots-clés, fautes

Les contrôles sont des règles simples, sans correcteur ni service en ligne : ils
attrapent les oublis fréquents (mot-clé de l'annonce absent, nom de l'entreprise
manquant, crochet laissé du modèle) et quelques fautes courantes. Ils ne
remplacent pas une relecture à voix haute.
"""

import re

from job.cv_keywords import QUALITIES, clean_title, contains_term
from job.fingerprint import normalize
from job.preparation import get_offer_skills, get_offer_text

# Longueur d'une lettre en mots : en dessous, elle paraît bâclée ; au-dessus,
# elle dépasse une page et n'est plus lue jusqu'au bout.
MIN_WORDS = 150
MAX_WORDS = 400

# Phrase difficile à suivre à l'oral comme à l'écrit
LONG_SENTENCE_WORDS = 40

# Compétences de l'annonce vérifiées, les premières citées d'abord
MAX_SKILLS = 12

# Faute repérée : motif insensible à la casse, conseil
MISTAKES = (
    (r"\bje me permet\b", "« Je me permets », avec un s."),
    (r"\bquelque soit\b", "« Quel que soit » s'écrit en deux mots."),
    (r"\ben temps que\b", "« En tant que » (en qualité de)."),
    (r"\bpallier à\b", "« Pallier » se construit sans « à » : pallier un manque."),
    (r"\bmalgré que\b", "Préférer « bien que » à « malgré que »."),
    (r"\bau jour d'aujourd'hui\b", "Pléonasme : « aujourd'hui » suffit."),
    (r"\bprofessionel", "« Professionnel » prend deux n."),
    (r"\bd[ée]v[ée]lop(?!p)|\bd[ée]v[ée]ll", "« Développer » : un l, deux p."),
    (r"\baddresse", "« Adresse » prend un seul d."),
    (r"\bconnection\b", "En français : « connexion »."),
    (r"\blanguages?\b", "En français : « langage » (de programmation)."),
    (r"\bcourament\b", "« Couramment » prend deux m."),
    (r"\bapprentisage", "« Apprentissage » prend deux s."),
)

# Formules toutes faites : signalées comme conseil, sans être des fautes
CLICHES = (
    (
        r"\bje reste à votre disposition pour tout renseignement complémentaire\b",
        "Formule très répandue : proposez plutôt un échange précis.",
    ),
    (
        r"\bvous trouverez ci-joint mon cv\b",
        "Le CV est joint de toute façon : la phrase peut disparaître.",
    ),
)

# Reste du modèle : crochets, XXX, chevrons
PLACEHOLDER_PATTERN = re.compile(r"\[[^\]\n]{1,40}\]|\bX{3,}\b|<[^>\n]{1,40}>")

# Mot répété à la suite (« le le »), sauf les doublons voulus du français
REPEATED_WORD_PATTERN = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
ALLOWED_REPEATS = {"nous", "vous", "si", "très", "plus"}

# Ponctuation double collée au mot : le français met une espace avant ; ! ? :
# (les adresses web « https:// » et les heures « 9:30 » sont épargnées).
FRENCH_SPACING_PATTERN = re.compile(r"[A-Za-zÀ-ÿ)»][;!?]|[A-Za-zÀ-ÿ)»]:(?!//)")

SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")


def count_words(pText):
    """Retourne le nombre de mots d'un texte."""

    rCount = len(re.findall(r"\w+(?:['’-]\w+)*", pText))

    return rCount


def describe_length(pWords):
    """Retourne l'avis sur la longueur et sa tonalité."""

    if pWords == 0:
        rLength = ("Lettre vide.", "danger")
    elif pWords < MIN_WORDS:
        rLength = (
            f"{pWords} mots : un peu court, visez {MIN_WORDS} à {MAX_WORDS} mots.",
            "warning",
        )
    elif pWords > MAX_WORDS:
        rLength = (
            f"{pWords} mots : plus d'une page, resserrez vers {MAX_WORDS} mots.",
            "warning",
        )
    else:
        rLength = (f"{pWords} mots : longueur adaptée à une page.", "success")

    return rLength


def find_mistakes(pText):
    """Retourne les fautes courantes repérées, chacune avec son extrait et un conseil."""

    rMistakes = []

    for vPattern, vAdvice in (*MISTAKES, *CLICHES):
        for vMatch in re.finditer(vPattern, pText, re.IGNORECASE):
            rMistakes.append({"excerpt": vMatch.group(0), "advice": vAdvice})

    for vMatch in REPEATED_WORD_PATTERN.finditer(pText):
        if vMatch.group(1).lower() not in ALLOWED_REPEATS:
            rMistakes.append(
                {"excerpt": vMatch.group(0), "advice": "Mot répété à la suite."}
            )

    for vMatch in PLACEHOLDER_PATTERN.finditer(pText):
        rMistakes.append(
            {"excerpt": vMatch.group(0), "advice": "Reste du modèle, à remplacer."}
        )

    for vMatch in FRENCH_SPACING_PATTERN.finditer(pText):
        rMistakes.append(
            {
                "excerpt": vMatch.group(0),
                "advice": "Une espace avant ; : ! et ? en français.",
            }
        )

    if "  " in pText.replace("\n", " "):
        rMistakes.append({"excerpt": "  ", "advice": "Double espace entre deux mots."})

    return rMistakes


def find_keywords(pLetter, pOffer):
    """Retourne les mots-clés de l'annonce, marqués présents ou absents de la lettre."""

    vLetter = normalize(pLetter)
    vOfferText = normalize(get_offer_text(pOffer))
    vTerms = []

    vTitle = clean_title(pOffer.get("title"))

    if vTitle:
        vTerms.append((vTitle, "Intitulé"))

    if pOffer.get("company"):
        vTerms.append((str(pOffer["company"]), "Entreprise"))

    vTerms.extend((vSkill, "Compétence") for vSkill in get_offer_skills(pOffer))
    vTerms = vTerms[: MAX_SKILLS + 2]
    vTerms.extend(
        (vLabel, "Qualité")
        for vLabel, vPattern in QUALITIES.items()
        if re.search(vPattern, vOfferText)
    )

    rKeywords = []
    vSeen = set()

    for vTerm, vKind in vTerms:
        # Une source écrit « python », le texte « Python » : un seul mot-clé.
        if vTerm.lower() in vSeen:
            continue

        vSeen.add(vTerm.lower())
        vFound = (
            re.search(QUALITIES[vTerm], vLetter) is not None
            if vKind == "Qualité"
            else contains_term(vLetter, vTerm)
        )
        rKeywords.append({"term": vTerm, "kind": vKind, "found": vFound})

    return rKeywords


def review_letter(pLetter, pOffer):
    """Retourne la relecture d'une lettre pour une offre : longueur, mots-clés, fautes."""

    vText = str(pLetter or "")
    vWords = count_words(vText)
    vKeywords = find_keywords(vText, pOffer) if vWords else []
    vFound = sum(1 for vKeyword in vKeywords if vKeyword["found"])

    rReview = {
        "words": vWords,
        "length": describe_length(vWords),
        "keywords": vKeywords,
        "found_share": round(100 * vFound / len(vKeywords)) if vKeywords else 0,
        "mistakes": find_mistakes(vText),
        "long_sentences": sum(
            1
            for vSentence in SENTENCE_PATTERN.findall(vText)
            if count_words(vSentence) > LONG_SENTENCE_WORDS
        ),
    }

    return rReview
